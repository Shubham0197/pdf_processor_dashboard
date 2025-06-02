import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
# Use our custom UUID type instead of PostgreSQL specific one for cross-database compatibility
from app.db.types import UUID
from app.database import Base

class BatchJob(Base):
    __tablename__ = "batch_jobs"
    
    # Change to UUID for consistency with new models
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    webhook_url = Column(String(255), nullable=True)
    source = Column(String(50), nullable=True)  # batch_upload, single_pdf, api
    batch_metadata = Column(JSON, nullable=True)       # Additional batch metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    
    # Request data
    request_data = Column(JSON, nullable=True)
    
    # Original relationships
    jobs = relationship("ProcessingJob", back_populates="batch", cascade="all, delete-orphan")
    
    # New relationships for the enhanced schema
    documents = relationship("BatchDocument", back_populates="batch", cascade="all, delete-orphan")
    original_documents = relationship("PDFDocument", back_populates="original_batch", foreign_keys="PDFDocument.original_batch_id")
    processing_requests = relationship("ProcessingRequest", back_populates="batch")
    
    def __repr__(self):
        return f"<BatchJob(id={self.id}, batch_id={self.batch_id}, status={self.status})>"
