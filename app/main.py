from fastapi import FastAPI, Request, Depends, HTTPException, status, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.api.router import api_router
from app.database import get_db, create_tables
from app.config import settings
from app.dashboard.routes import dashboard_router
from app.utils.auth import create_access_token, get_current_user
from app.models.user import User
from app.schemas.api_key import APIKeyUpdate
from app.dashboard.routes import get_current_user_from_cookie

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Set up templates for dashboard
dashboard_templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard/templates"))

# Set up templates for login
login_templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))

# Dashboard routes
from app.dashboard.routes import dashboard_router
app.include_router(dashboard_router)

# Login route
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.utils.auth import create_access_token
from datetime import timedelta
from sqlalchemy.future import select
from app.models.user import User

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return login_templates.TemplateResponse("login.html", {"request": request})

@app.get("/process-pdf", response_class=HTMLResponse)
async def process_pdf_page(request: Request, current_user: User = Depends(get_current_user_from_cookie)):
    return login_templates.TemplateResponse("process_pdf.html", {"request": request, "user": current_user, "active_page": "process_pdf"})

@app.get("/api-key", response_class=HTMLResponse)
async def api_key_page(request: Request, current_user: User = Depends(get_current_user_from_cookie)):
    return login_templates.TemplateResponse("api_key.html", {"request": request, "user": current_user, "active_page": "api_key"})

@app.post("/save-api-key", response_class=HTMLResponse)
async def save_api_key(request: Request, key_type: str = Form(...), key_value: str = Form(...), description: str = Form(None), is_active: str = Form("true"), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user_from_cookie)):
    try:
        # Find the key by type
        from sqlalchemy.future import select
        from app.models.api_key import APIKey
        from app.schemas.api_key import APIKeyCreate, APIKeyUpdate
        from app.services.api_key_service import create_api_key, update_api_key
        
        result = await db.execute(
            select(APIKey).where(APIKey.key_type == key_type)
        )
        db_api_key = result.scalars().first()
        
        if db_api_key is None:
            # If key doesn't exist, create it
            new_key = APIKeyCreate(
                name=f"{key_type.capitalize()} API Key",
                key_type=key_type,
                key_value=key_value,
                is_active=is_active.lower() == "true",
                description=description or f"API key for {key_type}"
            )
            db_api_key, _ = await create_api_key(db, new_key)
            message = "API key created successfully!"
        else:
            # Update the key
            update_data = APIKeyUpdate(
                key_value=key_value,
                description=description,
                is_active=is_active.lower() == "true"
            )
            await update_api_key(db, db_api_key.id, update_data)
            message = "API key updated successfully!"
        
        return login_templates.TemplateResponse(
            "api_key.html", 
            {
                "request": request, 
                "user": current_user, 
                "active_page": "api_key",
                "message": message,
                "message_type": "success"
            }
        )
    except Exception as e:
        return login_templates.TemplateResponse(
            "api_key.html", 
            {
                "request": request, 
                "user": current_user, 
                "active_page": "api_key",
                "message": f"Error: {str(e)}",
                "message_type": "danger"
            }
        )

@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token", path="/")
    return response

@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Find user by email
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    # Check credentials
    if not user or not user.verify_password(form_data.password):
        return login_templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Invalid email or password"}
        )
    
    if not user.is_active:
        return login_templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "User account is inactive"}
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.id, expires_delta=access_token_expires)
    
    # Create response with redirect
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    
    return response

@app.on_event("startup")
async def startup_event():
    """Initialize database and create initial admin user"""
    # Create database tables
    await create_tables()
    
    # Create initial admin user if it doesn't exist
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.future import select
    from app.database import SessionLocal
    from app.models.user import User
    
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        user = result.scalars().first()
        
        if not user:
            print(f"Creating admin user: {settings.ADMIN_EMAIL}")
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=User.get_password_hash(settings.ADMIN_PASSWORD),
                is_active=True,
                is_admin=True,
                full_name="Admin User"
            )
            db.add(admin_user)
            await db.commit()

@app.get("/")
async def root(request: Request):
    """Redirect to login page"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
