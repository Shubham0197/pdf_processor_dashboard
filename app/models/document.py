import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
# Use our custom UUID type instead of PostgreSQL specific one for cross-database compatibility
from app.db.types import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class PDFDocument(Base):
    """Model for storing unique PDF documents"""
    __tablename__ = "pdf_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String, index=True, unique=True, nullable=False)
    filename = Column(String)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    hash = Column(String, nullable=True)
    original_batch_id = Column(UUID(as_uuid=True), ForeignKey("batch_jobs.id"), nullable=True)
    first_seen_at = Column(DateTime, default=datetime.now)
    last_accessed_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    original_batch = relationship("BatchJob", back_populates="original_documents", foreign_keys=[original_batch_id])
    batch_associations = relationship("BatchDocument", back_populates="document")
    processing_requests = relationship("ProcessingRequest", back_populates="document")
    processing_results = relationship("AIProcessingResult", back_populates="document")
    
    def __repr__(self):
        return f"<PDFDocument(id={self.id}, url='{self.url}', filename='{self.filename}')>"


class BatchDocument(Base):
    """Association table between batch jobs and documents"""
    __tablename__ = "batch_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batch_jobs.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("pdf_documents.id"), nullable=False)
    order_in_batch = Column(Integer, nullable=True)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    batch = relationship("BatchJob", back_populates="documents")
    document = relationship("PDFDocument", back_populates="batch_associations")
    processing_requests = relationship("ProcessingRequest", back_populates="batch_document")
    
    def __repr__(self):
        return f"<BatchDocument(batch_id={self.batch_id}, document_id={self.document_id}, status='{self.status}')>"
