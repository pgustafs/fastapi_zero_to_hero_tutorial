from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

# Import the link model
from .bookmark_tag import BookmarkTag

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from .user import User
    from .tag import Tag


class BookmarkBase(SQLModel):
    """Shared properties for Bookmark models"""

    url: str = Field(index=True, max_length=2048)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_favorite: bool = Field(default=False)


class Bookmark(BookmarkBase, table=True):
    """Database model for bookmarks"""

    __tablename__ = "bookmarks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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


class BookmarkRead(BookmarkBase):
    """Schema for reading bookmark data"""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []


class BookmarkUpdate(SQLModel):
    """Schema for updating bookmark data"""

    url: Optional[str] = Field(None, max_length=2048)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_favorite: Optional[bool] = None
    tags: Optional[List[str]] = Field(None, max_items=10)
