from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base

from app.config import settings

# Create async engine for PostgreSQL
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
if SQLALCHEMY_DATABASE_URL.startswith('postgresql://'):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    """Dependency for getting async DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

async def create_tables():
    """Create database tables"""
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered with Base
        from app.models import batch, job, api_key, user
        await conn.run_sync(Base.metadata.create_all)
