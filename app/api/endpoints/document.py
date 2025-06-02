"""
API endpoints for document management in the enhanced schema.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import PDFDocument
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentSearch, DocumentUpdate
from app.services.document_service import (
    get_or_create_document,
    get_document_by_id,
    get_document_by_url,
    get_all_documents,
    search_documents,
    update_document_info,
    get_document_processing_history,
    fetch_document_metadata
)
from app.api.deps import get_api_key

router = APIRouter()


@router.post("/", response_model=DocumentResponse)
async def create_document(
    document: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Register a new document in the system.
    This doesn't process the document, just registers it.
    """
    # Check if document already exists
    existing_doc = await get_document_by_url(db, document.url)
    if existing_doc:
        return existing_doc
    
    # Get document metadata
    file_size, mime_type = await fetch_document_metadata(document.url)
    
    # Create the document
    batch_id = document.batch_id if document.batch_id else None
    pdf_doc = await get_or_create_document(db, document.url, batch_id)
    
    # Update with metadata if available
    if file_size or mime_type:
        await update_document_info(db, pdf_doc.id, file_size, mime_type)
    
    await db.commit()
    return pdf_doc


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    List all registered documents.
    """
    documents = await get_all_documents(db, limit, skip)
    return documents


@router.get("/search", response_model=List[DocumentResponse])
async def search_document(
    query: DocumentSearch,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Search for documents by filename or URL.
    """
    documents = await search_documents(db, query.search_term, limit, skip)
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Get a document by ID.
    """
    document = await get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    update_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Update document information.
    """
    document = await update_document_info(
        db, 
        document_id, 
        update_data.file_size, 
        update_data.mime_type,
        update_data.hash
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.commit()
    return document


@router.get("/{document_id}/history", response_model=List[dict])
async def get_document_history(
    document_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Get processing history for a document.
    """
    document = await get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    history = await get_document_processing_history(db, document_id, limit, skip)
    
    # Convert to dict for more flexible response
    history_response = []
    for request in history:
        history_item = {
            "id": request.id,
            "request_type": request.request_type,
            "status": request.status,
            "created_at": request.created_at,
            "completed_at": request.completed_at,
            "batch_id": request.batch_id
        }
        history_response.append(history_item)
    
    return history_response


@router.get("/by-url", response_model=Optional[DocumentResponse])
async def find_document_by_url(
    url: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Find a document by URL.
    """
    document = await get_document_by_url(db, url)
    return document
