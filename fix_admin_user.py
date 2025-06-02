import asyncio
import os
from sqlalchemy import select
from app.database import SessionLocal
from app.models.user import User
from app.config import settings

async def reset_admin_user():
    """Reset the admin user with the correct password hash"""
    print("Resetting admin user...")
    
    # Password that will work with the application's password verification
    password = "admin123"
    
    async with SessionLocal() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        user = result.scalars().first()
        
        if user:
            # Update existing user
            print(f"Updating existing admin user: {settings.ADMIN_EMAIL}")
            user.hashed_password = User.get_password_hash(password)
            user.is_active = True
            user.is_admin = True
        else:
            # Create new admin user
            print(f"Creating new admin user: {settings.ADMIN_EMAIL}")
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=User.get_password_hash(password),
                is_active=True,
                is_admin=True,
                full_name="Admin User"
            )
            db.add(admin_user)
        
        await db.commit()
    
    print("Admin user reset complete.")
    print("Login with:")
    print(f"  Email: {settings.ADMIN_EMAIL}")
    print(f"  Password: {password}")

if __name__ == "__main__":
    asyncio.run(reset_admin_user())
