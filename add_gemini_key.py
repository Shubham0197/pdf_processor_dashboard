import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate
from app.services.api_key_service import create_api_key
from app.database import Base

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pdf_processing.db")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def add_gemini_key():
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create a session
    async with async_session() as session:
        # Check if a Gemini key already exists
        from sqlalchemy.future import select
        result = await session.execute(
            select(APIKey).where(APIKey.key_type == "gemini")
        )
        existing_key = result.scalars().first()
        
        if existing_key:
            print("A Gemini API key already exists. Please update it using the API.")
            return
        
        # Get API key from environment or prompt user
        api_key_value = os.getenv("GEMINI_API_KEY")
        if not api_key_value:
            api_key_value = input("Enter your Gemini API key: ")
        
        # Create API key
        api_key = APIKeyCreate(
            name="Gemini API Key",
            key_type="gemini",
            key_value=api_key_value,
            is_active=True,
            description="API key for Google Gemini AI"
        )
        
        # Add to database
        db_api_key, _ = await create_api_key(session, api_key)
        print(f"Added Gemini API key with ID: {db_api_key.id}")

if __name__ == "__main__":
    asyncio.run(add_gemini_key())
