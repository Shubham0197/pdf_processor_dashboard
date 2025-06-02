import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text
# Use our custom UUID type instead of PostgreSQL specific one for cross-database compatibility
from app.db.types import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ProcessingRequest(Base):
    """Model for tracking individual PDF processing requests"""
    __tablename__ = "processing_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("pdf_documents.id"), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batch_jobs.id"), nullable=True)
    batch_document_id = Column(UUID(as_uuid=True), ForeignKey("batch_documents.id"), nullable=True)
    request_type = Column(String, nullable=False)  # single, batch
    requested_operations = Column(JSON, default={})
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    webhook_url = Column(String, nullable=True)
    webhook_sent_at = Column(DateTime, nullable=True)
    webhook_response = Column(JSON, nullable=True)
    user_id = Column(String, nullable=True)
    
    # Relationships
    document = relationship("PDFDocument", back_populates="processing_requests")
    batch = relationship("BatchJob", back_populates="processing_requests")
    batch_document = relationship("BatchDocument", back_populates="processing_requests")
    results = relationship("AIProcessingResult", back_populates="processing_request", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProcessingRequest(id={self.id}, document_id={self.document_id}, status='{self.status}')>"


class AIProcessingResult(Base):
    """Model for storing detailed AI processing results"""
    __tablename__ = "ai_processing_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_request_id = Column(UUID(as_uuid=True), ForeignKey("processing_requests.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("pdf_documents.id"), nullable=False)
    processing_type = Column(String, nullable=False)  # metadata, references, full_text
    status = Column(String, default="completed")  # completed, failed
    processing_time_ms = Column(Integer, nullable=True)
    raw_ai_response = Column(JSON, nullable=True)
    processed_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_type = Column(String, nullable=True)  # ai_error, processing_error, timeout
    error_step = Column(String, nullable=True)  # extraction, parsing, cleaning
    ai_model_used = Column(String, nullable=True)
    ai_tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    processing_request = relationship("ProcessingRequest", back_populates="results")
    document = relationship("PDFDocument", back_populates="processing_results")
    
    def __repr__(self):
        return f"<AIProcessingResult(id={self.id}, processing_type='{self.processing_type}', status='{self.status}')>"
