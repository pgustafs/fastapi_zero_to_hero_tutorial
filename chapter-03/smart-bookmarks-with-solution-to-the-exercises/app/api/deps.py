from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlmodel import Session
from app.core.database import get_session
from app.models import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Security scheme for JWT
security = HTTPBearer()


# Alias for DB session dependency
SessionDep = Annotated[Session, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: SessionDep,
) -> User:
    """Get current authenticated user (placeholder for now)"""
    # We'll implement this properly in the authentication chapter
    # For now, return a mock user for testing
    from sqlmodel import select

    # This is temporary - we'll replace with real JWT validation
    user = db.exec(select(User).where(User.username == "testuser")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


# Type alias for current user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]
