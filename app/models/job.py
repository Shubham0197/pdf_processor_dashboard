from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(Integer, ForeignKey("batch_jobs.id"), nullable=True)
    file_url = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=True)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Processing details
    error_message = Column(Text, nullable=True)
    processing_time = Column(Integer, nullable=True)  # in milliseconds
    
    # Results
    extracted_text = Column(Text, nullable=True)
    doc_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' which is reserved in SQLAlchemy
    references = Column(JSON, nullable=True)
    
    # Webhook status
    webhook_sent = Column(Boolean, default=False)
    webhook_response = Column(JSON, nullable=True)
    
    # Relationships
    batch = relationship("BatchJob", back_populates="jobs")
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, job_id={self.job_id}, status={self.status})>"
