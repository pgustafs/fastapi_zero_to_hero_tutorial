from datetime import timedelta

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
)
from sqlmodel import select, or_

from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
)
from app.core.rate_limit import login_limiter
from app.api.deps import SessionDep, CurrentUser
from app.models import User, UserRead
from app.schemas.auth import Token, LoginRequest, RegisterRequest

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: RegisterRequest,
    db: SessionDep,
):
    """
    Register a new user

    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: At least 8 characters
    - **full_name**: Optional full name
    """
    # Check if user exists
    existing = db.exec(
        select(User).where(
            or_(
                User.username == user_in.username,
                User.email == user_in.email,
            )
        )
    ).first()
    if existing:
        detail = (
            "Username already registered"
            if existing.username == user_in.username
            else "Email already registered"
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=detail)

    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: LoginRequest,
    request: Request,
    db: SessionDep,
):
    """
    Login to get access token

    - **username**: Username or email
    - **password**: User password

    Returns JWT access token
    """
    client_ip = request.client.host
    login_limiter.check_rate_limit(client_ip)

    user = db.exec(
        select(User).where(
            or_(
                User.username == form_data.username,
                User.email == form_data.username,
            )
        )
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        login_limiter.add_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = create_access_token(
        subject=user.username,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/refresh", response_model=Token)
def refresh_token(
    current_user: CurrentUser,
):
    """
    Refresh access token — requires a valid current token
    """
    access_token = create_access_token(
        subject=current_user.username,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
def read_users_me(
    current_user: CurrentUser,
):
    """
    Get the current authenticated user — 403 if no token, 401 if invalid
    """
    return current_user
