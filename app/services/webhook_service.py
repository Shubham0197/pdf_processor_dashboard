import httpx
import json
import time
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.batch import BatchJob
from app.models.job import ProcessingJob
from app.schemas.job import BatchWebhookPayload, JobResult
from sqlalchemy.future import select
from datetime import datetime

async def send_webhook(webhook_url: str, data: dict, timeout: int = 30):
    """Send webhook to the specified URL"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
            
            return {
                "success": response.status_code in range(200, 300),
                "status_code": response.status_code,
                "response": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def send_batch_webhook(db: AsyncSession, batch_id: int):
    """Send webhook for a completed batch"""
    # Get batch information
    result = await db.execute(select(BatchJob).where(BatchJob.id == batch_id))
    batch = result.scalars().first()
    
    if not batch or not batch.webhook_url:
        return False
    
    # Get all jobs for this batch
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.batch_id == batch_id))
    jobs = result.scalars().all()
    
    # Prepare webhook payload
    job_results = []
    for job in jobs:
        job_result = JobResult(
            job_id=job.job_id,
            status=job.status,
            file_url=job.file_url,
            file_name=job.file_name,
            metadata=job.metadata,
            references=job.references,
            error=job.error_message,
            processing_time=job.processing_time
        )
        job_results.append(job_result)
    
    payload = {
        "batch_id": batch.batch_id,
        "status": batch.status,
        "total_files": batch.total_files,
        "processed_files": batch.processed_files,
        "failed_files": batch.failed_files,
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else datetime.now().isoformat(),
        "files": [job.dict() for job in job_results]
    }
    
    # Send webhook
    webhook_response = await send_webhook(batch.webhook_url, payload)
    
    # Update batch with webhook response
    batch.webhook_response = webhook_response
    await db.commit()
    
    return webhook_response["success"]

async def send_job_webhook(db: AsyncSession, job_id: int):
    """Send webhook for a single job"""
    # Get job information
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    job = result.scalars().first()
    
    if not job or not job.batch:
        return False
    
    # Get batch information
    batch = job.batch
    
    if not batch.webhook_url:
        return False
    
    # Prepare webhook payload for a single job
    payload = {
        "batch_id": batch.batch_id,
        "job_id": job.job_id,
        "status": job.status,
        "file_url": job.file_url,
        "file_name": job.file_name,
        "metadata": job.metadata,
        "references": job.references,
        "error": job.error_message,
        "processing_time": job.processing_time,
        "completed_at": job.completed_at.isoformat() if job.completed_at else datetime.now().isoformat()
    }
    
    # Send webhook
    webhook_response = await send_webhook(batch.webhook_url, payload)
    
    # Update job with webhook response
    job.webhook_sent = True
    job.webhook_response = webhook_response
    await db.commit()
    
    return webhook_response["success"]
