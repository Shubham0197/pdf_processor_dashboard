"""
User adapter for PDF processing API
This module provides compatibility functions for working with User objects vs. Dict
"""
from typing import Union, Dict, Any, Optional
from app.models.user import User

def get_user_id(user: Union[User, Dict[str, Any]]) -> Optional[int]:
    """
    Extract user ID from either a User object or a Dict
    
    This compatibility function handles both User objects (from cookie auth)
    and Dict objects (from API auth) to extract the user ID consistently.
    """
    if user is None:
        return None
        
    if isinstance(user, User):
        return user.id
    elif isinstance(user, dict):
        return user.get("id")
    else:
        raise TypeError(f"Unexpected user type: {type(user)}")

