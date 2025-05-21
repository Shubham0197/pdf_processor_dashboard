from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class JobBase(BaseModel):
    file_url: str = Field(..., description="URL to the PDF file")
    file_name: Optional[str] = Field(None, description="Name of the file")

class JobCreate(JobBase):
    batch_id: Optional[int] = Field(None, description="ID of the batch this job belongs to")

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
        orm_mode = True

class JobResponse(BaseModel):
    job_id: str
    file_url: str
    file_name: Optional[str] = None
    status: str
    batch_id: Optional[int] = None

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
    
    class Config:
        orm_mode = True

class BatchWebhookPayload(BaseModel):
    batch_id: str
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    completed_at: datetime
    files: List[JobResult]
