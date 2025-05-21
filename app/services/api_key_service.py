from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import os
from app.utils.crypto import encrypt_value, decrypt_value

async def create_api_key(db: AsyncSession, api_key: APIKeyCreate):
    """Create a new API key"""
    # Generate key if not provided
    if not api_key.key_value:
        key_value = APIKey.generate_key(prefix=api_key.key_type[:3])
    else:
        key_value = api_key.key_value
    
    # Encrypt the key value
    encrypted_value = encrypt_value(key_value)
    
    # Create DB record
    db_api_key = APIKey(
        name=api_key.name,
        key_type=api_key.key_type,
        key_value=encrypted_value,
        is_active=api_key.is_active,
        description=api_key.description
    )
    
    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)
    
    # Return the unencrypted key for display once
    return db_api_key, key_value

async def get_api_key(db: AsyncSession, key_id: int):
    """Get API key by ID"""
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    return result.scalars().first()

async def get_api_keys(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Get all API keys"""
    result = await db.execute(select(APIKey).offset(skip).limit(limit))
    return result.scalars().all()

async def update_api_key(db: AsyncSession, key_id: int, api_key: APIKeyUpdate):
    """Update API key"""
    db_api_key = await get_api_key(db, key_id)
    if not db_api_key:
        return None
    
    update_data = api_key.dict(exclude_unset=True)
    
    # If key_value is being updated, encrypt it
    if "key_value" in update_data and update_data["key_value"]:
        update_data["key_value"] = encrypt_value(update_data["key_value"])
    
    for key, value in update_data.items():
        setattr(db_api_key, key, value)
    
    await db.commit()
    await db.refresh(db_api_key)
    return db_api_key

async def delete_api_key(db: AsyncSession, key_id: int):
    """Delete API key"""
    db_api_key = await get_api_key(db, key_id)
    if not db_api_key:
        return False
    
    await db.delete(db_api_key)
    await db.commit()
    return True

async def get_active_key_by_type(db: AsyncSession, key_type: str):
    """Get active API key by type"""
    result = await db.execute(
        select(APIKey)
        .where(APIKey.key_type == key_type)
        .where(APIKey.is_active == True)
        .order_by(APIKey.created_at.desc())
    )
    db_api_key = result.scalars().first()
    
    if db_api_key:
        # Update last used timestamp
        db_api_key.last_used_at = datetime.now()
        await db.commit()
        
        # Decrypt the key value
        try:
            decrypted_value = decrypt_value(db_api_key.key_value)
            return decrypted_value
        except Exception as e:
            print(f"Error decrypting key: {e}")
            return None
    
    return None
