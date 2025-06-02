from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import uuid
import asyncio

from app.database import get_db
from app.models.batch import BatchJob
from app.models.job import ProcessingJob
from app.schemas.batch import BatchRequest, BatchResponse, BatchStatusResponse
from app.services.pdf_service import process_pdf
from app.services.webhook_service import send_batch_webhook
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter()

async def process_batch_job(batch_id: int, db: AsyncSession):
    """Background task to process a batch job"""
    # Create a new session for this background task
    async_session = AsyncSession(bind=db.bind)
    
    try:
        # Get batch information
        result = await async_session.execute(select(BatchJob).where(BatchJob.id == batch_id))
        batch = result.scalars().first()
        
        if not batch:
            print(f"Batch {batch_id} not found")
            return
        
        # Update batch status
        batch.status = "processing"
        await async_session.commit()
        
        # Get all jobs for this batch
        result = await async_session.execute(select(ProcessingJob).where(ProcessingJob.batch_id == batch_id))
        jobs = result.scalars().all()
        
        # Process each job
        for job in jobs:
            try:
                # Update job status
                job.status = "processing"
                await async_session.commit()
                
                # Process the PDF
                options = batch.request_data.get("options", {}) if batch.request_data else {}
                result = await process_pdf(job.file_url, async_session, options)
                
                # Update job with results
                if "error" in result:
                    job.status = "failed"
                    job.error_message = result["error"]
                    batch.failed_files += 1
                else:
                    job.status = "completed"
                    job.doc_metadata = result.get("metadata")
                    job.references = result.get("references")
                    job.extracted_text = result.get("extracted_text")
                    batch.processed_files += 1
                
                job.processing_time = result.get("processing_time")
                job.completed_at = datetime.now()
                
                await async_session.commit()
                
            except Exception as e:
                # Handle job processing error
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.now()
                batch.failed_files += 1
                await async_session.commit()
        
        # Update batch status
        batch.status = "completed"
        batch.completed_at = datetime.now()
        await async_session.commit()
        
        # Send webhook if URL is provided
        if batch.webhook_url:
            await send_batch_webhook(async_session, batch_id)
            
    except Exception as e:
        print(f"Error processing batch {batch_id}: {e}")
        # Update batch status to failed
        result = await async_session.execute(select(BatchJob).where(BatchJob.id == batch_id))
        batch = result.scalars().first()
        if batch:
            batch.status = "failed"
            batch.completed_at = datetime.now()
            await async_session.commit()
    finally:
        # Close the session
        await async_session.close()

@router.post("/process", response_model=BatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_batch_job(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new batch job to process multiple PDF files
    """
    # Validate request
    if not request.files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for processing"
        )
    
    # Create batch job
    batch = BatchJob(
        batch_id=request.batch_id or str(uuid.uuid4()),
        webhook_url=request.webhook_url,
        total_files=len(request.files),
        request_data=request.dict()
    )
    
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    
    # Create job for each file
    for file_request in request.files:
        job = ProcessingJob(
            batch_id=batch.id,
            file_url=file_request.url,
            file_name=file_request.file_id or file_request.url.split("/")[-1],
            status="pending"
        )
        db.add(job)
    
    await db.commit()
    
    # Start background task to process the batch
    background_tasks.add_task(process_batch_job, batch.id, db)
    
    return BatchResponse(
        batch_id=batch.batch_id,
        status=batch.status,
        total_files=batch.total_files,
        created_at=batch.created_at
    )

@router.get("/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of a batch job
    """
    result = await db.execute(select(BatchJob).where(BatchJob.batch_id == batch_id))
    batch = result.scalars().first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job with ID {batch_id} not found"
        )
    
    return BatchStatusResponse(
        batch_id=batch.batch_id,
        status=batch.status,
        total_files=batch.total_files,
        processed_files=batch.processed_files,
        failed_files=batch.failed_files,
        created_at=batch.created_at,
        completed_at=batch.completed_at
    )
