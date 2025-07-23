from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db, get_session
from app.api.routes import api_router  # Import the master router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App startup...")
    if get_session not in app.dependency_overrides:
        init_db()
    yield
    print("App shutdown...")


app = FastAPI(
    title=settings.PROJECT_NAME,  # Change
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the master API router with the global prefix
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
    }
