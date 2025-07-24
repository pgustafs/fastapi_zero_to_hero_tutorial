from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

# Add this block to help the ruff linter understand the 'Bookmark' type
if TYPE_CHECKING:
    from .bookmark import Bookmark


class UserBase(SQLModel):
    """Shared properties for User models"""

    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    """Database model for users"""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    bookmarks: List["Bookmark"] = Relationship(back_populates="owner")


class UserCreate(UserBase):
    """Schema for creating a user"""

    password: str = Field(min_length=8, max_length=100)


class UserRead(UserBase):
    """Schema for reading user data"""

    id: int
    created_at: datetime
    updated_at: datetime


class UserUpdate(SQLModel):
    """Schema for updating user data"""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
