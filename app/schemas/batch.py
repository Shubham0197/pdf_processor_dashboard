from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class FileRequest(BaseModel):
    url: str = Field(..., description="URL to the PDF file")
    file_id: Optional[str] = Field(None, description="Optional client-side identifier for the file")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata about the file")

class BatchOptions(BaseModel):
    extract_references: bool = Field(True, description="Extract references from the PDF")
    extract_metadata: bool = Field(True, description="Extract metadata from the PDF")
    extract_full_text: bool = Field(False, description="Extract full text from the PDF")

class BatchRequest(BaseModel):
    webhook_url: Optional[str] = Field(None, description="URL to send results to when processing is complete")
    files: List[FileRequest] = Field(..., description="List of files to process")
    options: Optional[BatchOptions] = Field(None, description="Processing options")
    batch_id: Optional[str] = Field(None, description="Optional client-side batch identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "webhook_url": "https://example.com/webhook",
                "files": [
                    {"url": "https://example.com/file1.pdf", "file_id": "doc1"},
                    {"url": "https://example.com/file2.pdf", "file_id": "doc2"}
                ],
                "options": {
                    "extract_references": True,
                    "extract_metadata": True,
                    "extract_full_text": False
                },
                "batch_id": "client-batch-123"
            }
        }

class BatchResponse(BaseModel):
    batch_id: str = Field(..., description="Server-generated batch identifier")
    status: str = Field("pending", description="Status of the batch job")
    total_files: int = Field(..., description="Total number of files in the batch")
    created_at: datetime
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")
    
    class Config:
        from_attributes = True

class BatchStatusResponse(BatchResponse):
    processed_files: int = Field(0, description="Number of files processed")
    failed_files: int = Field(0, description="Number of files that failed processing")
    completed_at: Optional[datetime] = Field(None, description="When the batch was completed")
    
    class Config:
        from_attributes = True
