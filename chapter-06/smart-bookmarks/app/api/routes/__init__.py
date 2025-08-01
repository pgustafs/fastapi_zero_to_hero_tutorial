from fastapi import APIRouter
from . import health, status, users, bookmarks, tags, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(status.router, prefix="/status", tags=["status"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
