from typing import Optional
from sqlmodel import Field, SQLModel


# Link table for many-to-many relationship
class BookmarkTag(SQLModel, table=True):
    """Link table for bookmark-tag relationship"""

    __tablename__ = "bookmark_tags"

    bookmark_id: Optional[int] = Field(
        default=None, foreign_key="bookmarks.id", primary_key=True
    )
    tag_id: Optional[int] = Field(default=None, foreign_key="tags.id", primary_key=True)
