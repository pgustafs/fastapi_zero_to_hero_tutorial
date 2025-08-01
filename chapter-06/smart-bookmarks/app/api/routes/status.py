import re
from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings

# Import the response schema
from app.schemas.status import StatusResponse

# Create an API router
router = APIRouter()


def mask_db_url(url: str) -> str:
    """Masks credentials and sensitive parts of a database URL."""
    if not isinstance(url, str):
        return "Invalid URL format"
    if url.startswith("sqlite"):
        return re.sub(r"(\w+)\.db", "********.db", url)
    return re.sub(r"://(.*?):(.*?)@", r"://********:********@", url)


@router.get("/", response_model=StatusResponse)
async def get_status():
    """
    Returns the current server time and a masked database URL for status checks.
    """
    current_time = datetime.now(timezone.utc)
    masked_url = mask_db_url(settings.DATABASE_URL)

    return {
        "current_time": current_time,
        "database_url": masked_url,
    }
