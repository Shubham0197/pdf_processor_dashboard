from fastapi import APIRouter
from app.api.endpoints import batch, job, auth, api_keys, document, processing

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api keys"])
api_router.include_router(batch.router, prefix="/batch", tags=["batch processing"])
api_router.include_router(job.router, prefix="/jobs", tags=["job processing"])
api_router.include_router(document.router, prefix="/documents", tags=["document management"])
api_router.include_router(processing.router, prefix="/processing", tags=["processing status"])
