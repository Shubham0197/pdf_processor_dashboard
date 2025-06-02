"""
Document service for managing PDF documents in the enhanced schema.
"""
import os
import uuid
import logging
import httpx
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import PDFDocument, BatchDocument
from app.models.processing import ProcessingRequest, AIProcessingResult
from app.models.batch import BatchJob

logger = logging.getLogger(__name__)


async def get_or_create_document(db: AsyncSession, file_url: str, batch_id: Optional[uuid.UUID] = None) -> PDFDocument:
    """
    Get an existing document by URL or create a new one if it doesn't exist.
    
    Args:
        db: Database session
        file_url: URL of the PDF document
        batch_id: Optional batch ID if this is part of a batch job
        
    Returns:
        PDFDocument object
    """
    # Check if document already exists
    result = await db.execute(select(PDFDocument).where(PDFDocument.url == file_url))
    document = result.scalars().first()
    
    if not document:
        # Create new document
        filename = os.path.basename(file_url)
        document = PDFDocument(
            url=file_url,
            filename=filename,
            original_batch_id=batch_id,
            first_seen_at=datetime.now(),
            last_accessed_at=datetime.now()
        )
        db.add(document)
        await db.flush()
        logger.info(f"Created new document: {document.id} for URL: {file_url}")
    else:
        # Update last accessed time
        document.last_accessed_at = datetime.now()
        logger.info(f"Using existing document: {document.id} for URL: {file_url}")
    
    return document


async def create_batch_document(
    db: AsyncSession, 
    batch_id: uuid.UUID,
    document_id: uuid.UUID,
    order_in_batch: Optional[int] = None,
    status: str = "pending"
) -> BatchDocument:
    """
    Create a batch-document association.
    
    Args:
        db: Database session
        batch_id: Batch ID
        document_id: Document ID
        order_in_batch: Optional order in the batch
        status: Status (default: "pending")
        
    Returns:
        BatchDocument object
    """
    # Check if association already exists
    result = await db.execute(
        select(BatchDocument).where(
            BatchDocument.batch_id == batch_id,
            BatchDocument.document_id == document_id
        )
    )
    batch_doc = result.scalars().first()
    
    if not batch_doc:
        # Create new association
        batch_doc = BatchDocument(
            batch_id=batch_id,
            document_id=document_id,
            order_in_batch=order_in_batch,
            status=status,
            created_at=datetime.now()
        )
        db.add(batch_doc)
        await db.flush()
        logger.info(f"Created batch-document association: {batch_doc.id}")
    else:
        logger.info(f"Using existing batch-document association: {batch_doc.id}")
    
    return batch_doc


async def create_processing_request(
    db: AsyncSession,
    document_id: uuid.UUID,
    batch_id: Optional[uuid.UUID] = None,
    batch_document_id: Optional[uuid.UUID] = None,
    request_type: str = "single",
    requested_operations: Dict[str, Any] = None,
    webhook_url: Optional[str] = None,
    user_id: Optional[str] = None
) -> ProcessingRequest:
    """
    Create a new processing request for a document.
    
    Args:
        db: Database session
        document_id: Document ID
        batch_id: Optional batch ID
        batch_document_id: Optional BatchDocument ID
        request_type: Request type (default: "single")
        requested_operations: Optional operations to perform
        webhook_url: Optional webhook URL
        user_id: Optional user ID
        
    Returns:
        ProcessingRequest object
    """
    if requested_operations is None:
        requested_operations = {
            "extract_metadata": True,
            "extract_references": True,
            "extract_full_text": False,
            "complete_references": False
        }
    
    request = ProcessingRequest(
        document_id=document_id,
        batch_id=batch_id,
        batch_document_id=batch_document_id,
        request_type=request_type,
        requested_operations=requested_operations,
        status="pending",
        created_at=datetime.now(),
        webhook_url=webhook_url,
        user_id=user_id
    )
    db.add(request)
    await db.flush()
    logger.info(f"Created processing request: {request.id} for document: {document_id}")
    
    return request


async def save_ai_processing_result(
    db: AsyncSession,
    processing_request_id: uuid.UUID,
    document_id: uuid.UUID,
    processing_type: str,
    status: str = "completed",
    processing_time_ms: Optional[int] = None,
    raw_ai_response: Optional[Dict[str, Any]] = None,
    processed_result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    error_type: Optional[str] = None,
    error_step: Optional[str] = None,
    ai_model_used: Optional[str] = None,
    ai_tokens_used: Optional[int] = None
) -> AIProcessingResult:
    """
    Save an AI processing result.
    
    Args:
        db: Database session
        processing_request_id: Processing request ID
        document_id: Document ID
        processing_type: Type of processing (metadata, references, etc.)
        status: Status of the processing (default: "completed")
        processing_time_ms: Processing time in milliseconds
        raw_ai_response: Raw AI response
        processed_result: Processed result
        error_message: Error message if any
        error_type: Type of error if any
        error_step: Step where error occurred if any
        ai_model_used: AI model used
        ai_tokens_used: Number of tokens used
        
    Returns:
        AIProcessingResult object
    """
    result = AIProcessingResult(
        processing_request_id=processing_request_id,
        document_id=document_id,
        processing_type=processing_type,
        status=status,
        processing_time_ms=processing_time_ms,
        raw_ai_response=raw_ai_response,
        processed_result=processed_result,
        error_message=error_message,
        error_type=error_type,
        error_step=error_step,
        ai_model_used=ai_model_used,
        ai_tokens_used=ai_tokens_used,
        created_at=datetime.now()
    )
    db.add(result)
    await db.flush()
    logger.info(f"Saved AI processing result: {result.id} for request: {processing_request_id}")
    
    return result


async def get_document_processing_history(
    db: AsyncSession, 
    document_id: uuid.UUID,
    limit: int = 10,
    skip: int = 0
) -> List[ProcessingRequest]:
    """
    Get processing history for a document.
    
    Args:
        db: Database session
        document_id: Document ID
        limit: Maximum number of results
        skip: Number of results to skip
        
    Returns:
        List of ProcessingRequest objects
    """
    result = await db.execute(
        select(ProcessingRequest)
        .where(ProcessingRequest.document_id == document_id)
        .order_by(ProcessingRequest.created_at.desc())
        .limit(limit)
        .offset(skip)
    )
    return result.scalars().all()


async def get_document_by_url(db: AsyncSession, url: str) -> Optional[PDFDocument]:
    """
    Get a document by its URL.
    
    Args:
        db: Database session
        url: Document URL
        
    Returns:
        PDFDocument object or None if not found
    """
    result = await db.execute(select(PDFDocument).where(PDFDocument.url == url))
    return result.scalars().first()


async def get_document_by_id(db: AsyncSession, document_id: uuid.UUID) -> Optional[PDFDocument]:
    """
    Get a document by its ID.
    
    Args:
        db: Database session
        document_id: Document ID
        
    Returns:
        PDFDocument object or None if not found
    """
    result = await db.execute(select(PDFDocument).where(PDFDocument.id == document_id))
    return result.scalars().first()


async def get_all_documents(
    db: AsyncSession, 
    page: int = 1,
    limit: int = 10
) -> Tuple[List[PDFDocument], int]:
    """
    Get all documents with pagination.
    
    Args:
        db: Database session
        page: Page number (1-based)
        limit: Maximum number of results per page
        
    Returns:
        Tuple containing:
            - List of PDFDocument objects
            - Total count of documents
    """
    # Calculate skip (offset) from page number
    skip = (page - 1) * limit
    
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(PDFDocument))
    total = count_result.scalar_one()
    
    # Get paginated documents with eager loading of processing_requests
    result = await db.execute(
        select(PDFDocument)
        .options(selectinload(PDFDocument.processing_requests))
        .order_by(PDFDocument.last_accessed_at.desc())
        .limit(limit)
        .offset(skip)
    )
    documents = result.scalars().all()
    
    return documents, total


async def search_documents(
    db: AsyncSession, 
    search_term: str,
    page: int = 1,
    limit: int = 10
) -> Tuple[List[PDFDocument], int]:
    """
    Search documents by filename or URL with pagination.
    
    Args:
        db: Database session
        search_term: Search term
        page: Page number (1-based)
        limit: Maximum number of results per page
        
    Returns:
        Tuple containing:
            - List of PDFDocument objects
            - Total count of matching documents
    """
    # Calculate skip (offset) from page number
    skip = (page - 1) * limit
    
    search_pattern = f"%{search_term}%"
    
    # Search condition
    search_condition = or_(
        PDFDocument.filename.ilike(search_pattern),
        PDFDocument.url.ilike(search_pattern)
    )
    
    # Get total count of matching documents
    count_result = await db.execute(
        select(func.count())
        .select_from(PDFDocument)
        .where(search_condition)
    )
    total = count_result.scalar_one()
    
    # Get paginated search results with eager loading of processing_requests
    result = await db.execute(
        select(PDFDocument)
        .options(selectinload(PDFDocument.processing_requests))
        .where(search_condition)
        .order_by(PDFDocument.last_accessed_at.desc())
        .limit(limit)
        .offset(skip)
    )
    documents = result.scalars().all()
    
    return documents, total


async def update_document_info(
    db: AsyncSession,
    document_id: uuid.UUID,
    file_size: Optional[int] = None,
    mime_type: Optional[str] = None,
    hash_value: Optional[str] = None
) -> Optional[PDFDocument]:
    """
    Update document information.
    
    Args:
        db: Database session
        document_id: Document ID
        file_size: File size in bytes
        mime_type: MIME type
        hash_value: Hash value for integrity checks
        
    Returns:
        Updated PDFDocument object or None if not found
    """
    document = await get_document_by_id(db, document_id)
    if not document:
        return None
        
    if file_size is not None:
        document.file_size = file_size
    if mime_type is not None:
        document.mime_type = mime_type
    if hash_value is not None:
        document.hash = hash_value
        
    await db.flush()
    return document


async def fetch_document_metadata(url: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Fetch document metadata from URL.
    
    Args:
        url: Document URL
        
    Returns:
        Tuple of (file_size, content_type)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(url, follow_redirects=True, timeout=10.0)
            response.raise_for_status()
            
            content_length = response.headers.get("content-length")
            content_type = response.headers.get("content-type")
            
            file_size = int(content_length) if content_length else None
            
            return file_size, content_type
    except Exception as e:
        logger.error(f"Error fetching document metadata: {e}")
        return None, None
