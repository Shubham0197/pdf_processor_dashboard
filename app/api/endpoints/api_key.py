from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.api_key import APIKeyCreate, APIKeyResponse
from app.services.api_key_service import create_api_key

router = APIRouter()

@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def add_api_key(
    api_key: APIKeyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new API key to the system
    """
    try:
        db_api_key, key_value = await create_api_key(db, api_key)
        
        # Return the unencrypted key for display once
        return APIKeyResponse(
            id=db_api_key.id,
            name=db_api_key.name,
            key_type=db_api_key.key_type,
            key_value=key_value,  # Return the unencrypted key only once
            is_active=db_api_key.is_active,
            description=db_api_key.description,
            created_at=db_api_key.created_at,
            updated_at=db_api_key.updated_at,
            last_used_at=db_api_key.last_used_at
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating API key: {str(e)}"
        )
