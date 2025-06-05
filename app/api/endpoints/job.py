from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import re
import uuid

from app.database import get_db
from app.models.job import ProcessingJob
from app.models.batch import BatchJob
from app.schemas.job import JobCreate, JobResponse, JobResult, JobProgress
from app.services.pdf_service import process_pdf
from app.services.webhook_service import send_job_webhook
from app.services.background_task_manager import background_task_manager
from app.utils.auth import get_current_user
from app.utils.simple_auth import verify_api_key
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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Create a new job to process a single PDF file (now with background processing)
    """
    # Check if this is a standalone job (not part of an existing batch)
    # If so, create a new batch for tracking purposes
    batch = None
    if job.batch_id is None:
        # Create a new batch job for single PDF processing
        batch = BatchJob(
            batch_id=str(uuid.uuid4()),
            total_files=1,
            status="pending",
            request_data={
                "source": "single_pdf_processing",
                "options": {
                    "extract_metadata": True,
                    "extract_references": True,
                    "extract_full_text": False,
                    "complete_references": job.complete_references
                },
                "file": job.file_url
            }
        )
        db.add(batch)
        await db.commit()
        await db.refresh(batch)
        
        # Set the batch_id for this job
        job.batch_id = batch.id
    
    # Create job
    db_job = ProcessingJob(
        file_url=job.file_url,
        file_name=job.file_name or job.file_url.split("/")[-1],
        batch_id=str(batch.id),  # Convert UUID to string for the foreign key
        status="pending",
        progress_percentage=0  # Initialize progress
    )
    
    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)
    
    # Submit job for background processing
    background_tasks.add_task(background_task_manager.submit_pdf_processing_job, db_job.id)
    
    # Return immediately with job information
    return JobResponse(
        id=db_job.id,
        job_id=db_job.job_id,
        batch_id=db_job.batch_id,
        file_url=db_job.file_url,
        file_name=db_job.file_name,
        status=db_job.status,
        created_at=db_job.created_at,
        progress_percentage=db_job.progress_percentage or 0
    )

@router.get("/{job_id}", response_model=JobResult)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get status and results of a job (now with progress tracking)
    """
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.job_id == job_id))
    job = result.scalars().first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    # Return job result with progress tracking fields
    return JobResult(
        job_id=job.job_id,
        status=job.status,
        file_url=job.file_url,
        file_name=job.file_name,
        extracted_text=None,  # Don't include the extracted text
        doc_metadata=job.doc_metadata if hasattr(job, 'doc_metadata') else None,
        references=job.references if hasattr(job, 'references') else None,
        error=job.error_message if hasattr(job, 'error_message') else None,
        processing_time=job.processing_time if hasattr(job, 'processing_time') else None,
        # Add progress tracking fields
        progress_percentage=job.progress_percentage if hasattr(job, 'progress_percentage') else 0,
        started_at=job.started_at if hasattr(job, 'started_at') else None,
        completed_at=job.completed_at if hasattr(job, 'completed_at') else None,
        worker_id=job.worker_id if hasattr(job, 'worker_id') else None
    )

@router.get("/{job_id}/raw-response")
async def get_job_raw_response(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get raw AI responses for a job from the enhanced processing system.
    This endpoint attempts to fetch raw AI responses from both the old job system
    and the new processing system.
    """
    # First, check if this job exists in the old system
    job_result = await db.execute(select(ProcessingJob).where(ProcessingJob.job_id == job_id))
    job = job_result.scalars().first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    # Try to find processing results in the enhanced system
    # We need to look for processing requests/results that might be related to this job
    try:
        from app.models.processing import ProcessingRequest, AIProcessingResult
        from app.models.document import PDFDocument
        
        # Look for documents with the same URL
        doc_result = await db.execute(
            select(PDFDocument).where(PDFDocument.url == job.file_url)
        )
        document = doc_result.scalars().first()
        
        raw_responses = {}
        
        if document:
            # Get the latest processing results for this document
            processing_results = await db.execute(
                select(AIProcessingResult)
                .where(AIProcessingResult.document_id == document.id)
                .order_by(AIProcessingResult.created_at.desc())
            )
            
            results = processing_results.scalars().all()
            
            for result in results:
                if result.raw_ai_response:
                    raw_responses[result.processing_type] = result.raw_ai_response
        
        # If we found raw responses in the enhanced system, return them
        if raw_responses:
            return {
                "job_id": job_id,
                "source": "enhanced_processing_system",
                "raw_responses": raw_responses,
                "available_types": list(raw_responses.keys())
            }
        
        # Fallback: return a message indicating raw responses aren't available
        return {
            "job_id": job_id,
            "source": "legacy_job_system",
            "message": "Raw AI responses not available for jobs processed with the legacy system",
            "suggestion": "Process the PDF again to get detailed raw AI responses"
        }
        
    except Exception as e:
        # If there's an error accessing the enhanced system, return a safe response
        return {
            "job_id": job_id,
            "error": f"Unable to fetch raw AI responses: {str(e)}",
            "message": "Raw AI response data may not be available for this job"
        }

@router.get("/{job_id}/progress", response_model=JobProgress)
async def get_job_progress(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get real-time progress of a job
    """
    # Try to get status from background task manager first
    # Convert job_id (string) to job database ID (int)
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.job_id == job_id))
    job = result.scalars().first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    # Get progress from background task manager
    job_status = await background_task_manager.get_job_status(db, job.id)
    
    if job_status:
        # Return progress from background task manager
        return JobProgress(
            job_id=job_status["job_id"],
            status=job_status["status"],
            progress_percentage=job_status["progress_percentage"],
            started_at=datetime.fromisoformat(job_status["started_at"]) if job_status["started_at"] else None,
            estimated_completion=datetime.fromisoformat(job_status["estimated_completion"]) if job_status["estimated_completion"] else None,
            completed_at=datetime.fromisoformat(job_status["completed_at"]) if job_status["completed_at"] else None,
            worker_id=job_status["worker_id"],
            last_heartbeat=datetime.fromisoformat(job_status["last_heartbeat"]) if job_status["last_heartbeat"] else None,
            error_message=job_status["error_message"],
            processing_time=job_status["processing_time"],
            created_at=datetime.fromisoformat(job_status["created_at"]) if job_status["created_at"] else None,
            file_url=job_status["file_url"],
            file_name=job_status["file_name"]
        )
    else:
        # Fallback to database values
        return JobProgress(
            job_id=job.job_id,
            status=job.status,
            progress_percentage=job.progress_percentage or 0,
            started_at=job.started_at,
            estimated_completion=job.estimated_completion,
            completed_at=job.completed_at,
            worker_id=job.worker_id,
            last_heartbeat=job.last_heartbeat,
            error_message=job.error_message,
            processing_time=job.processing_time,
            created_at=job.created_at,
            file_url=job.file_url,
            file_name=job.file_name
        )
