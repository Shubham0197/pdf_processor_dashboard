import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyUpdate
from app.services.api_key_service import update_api_key
from app.database import Base

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pdf_processing.db")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def update_gemini_key():
    # Create a session
    async with async_session() as session:
        # Find the existing Gemini key
        result = await session.execute(
            select(APIKey).where(APIKey.key_type == "gemini")
        )
        existing_key = result.scalars().first()
        
        if not existing_key:
            print("No Gemini API key found. Please run add_gemini_key.py first.")
            return
        
        # Get API key from environment or prompt user
        api_key_value = os.getenv("GEMINI_API_KEY")
        if not api_key_value:
            api_key_value = input("Enter your Gemini API key: ")
        
        # Update API key
        api_key_update = APIKeyUpdate(
            key_value=api_key_value,
            is_active=True,
            description="Updated Gemini API Key"
        )
        
        # Update in database
        updated_key = await update_api_key(session, existing_key.id, api_key_update)
        print(f"Updated Gemini API key with ID: {updated_key.id}")

if __name__ == "__main__":
    asyncio.run(update_gemini_key())
