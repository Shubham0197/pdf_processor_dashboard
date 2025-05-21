from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os
import json
from datetime import datetime, timedelta

from app.database import get_db
from app.models.batch import BatchJob
from app.models.job import ProcessingJob
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate
from app.services.api_key_service import create_api_key, update_api_key, delete_api_key
from app.utils.auth import get_current_user, get_current_admin_user

dashboard_router = APIRouter()
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Cookie-based authentication
from fastapi import Cookie, Header
from jose import jwt, JWTError
from app.config import settings

async def get_current_user_from_cookie(
    db: AsyncSession = Depends(get_db),
    access_token: str = Cookie(None, alias="access_token")
) -> User:
    """Get current user from cookie"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Remove 'Bearer ' prefix if present
    if access_token.startswith("Bearer "):
        access_token = access_token[7:]
    
    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user

# Helper function to get dashboard stats
async def get_dashboard_stats(db: AsyncSession):
    """Get statistics for dashboard"""
    # Get total counts
    total_batches_result = await db.execute(select(BatchJob))
    total_batches = len(total_batches_result.scalars().all())
    
    total_jobs_result = await db.execute(select(ProcessingJob))
    total_jobs = len(total_jobs_result.scalars().all())
    
    # Get counts by status
    pending_batches_result = await db.execute(select(BatchJob).where(BatchJob.status == "pending"))
    pending_batches = len(pending_batches_result.scalars().all())
    
    processing_batches_result = await db.execute(select(BatchJob).where(BatchJob.status == "processing"))
    processing_batches = len(processing_batches_result.scalars().all())
    
    completed_batches_result = await db.execute(select(BatchJob).where(BatchJob.status == "completed"))
    completed_batches = len(completed_batches_result.scalars().all())
    
    failed_batches_result = await db.execute(select(BatchJob).where(BatchJob.status == "failed"))
    failed_batches = len(failed_batches_result.scalars().all())
    
    # Get recent batches
    recent_batches_result = await db.execute(
        select(BatchJob).order_by(BatchJob.created_at.desc()).limit(5)
    )
    recent_batches = recent_batches_result.scalars().all()
    
    # Get recent jobs
    recent_jobs_result = await db.execute(
        select(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(5)
    )
    recent_jobs = recent_jobs_result.scalars().all()
    
    # Calculate success rate
    success_rate = 0
    if total_jobs > 0:
        completed_jobs_result = await db.execute(select(ProcessingJob).where(ProcessingJob.status == "completed"))
        completed_jobs = len(completed_jobs_result.scalars().all())
        success_rate = (completed_jobs / total_jobs) * 100
    
    # Get processing time stats
    processing_time_result = await db.execute(
        select(ProcessingJob.processing_time).where(
            ProcessingJob.processing_time.is_not(None)
        )
    )
    processing_times = [time for time in processing_time_result.scalars().all() if time]
    
    avg_processing_time = 0
    if processing_times:
        avg_processing_time = sum(processing_times) / len(processing_times)
    
    # Get daily stats for the last 7 days
    daily_stats = []
    for i in range(7, 0, -1):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        # Get jobs created on this date
        day_start = datetime(date.year, date.month, date.day)
        day_end = day_start + timedelta(days=1)
        
        jobs_result = await db.execute(
            select(ProcessingJob).where(
                ProcessingJob.created_at >= day_start,
                ProcessingJob.created_at < day_end
            )
        )
        jobs = jobs_result.scalars().all()
        
        completed = len([j for j in jobs if j.status == "completed"])
        failed = len([j for j in jobs if j.status == "failed"])
        
        daily_stats.append({
            "date": date_str,
            "total": len(jobs),
            "completed": completed,
            "failed": failed
        })
    
    return {
        "total_batches": total_batches,
        "total_jobs": total_jobs,
        "pending_batches": pending_batches,
        "processing_batches": processing_batches,
        "completed_batches": completed_batches,
        "failed_batches": failed_batches,
        "recent_batches": recent_batches,
        "recent_jobs": recent_jobs,
        "success_rate": round(success_rate, 2),
        "avg_processing_time": round(avg_processing_time / 1000, 2) if avg_processing_time else 0,  # Convert to seconds
        "daily_stats": daily_stats
    }

# Dashboard routes
@dashboard_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Dashboard home page"""
    stats = await get_dashboard_stats(db)
    
    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "stats": stats,
            "user": current_user,
            "active_page": "dashboard"
        }
    )

@dashboard_router.get("/dashboard/batches", response_class=HTMLResponse)
async def batches_page(
    request: Request,
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Batch jobs listing page"""
    # Get total count for pagination
    total_result = await db.execute(select(BatchJob))
    total = len(total_result.scalars().all())
    
    # Get paginated batches
    offset = (page - 1) * limit
    batches_result = await db.execute(
        select(BatchJob).order_by(BatchJob.created_at.desc()).offset(offset).limit(limit)
    )
    batches = batches_result.scalars().all()
    
    # Calculate pagination info
    total_pages = (total + limit - 1) // limit
    
    return templates.TemplateResponse(
        "dashboard/batches.html",
        {
            "request": request,
            "batches": batches,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "user": current_user,
            "active_page": "batches"
        }
    )

@dashboard_router.get("/dashboard/batch/{batch_id}", response_class=HTMLResponse)
async def batch_detail(
    request: Request,
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Batch job detail page"""
    # Get batch
    batch_result = await db.execute(select(BatchJob).where(BatchJob.batch_id == batch_id))
    batch = batch_result.scalars().first()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Get jobs for this batch
    jobs_result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.batch_id == batch.id)
    )
    jobs = jobs_result.scalars().all()
    
    return templates.TemplateResponse(
        "dashboard/batch_detail.html",
        {
            "request": request,
            "batch": batch,
            "jobs": jobs,
            "user": current_user,
            "active_page": "batches"
        }
    )

@dashboard_router.get("/dashboard/job/{job_id}", response_class=HTMLResponse)
async def job_detail(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Job detail page"""
    # Get job
    job_result = await db.execute(select(ProcessingJob).where(ProcessingJob.job_id == job_id))
    job = job_result.scalars().first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return templates.TemplateResponse(
        "dashboard/job_detail.html",
        {
            "request": request,
            "job": job,
            "user": current_user,
            "active_page": "jobs"
        }
    )

@dashboard_router.get("/dashboard/api-keys", response_class=HTMLResponse)
async def api_keys_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """API Key management page"""
    # Get API keys
    api_keys_result = await db.execute(select(APIKey))
    api_keys = api_keys_result.scalars().all()
    
    return templates.TemplateResponse(
        "dashboard/api_keys.html",
        {
            "request": request,
            "api_keys": api_keys,
            "user": current_user,
            "active_page": "api_keys"
        }
    )

@dashboard_router.post("/dashboard/api-keys/create")
async def create_api_key_route(
    request: Request,
    name: str = Form(...),
    key_type: str = Form(...),
    key_value: str = Form(None),
    description: str = Form(None),
    is_active: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Create a new API key"""
    api_key = APIKeyCreate(
        name=name,
        key_type=key_type,
        key_value=key_value,
        description=description,
        is_active=is_active
    )
    
    db_api_key, key_value = await create_api_key(db, api_key)
    
    # Redirect back to API keys page with success message
    return RedirectResponse(
        url="/dashboard/api-keys?success=true&message=API+key+created+successfully",
        status_code=status.HTTP_303_SEE_OTHER
    )

@dashboard_router.post("/dashboard/api-keys/{key_id}/update")
async def update_api_key_route(
    request: Request,
    key_id: int,
    name: str = Form(...),
    is_active: bool = Form(None),
    description: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Update an API key"""
    api_key = APIKeyUpdate(
        name=name,
        is_active=is_active if is_active is not None else True,
        description=description
    )
    
    await update_api_key(db, key_id, api_key)
    
    # Redirect back to API keys page with success message
    return RedirectResponse(
        url="/dashboard/api-keys?success=true&message=API+key+updated+successfully",
        status_code=status.HTTP_303_SEE_OTHER
    )

@dashboard_router.post("/dashboard/api-keys/{key_id}/delete")
async def delete_api_key_route(
    request: Request,
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Delete an API key"""
    await delete_api_key(db, key_id)
    
    # Redirect back to API keys page with success message
    return RedirectResponse(
        url="/dashboard/api-keys?success=true&message=API+key+deleted+successfully",
        status_code=status.HTTP_303_SEE_OTHER
    )
