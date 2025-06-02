from fastapi import Depends, HTTPException, status, Header, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional

from app.database import get_db
from app.utils.auth import get_current_user, get_current_admin_user
from app.models.api_key import APIKey

# Re-export dependencies for easier imports
get_current_user = get_current_user
get_current_admin_user = get_current_admin_user

# Define API key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: Optional[str] = Security(api_key_header), db: AsyncSession = Depends(get_db)):
    """
    Validate API key and return the corresponding key record if valid.
    Raises HTTPException if the API key is invalid or expired.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Query database for the API key
    result = await db.execute(select(APIKey).where(APIKey.key == api_key, APIKey.active == True))
    db_key = result.scalars().first()
    
    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Update usage count and last used timestamp
    db_key.calls_count += 1
    db_key.last_used_at = db.bind.execute("SELECT now()").scalar()
    await db.commit()
    
    return db_key
