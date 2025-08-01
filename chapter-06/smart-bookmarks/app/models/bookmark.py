from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Index
from sqlmodel import Field, SQLModel, Relationship, Column, Enum as SQLModelEnum
from pydantic import field_validator
from enum import Enum

# Import the link model
from .bookmark_tag import BookmarkTag

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from .user import User
    from .tag import Tag


class ProcessingStatus(str, Enum):
    """Status of AI content processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Default for non-AI bookmarks


class BookmarkBase(SQLModel):
    """Shared properties for Bookmark models"""

    url: str = Field(index=True, max_length=2048)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_favorite: bool = Field(default=False)
    views_count: int = Field(default=0)
    ai_enabled: bool = Field(default=False, description="Enable AI content generation")

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class Bookmark(BookmarkBase, table=True):
    """Database model for bookmarks"""

    __tablename__ = "bookmarks"

    __table_args__ = (
        Index("ix_bookmarks_user_id_created_at", "user_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    ai_status: ProcessingStatus = Field(
        default=ProcessingStatus.SKIPPED,
        sa_column=Column(SQLModelEnum(ProcessingStatus)),
    )
    ai_error: Optional[str] = Field(default=None, max_length=500)

    # Relationships
    owner: Optional["User"] = Relationship(back_populates="bookmarks")
    tags: List["Tag"] = Relationship(
        back_populates="bookmarks",
        link_model=BookmarkTag,
        # enable cascading deletes
        sa_relationship_kwargs={"cascade": "all, delete"},
    )


class BookmarkCreate(BookmarkBase):
    """Schema for creating a bookmark"""

    tags: Optional[List[str]] = Field(default=[], max_items=10)
    ai_enabled: bool = Field(default=True)


class BookmarkRead(BookmarkBase):
    """Schema for reading bookmark data"""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []
    ai_status: ProcessingStatus


class BookmarkUpdate(SQLModel):
    """Schema for updating bookmark data"""

    url: Optional[str] = Field(None, max_length=2048)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    is_favorite: Optional[bool] = None
    tags: Optional[List[str]] = Field(None, max_items=10)


class BookmarkBulkDelete(SQLModel):
    """Schema for bulk deleting bookmarks."""

    bookmark_ids: List[int]
