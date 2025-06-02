from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.processing import ProcessingRequest, AIProcessingResult
from app.schemas.processing import ProcessingStatusResponse

router = APIRouter()

@router.get("/{request_id}/status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the status of a processing request
    """
    # Fetch the processing request
    processing_request = await db.get(ProcessingRequest, request_id)
    
    if not processing_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing request not found"
        )
    
    # Check if the processing request belongs to the current user
    if processing_request.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this processing request"
        )
    
    # Return the status
    return {
        "id": processing_request.id,
        "status": processing_request.status,
        "created_at": processing_request.created_at,
        "completed_at": processing_request.completed_at,
        "error": processing_request.error_message if processing_request.status == "failed" else None
    }
