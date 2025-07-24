from typing import List
from fastapi import APIRouter, Query
from sqlmodel import select, func
from app.api.deps import SessionDep, CurrentUser
from app.models import Tag, TagRead, BookmarkTag, Bookmark

router = APIRouter()


@router.get("/", response_model=List[TagRead])
def read_tags(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """Get all tags used by the current user"""
    # Query tags with bookmark count
    tags_query = (
        select(Tag, func.count(BookmarkTag.bookmark_id).label("bookmark_count"))
        .join(BookmarkTag)
        .join(Bookmark)
        .where(Bookmark.user_id == current_user.id)
        .group_by(Tag.id)
        .order_by(func.count(BookmarkTag.bookmark_id).desc())
        .offset(skip)
        .limit(limit)
    )

    results = db.exec(tags_query).all()

    return [
        TagRead(
            id=tag.id, name=tag.name, created_at=tag.created_at, bookmark_count=count
        )
        for tag, count in results
    ]


@router.get("/popular", response_model=List[dict])
def read_popular_tags(
    db: SessionDep,
    limit: int = Query(10, ge=1, le=50),
):
    """Get most popular tags across all users"""
    popular_tags = db.exec(
        select(Tag.name, func.count(BookmarkTag.bookmark_id).label("usage_count"))
        .join(BookmarkTag)
        .group_by(Tag.name)
        .order_by(func.count(BookmarkTag.bookmark_id).desc())
        .limit(limit)
    ).all()

    return [{"name": name, "usage_count": count} for name, count in popular_tags]
