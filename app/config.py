import os
from typing import Optional, List

# Handle both Pydantic v1 and v2
try:
    # For Pydantic v2
    from pydantic_settings import BaseSettings
    from pydantic import field_validator as validator
except ImportError:
    # For Pydantic v1
    from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    # Project name
    PROJECT_NAME: str = "PDF Processing API"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/pdf_processing")
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Default admin user
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "changeme")
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    # Handle both Pydantic v1 and v2 config styles
    try:
        # For Pydantic v2
        model_config = {
            "env_file": ".env",
            "case_sensitive": True
        }
    except:
        # For Pydantic v1
        class Config:
            env_file = ".env"
            case_sensitive = True

settings = Settings()
