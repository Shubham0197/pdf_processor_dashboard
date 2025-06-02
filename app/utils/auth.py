from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get current user from JWT token"""
    import logging
    logger = logging.getLogger("app.auth")
    logger.setLevel(logging.DEBUG)
    
    # Add console handler if not already added
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - API AUTH - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    logger.debug(f"API auth attempt with token: {'Present (starts with: ' + token[:10] + '...)' if token else 'None'}")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        logger.debug(f"Token decoded successfully. User ID: {user_id}")
        if user_id is None:
            logger.error("API auth failed: No user ID in token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.JWTError as e:
        logger.error(f"API auth failed: JWT decode error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    
    if user is None:
        logger.error(f"API auth failed: User ID {user_id} not found in database")
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        logger.error(f"API auth failed: User ID {user_id} is inactive")
        raise HTTPException(status_code=400, detail="Inactive user")
    
    logger.debug(f"API auth successful for user: {user.email}")
    
    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Check if current user is admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
