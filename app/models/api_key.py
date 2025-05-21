from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base
import secrets
import datetime

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    key_type = Column(String(50), nullable=False)  # e.g., "gemini", "webhook_auth", etc.
    key_value = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    @classmethod
    def generate_key(cls, prefix=""):
        """Generate a secure API key with optional prefix"""
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}" if prefix else random_part
