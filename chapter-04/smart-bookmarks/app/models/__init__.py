# Import models in an order that resolves dependencies

# Base models without relationships first (or stand-alone)
from .user import User, UserCreate, UserRead, UserUpdate

# Import the link model before the models that use it
from .bookmark_tag import BookmarkTag

# Import the models that have relationships
from .tag import Tag, TagRead
from .bookmark import (
    Bookmark,
    BookmarkCreate,
    BookmarkRead,
    BookmarkUpdate,
    BookmarkBulkDelete,
)

# This ensures all models are available when importing from app.models
__all__ = [
    "User",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "Bookmark",
    "BookmarkCreate",
    "BookmarkRead",
    "BookmarkUpdate",
    "Tag",
    "TagRead",
    "BookmarkTag",
    "BookmarkBulkDelete",
]
