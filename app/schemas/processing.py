from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ProcessingStatusResponse(BaseModel):
    """Processing status response schema"""
    id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True
