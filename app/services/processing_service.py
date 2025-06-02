"""
New processing service using the enhanced document-centric schema.
"""
import time
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import PDFDocument, BatchDocument
from app.models.processing import ProcessingRequest, AIProcessingResult
from app.models.batch import BatchJob
from app.services.document_service import get_or_create_document, create_batch_document
from app.services.pdf_service import process_pdf

logger = logging.getLogger(__name__)


async def process_document(
    db: AsyncSession,
    file_url: str,
    options: Dict[str, Any] = None,
    batch_id: Optional[uuid.UUID] = None,
    webhook_url: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Tuple[ProcessingRequest, List[AIProcessingResult]]:
    """
    Process a document using the enhanced document-centric schema.
    
    Args:
        db: Database session
        file_url: URL of the PDF to process
        options: Processing options
        batch_id: Optional batch ID if this is part of a batch
        webhook_url: Optional webhook URL for notification
        user_id: Optional user ID
        
    Returns:
        Tuple of (ProcessingRequest, list of AIProcessingResults)
    """
    start_time = time.time()
    
    # Default options if not provided
    if options is None:
        options = {
            "extract_metadata": True,
            "extract_references": True,
            "extract_full_text": False,
            "complete_references": False
        }
    
    # Step 1: Get or create document
    document = await get_or_create_document(db, file_url, batch_id)
    
    # Step 2: Handle batch association if needed
    batch_document = None
    if batch_id:
        batch_document = await create_batch_document(db, batch_id, document.id)
        
        # Update batch status
        batch_result = await db.execute(select(BatchJob).where(BatchJob.id == batch_id))
        batch = batch_result.scalars().first()
        if batch and batch.status == "pending":
            batch.status = "processing"
        await db.flush()
    
    # Step 3: Create processing request
    processing_request = ProcessingRequest(
        document_id=document.id,
        batch_id=batch_id,
        batch_document_id=batch_document.id if batch_document else None,
        request_type="batch" if batch_id else "single",
        requested_operations=options,
        status="processing",
        created_at=datetime.now(),
        started_at=datetime.now(),
        webhook_url=webhook_url,
        user_id=user_id
    )
    db.add(processing_request)
    await db.flush()
    
    # Step 4: Process the PDF
    try:
        # Use the existing process_pdf service
        result = await process_pdf(file_url, db, options)
        
        # Step 5: Save processing results
        ai_results = []
        
        # Metadata processing result
        if options.get("extract_metadata", True):
            # Ensure raw_metadata_response is a complete object including model info
            raw_metadata = {
                "text": result.get("raw_metadata_response", {}).get("text", "No raw response available"),
                "model": result.get("model", "gemini-pro"),
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "timestamp": datetime.now().isoformat(),
                "request_type": "metadata_extraction"
            }
            
            metadata_result = AIProcessingResult(
                processing_request_id=processing_request.id,
                document_id=document.id,
                processing_type="metadata",
                status="completed" if "error" not in result.get("metadata", {}) else "failed",
                processing_time_ms=int((time.time() - start_time) * 1000),
                raw_ai_response=raw_metadata,
                processed_result=result.get("metadata"),
                error_message=result.get("metadata", {}).get("error") if isinstance(result.get("metadata"), dict) else None,
                error_type="ai_error" if "error" in result.get("metadata", {}) else None,
                ai_model_used=result.get("model", "gemini-pro")
            )
            db.add(metadata_result)
            ai_results.append(metadata_result)
            
        # References processing result
        if options.get("extract_references", True):
            # Ensure raw_references_response is a complete object including model info
            raw_references = {
                "text": result.get("raw_references_response", {}).get("text", "No raw response available"),
                "model": result.get("model", "gemini-pro"),
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "timestamp": datetime.now().isoformat(),
                "request_type": "references_extraction",
                "extraction_options": {
                    "complete_references": options.get("complete_references", False)
                }
            }
            
            references_result = AIProcessingResult(
                processing_request_id=processing_request.id,
                document_id=document.id,
                processing_type="references",
                status="completed" if not isinstance(result.get("references"), dict) or "error" not in result.get("references", {}) else "failed",
                processing_time_ms=int((time.time() - start_time) * 1000),
                raw_ai_response=raw_references,
                processed_result=result.get("references"),
                error_message=result.get("references", {}).get("error") if isinstance(result.get("references"), dict) and "error" in result.get("references", {}) else None,
                error_type="ai_error" if isinstance(result.get("references"), dict) and "error" in result.get("references", {}) else None,
                ai_model_used=result.get("model", "gemini-pro")
            )
            db.add(references_result)
            ai_results.append(references_result)
            
        # Update processing request status
        processing_request.status = "completed"
        processing_request.completed_at = datetime.now()
        
        # Update batch_document status if batch processing
        if batch_document:
            batch_document.status = "completed"
            
            # Update batch counters
            if batch:
                batch.processed_files += 1
                
                # If all files processed, mark batch as completed
                if batch.processed_files + batch.failed_files >= batch.total_files:
                    batch.status = "completed"
                    batch.completed_at = datetime.now()
                    
        await db.commit()
        return processing_request, ai_results
        
    except Exception as e:
        # Handle errors
        logger.error(f"Error processing document {file_url}: {str(e)}")
        
        # Update processing request status
        processing_request.status = "failed"
        processing_request.completed_at = datetime.now()
        
        # Create error result with detailed information
        error_data = {
            "error_message": str(e),
            "error_type": "processing_error",
            "error_step": "pdf_processing",
            "timestamp": datetime.now().isoformat(),
            "requested_operations": options
        }
        
        error_result = AIProcessingResult(
            processing_request_id=processing_request.id,
            document_id=document.id,
            processing_type="processing_error",
            status="failed",
            processing_time_ms=int((time.time() - start_time) * 1000),
            raw_ai_response=error_data,  # Store error details in raw_ai_response for consistency
            processed_result={"error": str(e)},  # Simple error message in processed_result
            error_message=str(e),
            error_type="processing_error",
            error_step="pdf_processing"
        )
        db.add(error_result)
        
        # Update batch_document status if batch processing
        if batch_document:
            batch_document.status = "failed"
            
            # Update batch counters
            if batch:
                batch.failed_files += 1
                
                # If all files processed, mark batch as completed
                if batch.processed_files + batch.failed_files >= batch.total_files:
                    batch.status = "completed"
                    batch.completed_at = datetime.now()
        
        await db.commit()
        return processing_request, [error_result]


async def get_processing_request(db: AsyncSession, request_id: uuid.UUID) -> Optional[ProcessingRequest]:
    """
    Get a processing request by ID.
    
    Args:
        db: Database session
        request_id: Processing request ID
        
    Returns:
        ProcessingRequest object or None if not found
    """
    result = await db.execute(select(ProcessingRequest).where(ProcessingRequest.id == request_id))
    return result.scalars().first()


async def get_processing_results(
    db: AsyncSession,
    request_id: uuid.UUID,
    processing_type: Optional[str] = None
) -> List[AIProcessingResult]:
    """
    Get processing results for a request.
    
    Args:
        db: Database session
        request_id: Processing request ID
        processing_type: Optional type filter
        
    Returns:
        List of AIProcessingResult objects
    """
    query = select(AIProcessingResult).where(AIProcessingResult.processing_request_id == request_id)
    
    if processing_type:
        query = query.where(AIProcessingResult.processing_type == processing_type)
        
    result = await db.execute(query)
    return result.scalars().all()


async def get_latest_processing_request(
    db: AsyncSession,
    document_id: uuid.UUID
) -> Optional[ProcessingRequest]:
    """
    Get the latest processing request for a document.
    
    Args:
        db: Database session
        document_id: Document ID
        
    Returns:
        ProcessingRequest object or None if not found
    """
    result = await db.execute(
        select(ProcessingRequest)
        .where(ProcessingRequest.document_id == document_id)
        .order_by(ProcessingRequest.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def get_latest_processing_result(
    db: AsyncSession,
    document_id: uuid.UUID,
    processing_type: str
) -> Optional[AIProcessingResult]:
    """
    Get the latest processing result of a specific type for a document.
    
    Args:
        db: Database session
        document_id: Document ID
        processing_type: Processing type
        
    Returns:
        AIProcessingResult object or None if not found
    """
    # Get the latest processing request
    latest_request = await get_latest_processing_request(db, document_id)
    if not latest_request:
        return None
        
    # Get the result for the specific type
    result = await db.execute(
        select(AIProcessingResult)
        .where(
            AIProcessingResult.processing_request_id == latest_request.id,
            AIProcessingResult.processing_type == processing_type
        )
    )
    return result.scalars().first()
