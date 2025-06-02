from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import re
import uuid

from app.database import get_db
from app.models.job import ProcessingJob
from app.models.batch import BatchJob
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
        
        # Update batch status if this job is part of a batch
        if db_job.batch_id:
            batch_result = await db.execute(select(BatchJob).where(BatchJob.id == db_job.batch_id))
            batch = batch_result.scalars().first()
            if batch and batch.status == "pending":
                batch.status = "processing"
                
        await db.commit()
        
        # Use the enhanced processing service to handle the PDF
        try:
            # Import the enhanced processing service
            from app.services.processing_service import process_document
            from app.utils.auth import get_current_user_id_safe
            
            # Process the PDF with the enhanced processing service which captures raw AI responses
            options = {
                "extract_metadata": True,
                "extract_references": True,
                "extract_full_text": False,  # Don't include full text in the response
                "complete_references": job.complete_references  # New option for complete references extraction
            }
            
            # Use the enhanced processing service which properly stores raw AI responses
            try:
                processing_request, ai_results = await process_document(
                    db=db,
                    file_url=job.file_url,
                    options=options,
                    batch_id=uuid.UUID(str(db_job.batch_id)) if db_job.batch_id else None,
                    user_id=None  # Could be enhanced to get actual user ID
                )
                
                # Update the job status based on processing results
                if processing_request.status == "completed":
                    db_job.status = "completed"
                    
                    # Extract results from AI processing results
                    metadata = None
                    references = []
                    
                    for ai_result in ai_results:
                        if ai_result.processing_type == "metadata" and ai_result.processed_result:
                            metadata = ai_result.processed_result
                        elif ai_result.processing_type == "references" and ai_result.processed_result:
                            references = ai_result.processed_result
                    
                    # Set job metadata and references
                    db_job.doc_metadata = metadata
                    db_job.references = references if isinstance(references, list) else []
                    db_job.extracted_text = None  # Don't store extracted text to save space
                    db_job.processing_time = f"{processing_request.completed_at - processing_request.started_at}" if processing_request.completed_at and processing_request.started_at else None
                    db_job.completed_at = datetime.now()
                    
                elif processing_request.status == "failed":
                    db_job.status = "failed"
                    # Get error message from AI results
                    error_messages = []
                    for ai_result in ai_results:
                        if ai_result.error_message:
                            error_messages.append(f"{ai_result.processing_type}: {ai_result.error_message}")
                    db_job.error_message = "; ".join(error_messages) if error_messages else "Processing failed"
                    db_job.completed_at = datetime.now()
                
                # Update batch status if this is associated with a batch
                if db_job.batch_id:
                    # Get the batch
                    batch_result = await db.execute(select(BatchJob).where(BatchJob.id == db_job.batch_id))
                    batch = batch_result.scalars().first()
                    if batch:
                        if db_job.status == "completed":
                            batch.processed_files += 1
                        else:
                            batch.failed_files += 1
                        
                        # If all files are processed, mark batch as completed
                        if batch.processed_files + batch.failed_files >= batch.total_files:
                            batch.status = "completed"
                            batch.completed_at = datetime.now()
                        await db.commit()
                        
            except Exception as enhanced_error:
                print(f"Enhanced processing failed, falling back to legacy processing: {enhanced_error}")
                
                # Fallback to the original processing method
                from app.services.pdf_service import process_pdf
                
                # Process the PDF with the legacy service
                options_legacy = {
                    "extract_metadata": True,
                    "extract_references": True,
                    "extract_full_text": False,
                    "complete_references": job.complete_references
                }
                
                result = await process_pdf(job.file_url, db, options_legacy)
                
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
                    
                    # Update batch status if this is associated with a batch
                    if db_job.batch_id:
                        # Get the batch
                        batch_result = await db.execute(select(BatchJob).where(BatchJob.id == db_job.batch_id))
                        batch = batch_result.scalars().first()
                        if batch:
                            batch.processed_files += 1
                            # If all files are processed, mark batch as completed
                            if batch.processed_files + batch.failed_files >= batch.total_files:
                                batch.status = "completed"
                                batch.completed_at = datetime.now()
                            await db.commit()
        
        except Exception as e:
            db_job.status = "failed"
            db_job.error_message = str(e)
            db_job.completed_at = datetime.now()
            
            # Update batch status for failed job
            if db_job.batch_id:
                # Get the batch
                batch_result = await db.execute(select(BatchJob).where(BatchJob.id == db_job.batch_id))
                batch = batch_result.scalars().first()
                if batch:
                    batch.failed_files += 1
                    # If all files are processed, mark batch as completed
                    if batch.processed_files + batch.failed_files >= batch.total_files:
                        batch.status = "completed"
                        batch.completed_at = datetime.now()
                    await db.commit()
        
        await db.commit()
        
    except Exception as e:
        print(f"Error processing job {db_job.id}: {e}")
        db_job.status = "failed"
        db_job.error_message = str(e)
        
        # Update batch with failure status
        if db_job.batch_id:
            # Get the batch
            batch_result = await db.execute(select(BatchJob).where(BatchJob.id == db_job.batch_id))
            batch = batch_result.scalars().first()
            if batch:
                batch.failed_files += 1
                # If all files are processed, mark batch as completed
                if batch.processed_files + batch.failed_files >= batch.total_files:
                    batch.status = "completed"
                    batch.completed_at = datetime.now()
                
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

@router.get("/{job_id}/raw-response")
async def get_job_raw_response(
    job_id: str,
    db: AsyncSession = Depends(get_db)
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
