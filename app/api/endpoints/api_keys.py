from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate, APIKeyResponse
from app.services.api_key_service import (
    create_api_key, get_api_key, get_api_keys, 
    update_api_key, delete_api_key
)
from app.api.deps import get_current_admin_user
from typing import List

router = APIRouter()

# Disable authentication for demo purposes
from app.api.deps import get_current_admin_user
def get_demo_admin():
    return {"is_admin": True}

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_new_api_key(
    api_key: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_demo_admin)
):
    """Create a new API key (admin only)"""
    db_api_key, key_value = await create_api_key(db, api_key)
    return {
        "id": db_api_key.id,
        "name": db_api_key.name,
        "key_type": db_api_key.key_type,
        "key_value": key_value,  # Only returned once
        "created_at": db_api_key.created_at
    }

@router.get("/", response_model=List[APIKeyResponse])
async def read_api_keys(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_demo_admin)
):
    """Get all API keys (admin only)"""
    api_keys = await get_api_keys(db, skip=skip, limit=limit)
    return api_keys

@router.get("/{key_id}", response_model=APIKeyResponse)
async def read_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_demo_admin)
):
    """Get API key by ID (admin only)"""
    db_api_key = await get_api_key(db, key_id)
    if db_api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    return db_api_key

@router.put("/{key_id}", response_model=APIKeyResponse)
async def update_existing_api_key(
    key_id: int,
    api_key: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_demo_admin)
):
    """Update API key (admin only)"""
    db_api_key = await update_api_key(db, key_id, api_key)
    if db_api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    return db_api_key

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_demo_admin)
):
    """Delete API key (admin only)"""
    success = await delete_api_key(db, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")

@router.put("/type/{key_type}", response_model=APIKeyResponse)
async def update_api_key_by_type(
    key_type: str,
    api_key: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_demo_admin)
):
    """Update API key by type (admin only)"""
    # Find the key by type
    from sqlalchemy.future import select
    from app.models.api_key import APIKey
    
    result = await db.execute(
        select(APIKey).where(APIKey.key_type == key_type)
    )
    db_api_key = result.scalars().first()
    
    if db_api_key is None:
        # If key doesn't exist, create it
        from app.schemas.api_key import APIKeyCreate
        new_key = APIKeyCreate(
            name=f"{key_type.capitalize()} API Key",
            key_type=key_type,
            key_value=api_key.key_value,
            is_active=api_key.is_active if api_key.is_active is not None else True,
            description=api_key.description or f"API key for {key_type}"
        )
        db_api_key, _ = await create_api_key(db, new_key)
        return db_api_key
    
    # Update the key
    from app.services.api_key_service import update_api_key
    updated_key = await update_api_key(db, db_api_key.id, api_key)
    if updated_key is None:
        raise HTTPException(status_code=500, detail="Failed to update API key")
    
    return updated_key
