from fastapi import APIRouter
from app.core.config import settings

# Create an API router
router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,  # ADD
    }
