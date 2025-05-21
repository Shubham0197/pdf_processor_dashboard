from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import re

from app.database import get_db
from app.models.job import ProcessingJob
from app.schemas.job import JobCreate, JobResponse, JobResult
from app.services.pdf_service import process_pdf
from app.services.webhook_service import send_job_webhook
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter()

async def process_single_job(job_id: int, db: AsyncSession):
    """Background task to process a single job"""
    # Create a new session for this background task
    async_session = AsyncSession(bind=db.bind)
    
    try:
        # Get job information
        result = await async_session.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
        job = result.scalars().first()
        
        if not job:
            print(f"Job {job_id} not found")
            return
        
        # Update job status
        job.status = "processing"
        await async_session.commit()
        
        try:
            # Process the PDF
            options = {}
            if job.batch and job.batch.request_data and "options" in job.batch.request_data:
                options = job.batch.request_data["options"]
                
            result = await process_pdf(job.file_url, async_session, options)
            
            # Update job with results
            if "error" in result:
                job.status = "failed"
                job.error_message = result["error"]
                if job.batch:
                    job.batch.failed_files += 1
            else:
                job.status = "completed"
                job.doc_metadata = result.get("metadata")
                job.references = result.get("references")
                job.extracted_text = result.get("extracted_text")
                if job.batch:
                    job.batch.processed_files += 1
            
            job.processing_time = result.get("processing_time")
            job.completed_at = datetime.now()
            
            await async_session.commit()
            
            # Send webhook if needed
            if job.batch and job.batch.webhook_url:
                await send_job_webhook(async_session, job.id)
                
        except Exception as e:
            # Handle job processing error
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now()
            if job.batch:
                job.batch.failed_files += 1
            await async_session.commit()
            
    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
    finally:
        # Close the session
        await async_session.close()

@router.post("/", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    job: JobCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new job to process a single PDF file
    """
    # Create job
    db_job = ProcessingJob(
        file_url=job.file_url,
        file_name=job.file_name or job.file_url.split("/")[-1],
        batch_id=job.batch_id,
        status="pending"
    )
    
    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)
    
    # For demo purposes, process the job immediately instead of in background
    # This avoids issues with async SQLAlchemy in background tasks
    try:
        # Update job status
        db_job.status = "processing"
        await db.commit()
        
        # Process the PDF
        options = {}
        if job.batch_id:
            # Get batch options if needed
            pass
            
        # Use the Gemini service to process the PDF
        try:
            # Import the process_pdf function
            from app.services.pdf_service import process_pdf
            
            # Process the PDF with Gemini
            options = {
                "extract_metadata": True,
                "extract_references": True,
                "extract_full_text": False  # Don't include full text in the response
            }
            
            # Call the existing process_pdf function which uses Gemini
            result = await process_pdf(job.file_url, db, options)
            
            # Check if there was an error
            if "error" in result:
                db_job.status = "failed"
                db_job.error_message = result["error"]
                db_job.completed_at = datetime.now()
            else:
                # Check if there was an error in metadata or references
                metadata = result.get("metadata", {})
                references = result.get("references", [])
                
                # Handle potential errors in metadata or references
                if isinstance(metadata, dict) and "error" in metadata:
                    error_msg = metadata.get("error")
                    print(f"Error in metadata: {error_msg}")
                    # Set basic metadata with error info
                    db_job.doc_metadata = {
                        "title": "Could not extract metadata",
                        "error": error_msg
                    }
                else:
                    db_job.doc_metadata = metadata
                
                # Handle references - ensure it's always a list
                if isinstance(references, dict) and "error" in references:
                    error_msg = references.get("error")
                    print(f"Error in references: {error_msg}")
                    # Create a list with one error item
                    db_job.references = [{"text": f"Error extracting references: {error_msg}"}]
                elif not isinstance(references, list):
                    # Convert to list if not already
                    db_job.references = [{"text": "No references found or invalid format"}]
                else:
                    db_job.references = references
                
                # Update other job fields
                db_job.status = "completed"
                # Don't store extracted_text to save database space
                db_job.extracted_text = None
                db_job.processing_time = result.get("processing_time")
                db_job.completed_at = datetime.now()
            
        except Exception as e:
            db_job.status = "failed"
            db_job.error_message = str(e)
            db_job.completed_at = datetime.now()
        
        await db.commit()
        
    except Exception as e:
        print(f"Error processing job {db_job.id}: {e}")
        db_job.status = "failed"
        db_job.error_message = str(e)
        await db.commit()
    
    # Return a simplified response to avoid ORM issues
    return JobResponse(
        job_id=db_job.job_id,
        file_url=db_job.file_url,
        file_name=db_job.file_name,
        status=db_job.status,
        batch_id=db_job.batch_id
    )

@router.get("/{job_id}", response_model=JobResult)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get status and results of a job
    """
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.job_id == job_id))
    job = result.scalars().first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    # Return a simplified response to avoid ORM issues
    # Exclude extracted_text as it's not needed in the response
    return JobResult(
        job_id=job.job_id,
        status=job.status,
        file_url=job.file_url,
        file_name=job.file_name,
        extracted_text=None,  # Don't include the extracted text
        doc_metadata=job.doc_metadata if hasattr(job, 'doc_metadata') else None,
        references=job.references if hasattr(job, 'references') else None,
        error=job.error_message if hasattr(job, 'error_message') else None,
        processing_time=job.processing_time if hasattr(job, 'processing_time') else None
    )
