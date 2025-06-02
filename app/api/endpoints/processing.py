from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Dict, List
import uuid

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.processing import ProcessingRequest, AIProcessingResult
from app.schemas.processing import ProcessingStatusResponse
from app.services.processing_service import get_processing_request, get_processing_results

router = APIRouter()

@router.get("/{request_id}/status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the status of a processing request (with authentication)
    """
    try:
        request_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request ID format"
        )
    
    # Fetch the processing request
    processing_request = await get_processing_request(db, request_uuid)
    
    if not processing_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing request not found"
        )
    
    # Check if the processing request belongs to the current user
    if processing_request.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this processing request"
        )
    
    # Get the processing results
    processing_results = await get_processing_results(db, request_uuid)
    
    # Return the status with results
    return {
        "id": str(processing_request.id),
        "status": processing_request.status,
        "created_at": processing_request.created_at,
        "completed_at": processing_request.completed_at,
        "error_message": processing_request.error_message if processing_request.status == "failed" else None,
        "results": [
            {
                "processing_type": result.processing_type,
                "status": result.status,
                "processed_result": result.processed_result,
                "raw_ai_response": result.raw_ai_response,
                "error_message": result.error_message,
                "processing_time_ms": result.processing_time_ms,
                "ai_model_used": result.ai_model_used,
                "ai_tokens_used": result.ai_tokens_used
            }
            for result in processing_results
        ]
    }

@router.get("/{request_id}")
async def get_processing_status_public(
    request_id: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get the status of a processing request (public endpoint for frontend)
    """
    print(f"🐛 DEBUG: get_processing_status_public called with request_id: {request_id}")
    
    try:
        request_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request ID format"
        )
    
    # Fetch the processing request
    processing_request = await get_processing_request(db, request_uuid)
    
    if not processing_request:
        print(f"🐛 DEBUG: ❌ Processing request not found for ID: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing request not found"
        )
    
    print(f"🐛 DEBUG: Found processing request with status: {processing_request.status}")
    
    # Get the processing results
    processing_results = await get_processing_results(db, request_uuid)
    print(f"🐛 DEBUG: Found {len(processing_results)} processing results")
    
    # Debug each processing result
    for i, result in enumerate(processing_results):
        print(f"🐛 DEBUG: Result {i}: processing_type={result.processing_type}, status={result.status}")
        print(f"🐛 DEBUG: Result {i}: raw_ai_response type={type(result.raw_ai_response)}")
        if isinstance(result.raw_ai_response, dict):
            print(f"🐛 DEBUG: Result {i}: raw_ai_response keys={list(result.raw_ai_response.keys())}")
            print(f"🐛 DEBUG: Result {i}: raw_ai_response has text={'text' in result.raw_ai_response}")
            if 'text' in result.raw_ai_response:
                text_length = len(result.raw_ai_response['text']) if result.raw_ai_response['text'] else 0
                print(f"🐛 DEBUG: Result {i}: raw_ai_response text length={text_length}")
                print(f"🐛 DEBUG: Result {i}: raw_ai_response text preview={result.raw_ai_response['text'][:100] if result.raw_ai_response['text'] else 'None'}...")
        else:
            print(f"🐛 DEBUG: Result {i}: raw_ai_response={result.raw_ai_response}")
    
    # Return the status with results (no user check for frontend usage)
    response_data = {
        "id": str(processing_request.id),
        "status": processing_request.status,
        "created_at": processing_request.created_at.isoformat() if processing_request.created_at else None,
        "completed_at": processing_request.completed_at.isoformat() if processing_request.completed_at else None,
        "error_message": processing_request.error_message if processing_request.status == "failed" else None,
        "results": [
            {
                "processing_type": result.processing_type,
                "status": result.status,
                "processed_result": result.processed_result,
                "raw_ai_response": result.raw_ai_response,
                "error_message": result.error_message,
                "processing_time_ms": result.processing_time_ms,
                "ai_model_used": result.ai_model_used,
                "ai_tokens_used": result.ai_tokens_used
            }
            for result in processing_results
        ]
    }
    
    print(f"🐛 DEBUG: Returning response with {len(response_data['results'])} results")
    return response_data
