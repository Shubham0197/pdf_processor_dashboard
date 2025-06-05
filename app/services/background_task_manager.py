"""
Background Task Manager for PDF Processing
Handles background processing of PDF files with progress tracking and job management.
"""
import time
import uuid
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ProcessingJob
from app.models.batch import BatchJob
from app.services.gemini_service import process_pdf_directly
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manager for background PDF processing tasks"""
    
    def __init__(self):
        self.worker_id = f"worker_{uuid.uuid4().hex[:8]}"
        logger.info(f"Initialized BackgroundTaskManager with worker ID: {self.worker_id}")

    def submit_pdf_processing_job(self, job_id: int) -> None:
        """
        Submit a PDF processing job for background processing (synchronous wrapper).
        This method is called by FastAPI BackgroundTasks.
        
        Args:
            job_id: Database ID of the job to process
        """
        def run_in_thread():
            """Run the async processing in a separate thread"""
            try:
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Run the async processing
                    loop.run_until_complete(self._async_submit_pdf_processing_job(job_id))
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"[{self.worker_id}] Error in background task for job {job_id}: {e}")
        
        # Start the processing in a separate thread
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True  # Don't block app shutdown
        thread.start()

    async def _async_submit_pdf_processing_job(self, job_id: int) -> None:
        """
        Async implementation of PDF processing job submission.
        
        Args:
            job_id: Database ID of the job to process
        """
        # Create a new database session for this background task
        async with SessionLocal() as db:
            try:
                # Get the job
                result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
                job = result.scalars().first()
                
                if not job:
                    logger.error(f"[{self.worker_id}] Job {job_id} not found")
                    return
                
                logger.info(f"[{self.worker_id}] Starting processing for job {job_id}")
                
                # Initialize job for processing
                await self._initialize_job(db, job)
                
                # Process the PDF with progress updates
                await self._process_pdf_with_progress(db, job)
                
                # Complete the job
                await self._complete_job(db, job)
                
            except Exception as e:
                # Handle any errors during processing
                await self._handle_job_error(db, job_id, str(e))

    async def _initialize_job(self, db: AsyncSession, job: ProcessingJob) -> None:
        """Initialize job for background processing"""
        now = datetime.now()
        
        # Update job status and tracking fields
        job.status = "processing"
        job.started_at = now
        job.worker_id = self.worker_id
        job.last_heartbeat = now
        job.progress_percentage = 0
        job.estimated_completion = now + timedelta(minutes=2)  # Initial estimate
        
        await db.commit()
        logger.info(f"[{self.worker_id}] Initialized job {job.id} for processing")

    async def _process_pdf_with_progress(self, db: AsyncSession, job: ProcessingJob) -> None:
        """Process PDF with regular progress updates"""
        try:
            # Update progress: Starting download/preparation
            await self.update_job_progress(db, job.id, 10, "Preparing PDF processing")
            
            # Determine processing options
            options = self._get_processing_options(job)
            
            # Update progress: Starting AI processing
            await self.update_job_progress(db, job.id, 25, "Starting AI extraction")
            
            # Process the PDF using the existing Gemini service
            start_time = time.time()
            result = await process_pdf_directly(
                pdf_path=job.file_url,
                db=db,
                extract_metadata=options.get("extract_metadata", True),
                extract_references=options.get("extract_references", True),
                complete_references=options.get("complete_references", False)
            )
            processing_time = int((time.time() - start_time) * 1000)
            
            # Update progress: Processing complete
            await self.update_job_progress(db, job.id, 90, "Processing complete, saving results")
            
            # Save results to job
            if "error" in result:
                raise Exception(result["error"])
            
            job.doc_metadata = result.get("metadata")
            job.references = result.get("references")
            job.extracted_text = result.get("extracted_text")
            job.processing_time = processing_time
            
            # Update progress: Finalizing
            await self.update_job_progress(db, job.id, 100, "Complete")
            
        except Exception as e:
            logger.error(f"[{self.worker_id}] Error processing PDF for job {job.id}: {e}")
            raise

    async def _complete_job(self, db: AsyncSession, job: ProcessingJob) -> None:
        """Complete the job processing"""
        now = datetime.now()
        job.status = "completed"
        job.completed_at = now
        job.progress_percentage = 100
        job.last_heartbeat = now
        
        # Update batch statistics if this job is part of a batch
        if job.batch_id:
            batch_result = await db.execute(select(BatchJob).where(BatchJob.id == job.batch_id))
            batch = batch_result.scalars().first()
            if batch:
                batch.processed_files += 1
                
                # Check if batch is complete
                total_jobs = await db.execute(
                    select(ProcessingJob).where(ProcessingJob.batch_id == job.batch_id)
                )
                all_jobs = total_jobs.scalars().all()
                completed_jobs = [j for j in all_jobs if j.status in ["completed", "failed"]]
                
                if len(completed_jobs) >= len(all_jobs):
                    batch.status = "completed"
                    batch.completed_at = now
        
        await db.commit()
        logger.info(f"[{self.worker_id}] Completed job {job.id}")

    async def _handle_job_error(self, db: AsyncSession, job_id: int, error_message: str) -> None:
        """Handle job processing error"""
        try:
            result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
            job = result.scalars().first()
            
            if job:
                now = datetime.now()
                job.status = "failed"
                job.error_message = error_message
                job.completed_at = now
                job.last_heartbeat = now
                job.progress_percentage = 0  # Reset progress on failure
                
                # Update batch statistics
                if job.batch_id:
                    batch_result = await db.execute(select(BatchJob).where(BatchJob.id == job.batch_id))
                    batch = batch_result.scalars().first()
                    if batch:
                        batch.failed_files += 1
                
                await db.commit()
                logger.error(f"[{self.worker_id}] Failed job {job_id}: {error_message}")
        except Exception as e:
            logger.error(f"[{self.worker_id}] Error handling job failure for {job_id}: {e}")

    async def update_job_progress(
        self, 
        db: AsyncSession, 
        job_id: int, 
        progress_percentage: int, 
        status_message: Optional[str] = None
    ) -> None:
        """
        Update job progress and heartbeat.
        
        Args:
            db: Database session
            job_id: Job ID to update
            progress_percentage: Progress percentage (0-100)
            status_message: Optional status message for logging
        """
        try:
            now = datetime.now()
            
            # Calculate estimated completion based on progress
            result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
            job = result.scalars().first()
            
            if job and job.started_at and progress_percentage > 0:
                elapsed = (now - job.started_at).total_seconds()
                estimated_total = elapsed * (100 / progress_percentage)
                estimated_completion = job.started_at + timedelta(seconds=estimated_total)
            else:
                estimated_completion = now + timedelta(minutes=2)  # Default estimate
            
            # Update job progress
            await db.execute(
                update(ProcessingJob)
                .where(ProcessingJob.id == job_id)
                .values(
                    progress_percentage=progress_percentage,
                    last_heartbeat=now,
                    estimated_completion=estimated_completion
                )
            )
            await db.commit()
            
            if status_message:
                logger.info(f"[{self.worker_id}] Job {job_id}: {progress_percentage}% - {status_message}")
            
        except Exception as e:
            logger.error(f"[{self.worker_id}] Error updating progress for job {job_id}: {e}")

    async def get_job_status(self, db: AsyncSession, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current job status and progress.
        
        Args:
            db: Database session
            job_id: Job ID to check
            
        Returns:
            Dictionary with job status information or None if not found
        """
        try:
            result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
            job = result.scalars().first()
            
            if not job:
                return None
            
            return {
                "job_id": job.job_id,
                "status": job.status,
                "progress_percentage": job.progress_percentage or 0,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "estimated_completion": job.estimated_completion.isoformat() if job.estimated_completion else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "worker_id": job.worker_id,
                "last_heartbeat": job.last_heartbeat.isoformat() if job.last_heartbeat else None,
                "error_message": job.error_message,
                "processing_time": job.processing_time,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "file_url": job.file_url,
                "file_name": job.file_name
            }
            
        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return None

    def _get_processing_options(self, job: ProcessingJob) -> Dict[str, Any]:
        """Get processing options for a job"""
        # Default options
        options = {
            "extract_metadata": True,
            "extract_references": True,
            "complete_references": False
        }
        
        # Try to get options from batch if available
        if job.batch_id and job.batch:
            batch_options = job.batch.request_data.get("options", {})
            options.update(batch_options)
        
        return options

    async def cleanup_stuck_jobs(self, db: AsyncSession, timeout_minutes: int = 30) -> List[int]:
        """
        Clean up jobs that have been stuck in processing state.
        
        Args:
            db: Database session
            timeout_minutes: Minutes after which a job is considered stuck
            
        Returns:
            List of job IDs that were cleaned up
        """
        try:
            timeout_time = datetime.now() - timedelta(minutes=timeout_minutes)
            
            # Find stuck jobs
            result = await db.execute(
                select(ProcessingJob).where(
                    ProcessingJob.status == "processing",
                    ProcessingJob.last_heartbeat < timeout_time
                )
            )
            stuck_jobs = result.scalars().all()
            
            cleaned_job_ids = []
            for job in stuck_jobs:
                job.status = "failed"
                job.error_message = f"Job timed out after {timeout_minutes} minutes"
                job.completed_at = datetime.now()
                cleaned_job_ids.append(job.id)
                
                logger.warning(f"Cleaned up stuck job {job.id}")
            
            if cleaned_job_ids:
                await db.commit()
                logger.info(f"Cleaned up {len(cleaned_job_ids)} stuck jobs")
            
            return cleaned_job_ids
            
        except Exception as e:
            logger.error(f"Error cleaning up stuck jobs: {e}")
            return []


# Global instance
background_task_manager = BackgroundTaskManager() 