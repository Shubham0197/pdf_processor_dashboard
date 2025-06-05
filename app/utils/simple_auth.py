"""
Simple API Key Authentication System
"""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader
from typing import Optional

# Simple constant API key - in production, this should be in environment variables
SIMPLE_API_KEY = "pdf-processing-api-key-2024"

# API Key header dependency
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> bool:
    """
    Verify the API key from the X-API-Key header
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required. Please provide X-API-Key header."
        )
    
    if api_key != SIMPLE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return True

# Optional authentication (for endpoints that can work with or without auth)
async def optional_verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> bool:
    """
    Optional API key verification - returns True if valid, False if missing/invalid
    """
    if not api_key:
        return False
    
    return api_key == SIMPLE_API_KEY 