"""
Main dashboard router initialization
"""
from fastapi import APIRouter

from app.dashboard.routes import dashboard_router
from app.dashboard.routes_document import router as document_router

# Create main dashboard router
main_dashboard_router = APIRouter()

# Include all dashboard routes
main_dashboard_router.include_router(dashboard_router)
main_dashboard_router.include_router(document_router, prefix="/dashboard")

# Export the combined router
dashboard_router = main_dashboard_router
