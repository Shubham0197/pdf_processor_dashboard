from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
import os
import json
from datetime import datetime, timedelta

from app.database import get_db
from app.models.batch import BatchJob
from app.models.processing import ProcessingRequest, AIProcessingResult
from app.models.document import PDFDocument, BatchDocument
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
    import logging
    logger = logging.getLogger("app.auth")
    logger.setLevel(logging.DEBUG)
    
    # Add console handler if not already added
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - COOKIE AUTH - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    logger.debug(f"Cookie auth attempt with token: {'Present (starts with: ' + access_token[:10] + '...)' if access_token else 'None'}")
    """Get current user from cookie"""
    if not access_token:
        logger.error("Cookie auth failed: No access_token cookie")
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
            logger.error("Cookie auth failed: No user ID in token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        logger.debug(f"Token decoded successfully. User ID: {user_id}")
    except Exception as e:
        logger.error(f"Cookie auth failed: Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    
    if user is None:
        logger.error(f"Cookie auth failed: User ID {user_id} not found in database")
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        logger.error(f"Cookie auth failed: User ID {user_id} is inactive")
        raise HTTPException(status_code=400, detail="Inactive user")
    
    logger.debug(f"Cookie auth successful for user: {user.email}")
    
    return user

# Helper function to get dashboard stats
async def get_dashboard_stats(db: AsyncSession):
    """Get enhanced statistics for dashboard using new schema"""
    # Get total counts
    total_batches_result = await db.execute(select(BatchJob))
    total_batches = len(total_batches_result.scalars().all())
    
    total_requests_result = await db.execute(select(ProcessingRequest))
    total_requests = len(total_requests_result.scalars().all())
    
    total_documents_result = await db.execute(select(PDFDocument))
    total_documents = len(total_documents_result.scalars().all())
    
    total_ai_results_result = await db.execute(select(AIProcessingResult))
    total_ai_results = len(total_ai_results_result.scalars().all())
    
    # Get counts by status for processing requests
    pending_requests_result = await db.execute(select(ProcessingRequest).where(ProcessingRequest.status == "processing"))
    pending_requests = len(pending_requests_result.scalars().all())
    
    completed_requests_result = await db.execute(select(ProcessingRequest).where(ProcessingRequest.status == "completed"))
    completed_requests = len(completed_requests_result.scalars().all())
    
    failed_requests_result = await db.execute(select(ProcessingRequest).where(ProcessingRequest.status == "failed"))
    failed_requests = len(failed_requests_result.scalars().all())
    
    # Get batch status counts
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
    
    # Get recent processing requests
    recent_requests_result = await db.execute(
        select(ProcessingRequest).order_by(ProcessingRequest.created_at.desc()).limit(5)
    )
    recent_requests = recent_requests_result.scalars().all()
    
    # Calculate success rate for processing requests
    success_rate = 0
    if total_requests > 0:
        success_rate = (completed_requests / total_requests) * 100
    
    # Get processing time stats from AIProcessingResult table
    processing_time_result = await db.execute(
        select(AIProcessingResult.processing_time_ms).where(
            AIProcessingResult.processing_time_ms.is_not(None)
        )
    )
    processing_times = [time for time in processing_time_result.scalars().all() if time]
    
    avg_processing_time = 0
    if processing_times:
        avg_processing_time = sum(processing_times) / len(processing_times)
    
    # Get AI model usage statistics
    ai_model_stats_result = await db.execute(
        select(AIProcessingResult.ai_model_used, func.count(AIProcessingResult.id))
        .group_by(AIProcessingResult.ai_model_used)
    )
    ai_model_stats = {model: count for model, count in ai_model_stats_result.all() if model}
    
    # Get processing type statistics  
    processing_type_stats_result = await db.execute(
        select(AIProcessingResult.processing_type, func.count(AIProcessingResult.id))
        .group_by(AIProcessingResult.processing_type)
    )
    processing_type_stats = {ptype: count for ptype, count in processing_type_stats_result.all() if ptype}
    
    # Get token usage statistics
    total_tokens_result = await db.execute(
        select(func.sum(AIProcessingResult.ai_tokens_used)).where(
            AIProcessingResult.ai_tokens_used.is_not(None)
        )
    )
    total_tokens = total_tokens_result.scalar() or 0
    
    # Get daily stats for the last 7 days
    daily_stats = []
    for i in range(7, 0, -1):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        # Get processing requests created on this date
        day_start = datetime(date.year, date.month, date.day)
        day_end = day_start + timedelta(days=1)
        
        requests_result = await db.execute(
            select(ProcessingRequest).where(
                ProcessingRequest.created_at >= day_start,
                ProcessingRequest.created_at < day_end
            )
        )
        requests = requests_result.scalars().all()
        
        completed = len([r for r in requests if r.status == "completed"])
        failed = len([r for r in requests if r.status == "failed"])
        processing = len([r for r in requests if r.status == "processing"])
        
        daily_stats.append({
            "date": date_str,
            "total": len(requests),
            "completed": completed,
            "failed": failed,
            "processing": processing
        })
    
    # Calculate error rate
    error_rate = 0
    if total_ai_results > 0:
        error_results_result = await db.execute(
            select(AIProcessingResult).where(AIProcessingResult.status == "failed")
        )
        error_results = len(error_results_result.scalars().all())
        error_rate = (error_results / total_ai_results) * 100
    
    return {
        # Basic counts
        "total_batches": total_batches,
        "total_requests": total_requests,
        "total_documents": total_documents,
        "total_ai_results": total_ai_results,
        "total_jobs": total_requests,  # For compatibility with template
        
        # Processing request status
        "pending_requests": pending_requests,
        "completed_requests": completed_requests,
        "failed_requests": failed_requests,
        
        # Batch status
        "pending_batches": pending_batches,
        "processing_batches": processing_batches,
        "completed_batches": completed_batches,
        "failed_batches": failed_batches,
        
        # Recent data
        "recent_batches": recent_batches,
        "recent_requests": recent_requests,
        "recent_jobs": recent_requests,  # For compatibility with template
        
        # Performance metrics
        "success_rate": round(success_rate, 2),
        "error_rate": round(error_rate, 2),
        "avg_processing_time": round(avg_processing_time / 1000, 2) if avg_processing_time else 0,  # Convert to seconds
        "total_tokens": total_tokens,
        
        # AI analytics
        "ai_model_stats": ai_model_stats,
        "processing_type_stats": processing_type_stats,
        
        # Time series data
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
    
    # Identify single PDF processing jobs from their request_data
    for batch in batches:
        # Check if this is a single PDF processing job (from process-pdf page)
        if batch.request_data and isinstance(batch.request_data, dict):
            source = batch.request_data.get("source", "")
            batch.is_single_pdf = (source == "single_pdf_processing")
            
            # Include the file name or URL for display in the UI
            if batch.is_single_pdf and "file" in batch.request_data:
                batch.pdf_url = batch.request_data.get("file", "")
                # Get just the filename from the URL for display
                batch.pdf_name = batch.pdf_url.split("/")[-1]
        else:
            batch.is_single_pdf = False
    
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
    """Batch job detail page with enhanced schema"""
    # Get batch
    batch_result = await db.execute(select(BatchJob).where(BatchJob.batch_id == batch_id))
    batch = batch_result.scalars().first()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Check if this is a single PDF processing job
    if batch.request_data and isinstance(batch.request_data, dict):
        source = batch.request_data.get("source", "")
        batch.is_single_pdf = (source == "single_pdf_processing")
        
        # Include the file name or URL for display in the UI
        if batch.is_single_pdf and "file" in batch.request_data:
            batch.pdf_url = batch.request_data.get("file", "")
            batch.pdf_name = batch.pdf_url.split("/")[-1]
    else:
        batch.is_single_pdf = False
    
    # Get processing requests for this batch with document information
    processing_requests_result = await db.execute(
        select(ProcessingRequest, PDFDocument)
        .join(PDFDocument, ProcessingRequest.document_id == PDFDocument.id, isouter=True)
        .where(ProcessingRequest.batch_id == batch.id)
        .order_by(ProcessingRequest.created_at.desc())
    )
    processing_data = processing_requests_result.all()
    
    # Get AI processing results for these requests
    processing_request_ids = [req.id for req, doc in processing_data]
    ai_results_result = await db.execute(
        select(AIProcessingResult)
        .where(AIProcessingResult.processing_request_id.in_(processing_request_ids))
        .order_by(AIProcessingResult.created_at.desc())
    )
    ai_results = ai_results_result.scalars().all()
    
    # Group AI results by processing request ID
    ai_results_by_request = {}
    for result in ai_results:
        if result.processing_request_id not in ai_results_by_request:
            ai_results_by_request[result.processing_request_id] = []
        ai_results_by_request[result.processing_request_id].append(result)
    
    # Prepare enhanced job data with AI results
    enhanced_jobs = []
    for processing_request, document in processing_data:
        job_ai_results = ai_results_by_request.get(processing_request.id, [])
        
        # Calculate total processing time from AI results
        total_processing_time = sum(result.processing_time_ms for result in job_ai_results if result.processing_time_ms)
        
        # Determine overall status (failed if any AI result failed)
        overall_status = processing_request.status
        has_failures = any(result.status == 'failed' for result in job_ai_results)
        if has_failures and overall_status == 'completed':
            overall_status = 'partial_failure'
        
        # Extract file name from URL with proper error handling
        file_name = "Unknown"
        file_url = None
        
        if document and hasattr(document, 'file_url') and document.file_url:
            file_url = document.file_url
            try:
                file_name = file_url.split("/")[-1]
            except (AttributeError, IndexError):
                file_name = "Unknown"
        elif batch.is_single_pdf and batch.request_data and "file" in batch.request_data:
            # Fallback to batch request data for single PDF processing
            file_url = batch.request_data.get("file", "")
            try:
                file_name = file_url.split("/")[-1] if file_url else "Unknown"
            except (AttributeError, IndexError):
                file_name = "Unknown"
        
        enhanced_job = {
            'id': str(processing_request.id),
            'job_id': str(processing_request.id),  # For compatibility with template
            'file_name': file_name,
            'file_url': file_url or "",
            'status': overall_status,
            'created_at': processing_request.created_at,
            'completed_at': processing_request.completed_at,
            'processing_time': total_processing_time,
            'processing_request': processing_request,
            'document': document,
            'ai_results': job_ai_results,
            'metadata_result': next((r for r in job_ai_results if r.processing_type == 'metadata'), None),
            'references_result': next((r for r in job_ai_results if r.processing_type == 'references'), None),
            'error_results': [r for r in job_ai_results if r.processing_type == 'processing_error'],
        }
        enhanced_jobs.append(enhanced_job)
    
    return templates.TemplateResponse(
        "dashboard/batch_detail.html",
        {
            "request": request,
            "batch": batch,
            "jobs": enhanced_jobs,
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
    # Get job with batch relationship eagerly loaded
    job_result = await db.execute(
        select(ProcessingRequest)
        .options(joinedload(ProcessingRequest.batch))
        .where(ProcessingRequest.job_id == job_id)
    )
    job = job_result.scalars().first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Helper function to make dictionaries JSON serializable
    def make_serializable(obj):
        if isinstance(obj, dict):
            # Create a new dict with string keys
            result = {}
            for k, v in obj.items():
                # Convert any non-string keys to strings
                if not isinstance(k, (str, int, float, bool, type(None))):
                    k = str(k)
                # Recursively convert values
                result[k] = make_serializable(v)
            return result
        elif isinstance(obj, list):
            # Convert list items
            return [make_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Convert object to dict if it has __dict__
            return make_serializable(obj.__dict__)
        elif hasattr(obj, 'dict'):  # For Pydantic models
            return make_serializable(obj.dict())
        else:
            # Return primitives as is
            return obj
    
    # Handle serialization of metadata, references, and other fields
    if hasattr(job, 'metadata') and job.metadata:
        try:
            job.metadata = make_serializable(job.metadata)
        except Exception as e:
            job.metadata = {"error": f"Could not serialize metadata: {str(e)}"}
    
    # Similarly handle references, which could also be objects
    if hasattr(job, 'references') and job.references:
        try:
            job.references = make_serializable(job.references)
        except Exception as e:
            job.references = {"error": f"Could not serialize references: {str(e)}"}
            
    # Handle webhook response serialization as well
    if hasattr(job, 'webhook_response') and job.webhook_response:
        try:
            job.webhook_response = make_serializable(job.webhook_response)
        except Exception as e:
            job.webhook_response = {"error": f"Could not serialize webhook response: {str(e)}"}
    
    # If we have a batch, prepare batch info for display
    if job.batch:
        # Make sure batch_id is available for template
        batch_id = job.batch.batch_id
    
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
