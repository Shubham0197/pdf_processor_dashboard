from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.utils.auth import get_current_user, get_current_admin_user

# Re-export dependencies for easier imports
get_current_user = get_current_user
get_current_admin_user = get_current_admin_user
