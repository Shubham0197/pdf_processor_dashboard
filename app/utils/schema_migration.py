"""
Utility for migrating existing job data to the new schema.
This script is intended to be run manually when needed.
"""
import asyncio
import logging
from sqlalchemy import select
from datetime import datetime

from app.database import SessionLocal
from app.models.job import ProcessingJob
from app.models.batch import BatchJob
from app.models.document import PDFDocument, BatchDocument
from app.models.processing import ProcessingRequest, AIProcessingResult


logger = logging.getLogger(__name__)


async def migrate_to_new_schema():
    """Migrate data from old schema to new document-centric schema"""
    logger.info("Starting migration to new schema")
    async with SessionLocal() as db:
        # Step 1: Get all existing jobs
        logger.info("Fetching all existing jobs")
        result = await db.execute(select(ProcessingJob))
        jobs = result.scalars().all()
        logger.info(f"Found {len(jobs)} jobs to migrate")
        
        # Step 2: Create PDFDocument for each unique URL
        unique_urls = {}
        for job in jobs:
            if job.file_url and job.file_url not in unique_urls:
                # Extract filename from URL
                filename = job.file_url.split("/")[-1] if job.file_url else "unknown.pdf"
                
                # Create document entry
                pdf_doc = PDFDocument(
                    url=job.file_url,
                    filename=filename,
                    original_batch_id=job.batch_id,
                    first_seen_at=job.created_at,
                    last_accessed_at=job.updated_at if hasattr(job, "updated_at") else job.created_at
                )
                db.add(pdf_doc)
                await db.flush()  # Get the ID
                
                unique_urls[job.file_url] = pdf_doc.id
                logger.info(f"Created document for URL: {job.file_url}")
        
        await db.commit()
        logger.info(f"Created {len(unique_urls)} unique document entries")
        
        # Step 3: Create BatchDocument associations
        logger.info("Creating BatchDocument associations")
        batch_docs_created = 0
        for job in jobs:
            if not job.batch_id or not job.file_url or job.file_url not in unique_urls:
                continue
                
            # Check if this association already exists
            batch_doc_result = await db.execute(
                select(BatchDocument).where(
                    BatchDocument.batch_id == job.batch_id,
                    BatchDocument.document_id == unique_urls[job.file_url]
                )
            )
            existing_batch_doc = batch_doc_result.scalars().first()
            
            if not existing_batch_doc:
                # Create association
                batch_doc = BatchDocument(
                    batch_id=job.batch_id,
                    document_id=unique_urls[job.file_url],
                    status=job.status,
                    created_at=job.created_at
                )
                db.add(batch_doc)
                batch_docs_created += 1
        
        await db.commit()
        logger.info(f"Created {batch_docs_created} batch document associations")
        
        # Step 4: Migrate jobs to ProcessingRequests and AIProcessingResults
        logger.info("Migrating jobs to ProcessingRequests and AIProcessingResults")
        processing_requests_created = 0
        ai_results_created = 0
        
        for job in jobs:
            if not job.file_url or job.file_url not in unique_urls:
                logger.warning(f"Skipping job {job.id} - missing URL or document not created")
                continue
                
            document_id = unique_urls[job.file_url]
            
            # Get associated BatchDocument if exists
            batch_doc_id = None
            if job.batch_id:
                batch_doc_result = await db.execute(
                    select(BatchDocument).where(
                        BatchDocument.batch_id == job.batch_id,
                        BatchDocument.document_id == document_id
                    )
                )
                batch_doc = batch_doc_result.scalars().first()
                if batch_doc:
                    batch_doc_id = batch_doc.id
            
            # Create ProcessingRequest
            request = ProcessingRequest(
                document_id=document_id,
                batch_id=job.batch_id,
                batch_document_id=batch_doc_id,
                request_type="batch" if job.batch_id else "single",
                status=job.status,
                created_at=job.created_at,
                started_at=job.updated_at if job.status in ["processing", "completed"] else None,
                completed_at=job.completed_at,
                webhook_url=job.webhook_url,
                webhook_sent_at=job.webhook_sent_at if hasattr(job, "webhook_sent_at") else None,
                webhook_response=job.webhook_response,
                requested_operations={
                    "extract_metadata": True,
                    "extract_references": True,
                    "extract_full_text": False,
                    "complete_references": job.complete_references if hasattr(job, "complete_references") else False
                }
            )
            db.add(request)
            await db.flush()  # Get the ID
            processing_requests_created += 1
            
            # Create AIProcessingResults
            # For metadata
            if hasattr(job, "doc_metadata") and job.doc_metadata:
                metadata_result = AIProcessingResult(
                    processing_request_id=request.id,
                    document_id=document_id,
                    processing_type="metadata",
                    status="completed" if not job.error_message else "failed",
                    processing_time_ms=int(job.processing_time * 1000) if job.processing_time else None,
                    processed_result=job.doc_metadata,
                    error_message=job.error_message,
                    error_type="processing_error" if job.error_message else None,
                    created_at=job.completed_at or job.updated_at or job.created_at
                )
                db.add(metadata_result)
                ai_results_created += 1
            
            # For references
            if hasattr(job, "references") and job.references:
                references_result = AIProcessingResult(
                    processing_request_id=request.id,
                    document_id=document_id,
                    processing_type="references",
                    status="completed" if not job.error_message else "failed",
                    processing_time_ms=int(job.processing_time * 1000) if job.processing_time else None,
                    processed_result=job.references,
                    error_message=job.error_message,
                    error_type="processing_error" if job.error_message else None,
                    created_at=job.completed_at or job.updated_at or job.created_at
                )
                db.add(references_result)
                ai_results_created += 1
                
        await db.commit()
        logger.info(f"Created {processing_requests_created} processing requests")
        logger.info(f"Created {ai_results_created} AI processing results")
        
        logger.info("Migration completed successfully!")
        return {
            "documents_created": len(unique_urls),
            "batch_documents_created": batch_docs_created,
            "processing_requests_created": processing_requests_created,
            "ai_results_created": ai_results_created
        }


async def run_migration():
    """Run the migration script"""
    try:
        results = await migrate_to_new_schema()
        print(f"Migration completed successfully!")
        print(f"Documents created: {results['documents_created']}")
        print(f"Batch documents created: {results['batch_documents_created']}")
        print(f"Processing requests created: {results['processing_requests_created']}")
        print(f"AI results created: {results['ai_results_created']}")
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(run_migration())
