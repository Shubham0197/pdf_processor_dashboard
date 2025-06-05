"""
Manual migration to add progress tracking fields to ProcessingJob table (SQLite version)
This script adds the new background job progress tracking fields to the existing table.
"""
import asyncio
import aiosqlite
import os
from app.config import settings

async def add_progress_fields():
    """Add progress tracking fields to processing_jobs table for SQLite"""
    # Extract the database file path from SQLite URL
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite+aiosqlite:///'):
        db_path = db_url.replace('sqlite+aiosqlite:///', '')
    elif db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
    else:
        raise ValueError(f"Unsupported database URL format: {db_url}")
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist. Creating tables using SQLAlchemy...")
        from app.database import create_tables
        await create_tables()
        print("✅ Database and tables created successfully!")
        return
    
    try:
        # Connect to SQLite database
        async with aiosqlite.connect(db_path) as conn:
            print("Adding progress tracking fields to processing_jobs table...")
            
            # Check if columns already exist
            async with conn.execute("PRAGMA table_info(processing_jobs)") as cursor:
                columns_info = await cursor.fetchall()
                existing_column_names = [row[1] for row in columns_info]  # Column name is at index 1
                print(f"Existing columns: {existing_column_names}")
            
            # Add columns if they don't exist
            columns_to_add = [
                ("progress_percentage", "INTEGER DEFAULT 0"),
                ("started_at", "TIMESTAMP"),
                ("estimated_completion", "TIMESTAMP"),
                ("worker_id", "VARCHAR(255)"),
                ("last_heartbeat", "TIMESTAMP")
            ]
            
            for column_name, column_type in columns_to_add:
                if column_name not in existing_column_names:
                    query = f"ALTER TABLE processing_jobs ADD COLUMN {column_name} {column_type}"
                    print(f"Executing: {query}")
                    await conn.execute(query)
                    await conn.commit()
                    print(f"✅ Added column: {column_name}")
                else:
                    print(f"⏭️  Column {column_name} already exists")
            
            # Update existing rows to have progress_percentage = 0 if it's NULL
            await conn.execute("""
                UPDATE processing_jobs 
                SET progress_percentage = 0 
                WHERE progress_percentage IS NULL
            """)
            await conn.commit()
            
            print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(add_progress_fields()) 