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
    complete_references: bool = Field(False, description="Extract complete reference information")

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
                    "extract_full_text": False,
                    "complete_references": True
                },
                "batch_id": "client-batch-123"
            }
        }

# New schemas for the enhanced batch processing format
class EnhancedFileMetadata(BaseModel):
    year: Optional[str] = Field(None, description="Publication year")
    issue: Optional[str] = Field(None, description="Issue number")
    volume: Optional[str] = Field(None, description="Volume number")
    journal: Optional[str] = Field(None, description="Journal name")

class EnhancedFileRequest(BaseModel):
    des_id: int = Field(..., description="Destination ID")
    entry_id: str = Field(..., description="Entry identifier")
    file_url: str = Field(..., description="URL to the PDF file")
    metadata: Optional[EnhancedFileMetadata] = Field(None, description="Publication metadata")

class EnhancedBatchOptions(BaseModel):
    extract_metadata: bool = Field(True, description="Extract metadata from the PDF")
    extract_full_text: bool = Field(False, description="Extract full text from the PDF")
    extract_references: bool = Field(True, description="Extract references from the PDF")
    complete_references: bool = Field(False, description="Extract complete reference information")

class EnhancedBatchRequest(BaseModel):
    files: List[EnhancedFileRequest] = Field(..., description="List of files to process")
    options: EnhancedBatchOptions = Field(..., description="Processing options")
    batch_id: str = Field(..., description="Batch identifier")
    webhook_url: str = Field(..., description="URL to send results to when processing is complete")

    class Config:
        json_schema_extra = {
            "example": {
                "files": [
                    {
                        "des_id": 3,
                        "entry_id": "20",
                        "file_url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf",
                        "metadata": {
                            "year": "1234",
                            "issue": "12",
                            "volume": "123",
                            "journal": "test"
                        }
                    }
                ],
                "options": {
                    "extract_metadata": True,
                    "extract_full_text": True,
                    "extract_references": True
                },
                "batch_id": "9",
                "webhook_url": "http://127.0.0.1:8000/api-integration/webhook/"
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
