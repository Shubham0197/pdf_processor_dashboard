"""
Reset development database script.
Use this during development to reset the database when schema changes are made.
CAUTION: This will delete all data in the database!
"""
import asyncio
from app.database import reset_db

async def main():
    """Main function to reset the database"""
    print("Resetting development database...")
    await reset_db()
    print("Done! Database has been reset with the current schema.")
    print("You can now start the application with 'uvicorn app.main:app --reload'")

if __name__ == "__main__":
    asyncio.run(main())
