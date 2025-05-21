from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class APIKeyBase(BaseModel):
    name: str = Field(..., description="Name of the API key")
    key_type: str = Field(..., description="Type of API key (e.g., 'gemini', 'webhook_auth')")
    is_active: bool = Field(True, description="Whether the key is active")
    description: Optional[str] = Field(None, description="Optional description of the API key")

class APIKeyCreate(APIKeyBase):
    key_value: Optional[str] = Field(None, description="API key value (leave empty to auto-generate)")

class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class APIKeyInDB(APIKeyBase):
    id: int
    key_value: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class APIKeyResponse(APIKeyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
