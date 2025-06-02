import asyncio
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.config import settings

async def fix_auth_issue():
    """Reset the admin user to ensure it has correct credentials"""
    print("Resetting admin user...")
    
    async with engine.begin() as conn:
        # Ensure the user exists with proper ID
        await conn.execute(text("""
        INSERT OR REPLACE INTO users (id, email, hashed_password, is_active, is_admin, full_name) 
        VALUES (1, :email, :password, 1, 1, 'Admin User')
        """), {
            "email": settings.ADMIN_EMAIL,
            "password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password" hashed
        })
    
    print("Admin user reset complete.")
    print("Login with:")
    print(f"  Email: {settings.ADMIN_EMAIL}")
    print("  Password: password")

if __name__ == "__main__":
    asyncio.run(fix_auth_issue())
