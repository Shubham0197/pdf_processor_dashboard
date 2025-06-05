from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class JobBase(BaseModel):
    file_url: str = Field(..., description="URL to the PDF file")
    file_name: Optional[str] = Field(None, description="Name of the file")

class JobCreate(JobBase):
    batch_id: Optional[int] = Field(None, description="ID of the batch this job belongs to")
    complete_references: Optional[bool] = Field(False, description="Whether to extract complete references using multiple API calls")

class JobUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Status of the job")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    processing_time: Optional[int] = Field(None, description="Processing time in milliseconds")
    extracted_text: Optional[str] = Field(None, description="Extracted text from the PDF")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extracted metadata")
    references: Optional[List[Dict[str, Any]]] = Field(None, description="Extracted references")
    webhook_sent: Optional[bool] = Field(None, description="Whether webhook was sent")
    webhook_response: Optional[Dict[str, Any]] = Field(None, description="Response from webhook")

class JobInDB(JobBase):
    id: int
    job_id: str
    batch_id: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    processing_time: Optional[int] = None
    webhook_sent: bool
    
    class Config:
        from_attributes = True

class JobResponse(BaseModel):
    id: int
    job_id: str
    file_url: str
    file_name: Optional[str] = None
    status: str
    batch_id: Optional[int] = None
    created_at: datetime
    progress_percentage: int = Field(default=0, description="Progress percentage (0-100)")

class JobProgress(BaseModel):
    job_id: str
    status: str
    progress_percentage: int = Field(description="Progress percentage (0-100)")
    started_at: Optional[datetime] = Field(None, description="When the job started processing")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    completed_at: Optional[datetime] = Field(None, description="When the job was completed")
    worker_id: Optional[str] = Field(None, description="ID of the worker processing the job")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat from the worker")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    processing_time: Optional[int] = Field(None, description="Processing time in milliseconds")
    created_at: Optional[datetime] = Field(None, description="When the job was created")
    file_url: str = Field(description="URL of the PDF being processed")
    file_name: Optional[str] = Field(None, description="Name of the file")

class JobResult(BaseModel):
    job_id: str
    status: str
    file_url: str
    file_name: Optional[str] = None
    extracted_text: Optional[str] = None
    doc_metadata: Optional[Dict[str, Any]] = None
    references: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    processing_time: Optional[int] = None
    
    # Add progress tracking fields to job result
    progress_percentage: Optional[int] = Field(None, description="Progress percentage (0-100)")
    started_at: Optional[datetime] = Field(None, description="When the job started processing")
    completed_at: Optional[datetime] = Field(None, description="When the job was completed")
    worker_id: Optional[str] = Field(None, description="ID of the worker that processed the job")
    
    class Config:
        from_attributes = True

class BatchWebhookPayload(BaseModel):
    batch_id: str
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    completed_at: datetime
    files: List[JobResult]
