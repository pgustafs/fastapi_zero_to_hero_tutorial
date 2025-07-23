from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

# Import the link model
from .bookmark_tag import BookmarkTag

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from .bookmark import Bookmark


class TagBase(SQLModel):
    """Shared properties for Tag models"""

    name: str = Field(unique=True, index=True, max_length=50)


class Tag(TagBase, table=True):
    """Database model for tags"""

    __tablename__ = "tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    bookmarks: List["Bookmark"] = Relationship(
        back_populates="tags",
        link_model=BookmarkTag,
        sa_relationship_kwargs={"cascade": "all, delete"},
    )


class TagRead(TagBase):
    """Schema for reading tag data"""

    id: int
    created_at: datetime
    bookmark_count: Optional[int] = 0
