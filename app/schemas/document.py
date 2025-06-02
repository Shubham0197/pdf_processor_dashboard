"""
Pydantic schemas for document models.
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class DocumentBase(BaseModel):
    """Base document schema with common fields"""
    url: str
    filename: Optional[str] = None


class DocumentCreate(DocumentBase):
    """Schema for creating a document"""
    batch_id: Optional[uuid.UUID] = None


class DocumentUpdate(BaseModel):
    """Schema for updating document information"""
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    hash: Optional[str] = None


class DocumentSearch(BaseModel):
    """Schema for document search"""
    search_term: str = Field(..., min_length=2)


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: uuid.UUID
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    hash: Optional[str] = None
    original_batch_id: Optional[uuid.UUID] = None
    first_seen_at: datetime
    last_accessed_at: datetime
    
    class Config:
        orm_mode = True


class BatchDocumentBase(BaseModel):
    """Base schema for batch document association"""
    batch_id: uuid.UUID
    document_id: uuid.UUID
    order_in_batch: Optional[int] = None
    status: str = "pending"


class BatchDocumentCreate(BatchDocumentBase):
    """Schema for creating a batch document association"""
    pass


class BatchDocumentResponse(BatchDocumentBase):
    """Schema for batch document response"""
    id: uuid.UUID
    created_at: datetime
    
    class Config:
        orm_mode = True


class ProcessingRequestBase(BaseModel):
    """Base schema for processing requests"""
    document_id: uuid.UUID
    batch_id: Optional[uuid.UUID] = None
    batch_document_id: Optional[uuid.UUID] = None
    request_type: str = "single"
    requested_operations: Dict[str, Any] = Field(default_factory=dict)
    webhook_url: Optional[str] = None


class ProcessingRequestCreate(ProcessingRequestBase):
    """Schema for creating a processing request"""
    pass


class ProcessingRequestUpdate(BaseModel):
    """Schema for updating a processing request"""
    status: Optional[str] = None
    webhook_response: Optional[Dict[str, Any]] = None


class ProcessingRequestResponse(ProcessingRequestBase):
    """Schema for processing request response"""
    id: uuid.UUID
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    webhook_sent_at: Optional[datetime] = None
    webhook_response: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True


class AIProcessingResultBase(BaseModel):
    """Base schema for AI processing results"""
    processing_type: str
    status: str = "completed"
    processing_time_ms: Optional[int] = None
    processed_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_step: Optional[str] = None
    ai_model_used: Optional[str] = None
    ai_tokens_used: Optional[int] = None


class AIProcessingResultCreate(AIProcessingResultBase):
    """Schema for creating an AI processing result"""
    processing_request_id: uuid.UUID
    document_id: uuid.UUID
    raw_ai_response: Optional[Dict[str, Any]] = None


class AIProcessingResultResponse(AIProcessingResultBase):
    """Schema for AI processing result response"""
    id: uuid.UUID
    processing_request_id: uuid.UUID
    document_id: uuid.UUID
    created_at: datetime
    raw_ai_response: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True


class DocumentWithHistory(DocumentResponse):
    """Schema for document with processing history"""
    processing_history: List[ProcessingRequestResponse] = Field(default_factory=list)
    
    class Config:
        orm_mode = True
