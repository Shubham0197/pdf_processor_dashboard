from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class BatchJob(Base):
    __tablename__ = "batch_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    webhook_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    
    # Request data
    request_data = Column(JSON, nullable=True)
    
    # Relationships
    jobs = relationship("ProcessingJob", back_populates="batch", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BatchJob(id={self.id}, batch_id={self.batch_id}, status={self.status})>"
