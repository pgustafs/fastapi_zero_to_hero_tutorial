from typing import List
from fastapi import APIRouter, HTTPException, status, Query
from sqlmodel import select
from app.api.deps import SessionDep, CurrentUser
from app.models import User, UserCreate, UserRead, UserUpdate
from app.core.security import get_password_hash

router = APIRouter()


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: SessionDep):
    """Create a new user"""
    # Check if user exists
    existing_user = db.exec(
        select(User).where(
            (User.username == user_in.username) | (User.email == user_in.email)
        )
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    # Create new user
    user = User(
        **user_in.model_dump(exclude={"password"}),
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.get("/", response_model=List[UserRead])
def read_users(
    db: SessionDep,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of items to return"),
):
    """Get list of users"""
    users = db.exec(select(User).offset(skip).limit(limit)).all()

    return users


@router.get("/me", response_model=UserRead)
def read_user_me(current_user: CurrentUser):
    """Get current user"""
    return current_user


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: SessionDep):
    """Get user by ID"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int, user_in: UserUpdate, db: SessionDep, current_user: CurrentUser
):
    """Update user (only own profile)"""
    # Check if user can update this profile
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Can only update own profile"
        )

    # Get user
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update fields
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    from datetime import datetime

    user.updated_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: SessionDep, current_user: CurrentUser):
    """Delete user (only own profile)"""
    # Check if user can delete this profile
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Can only delete own profile"
        )

    # Get user
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Delete user (cascade will handle bookmarks)
    db.delete(user)
    db.commit()
