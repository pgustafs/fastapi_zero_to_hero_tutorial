from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Request
from sqlmodel import select, func, or_
from app.api.deps import SessionDep, CurrentUser
from enum import Enum
import csv
import io
from fastapi.responses import StreamingResponse
from app.models import (
    Bookmark,
    BookmarkCreate,
    BookmarkRead,
    BookmarkUpdate,
    BookmarkBulkDelete,
    Tag,
    BookmarkTag,
    ProcessingStatus,
)
from app.tasks.ai_tasks import process_bookmark_content
import logging

# Add a logger
logger = logging.getLogger(__name__)

router = APIRouter()


class BookmarkSortField(str, Enum):
    """Fields to sort bookmarks by."""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    TITLE = "title"
    IS_FAVORITE = "is_favorite"


@router.post("/", response_model=BookmarkRead, status_code=status.HTTP_201_CREATED)
def create_bookmark(
    bookmark_in: BookmarkCreate,
    db: SessionDep,
    current_user: CurrentUser,
    request: Request,
):
    """Create a new bookmark with optional AI enhancement"""
    # Create the initial bookmark object
    bookmark = Bookmark(
        **bookmark_in.model_dump(exclude={"tags"}),
        user_id=current_user.id,
        ai_status=ProcessingStatus.PENDING
        if bookmark_in.ai_enabled
        else ProcessingStatus.SKIPPED,
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    # If AI is NOT enabled, use the explicit, manual tag handling logic
    if not bookmark.ai_enabled and bookmark_in.tags:
        for tag_name in set(bookmark_in.tags):
            tag = db.exec(select(Tag).where(Tag.name == tag_name.lower())).first()
            if not tag:
                tag = Tag(name=tag_name.lower())
                db.add(tag)
                db.commit()
                db.refresh(tag)

            # Manually create the link table entry
            bookmark_tag = BookmarkTag(bookmark_id=bookmark.id, tag_id=tag.id)
            db.add(bookmark_tag)

        db.commit()
        db.refresh(bookmark)

    # Log the creation event
    log_context = {
        "event": "CREATE_BOOKMARK",
        "bookmark_id": bookmark.id,
        "user_id": current_user.id,
        "request_id": getattr(request.state, "request_id", None),
    }
    logger.info("Bookmark created", extra={"extra_info": log_context})

    # Queue AI processing if enabled
    if bookmark.ai_enabled:
        try:
            process_bookmark_content.delay(
                bookmark_id=bookmark.id,
                user_id=current_user.id,
                request_id=getattr(request.state, "request_id", None),
            )
        except Exception as e:
            logger.error(
                f"Failed to queue AI processing for bookmark {bookmark.id}: {e}"
            )
            bookmark.ai_status = ProcessingStatus.FAILED
            bookmark.ai_error = "Failed to queue processing task."
            db.add(bookmark)
            db.commit()
            db.refresh(bookmark)

    # Manually construct the response model
    return BookmarkRead(
        **bookmark.model_dump(exclude={"tags", "tags_from_relationship"}),
        tags=[tag.name for tag in bookmark.tags],
    )


@router.get("/", response_model=List[BookmarkRead])
def read_bookmarks(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search in title and description"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    is_favorite: Optional[bool] = Query(None, description="Filter favorites only"),
    sort_by: BookmarkSortField = Query(
        BookmarkSortField.CREATED_AT, description="Field to sort by"
    ),
    sort_order: str = Query(
        "desc", description="Sort order (asc or desc)", pattern="^(asc|desc)$"
    ),
):
    """Get user's bookmarks with optional filtering"""
    # Base query
    query = select(Bookmark).where(Bookmark.user_id == current_user.id)

    # Apply filters
    if search:
        search_filter = or_(
            Bookmark.title.contains(search),
            Bookmark.description.contains(search),
            Bookmark.url.contains(search),
        )
        query = query.where(search_filter)

    if is_favorite is not None:
        query = query.where(Bookmark.is_favorite == is_favorite)

    if tag:
        # Join with tags
        query = query.join(BookmarkTag).join(Tag).where(Tag.name == tag.lower())

    sort_column = getattr(Bookmark, sort_by.value)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Execute query
    bookmarks = db.exec(
        query.order_by(Bookmark.created_at.desc()).offset(skip).limit(limit)
    ).all()

    # Format response with tags
    result = []
    for bookmark in bookmarks:
        bookmark_dict = bookmark.model_dump()
        bookmark_dict["tags"] = [tag.name for tag in bookmark.tags]
        result.append(BookmarkRead(**bookmark_dict))

    return result


@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
def bulk_delete_bookmarks(
    delete_in: BookmarkBulkDelete, db: SessionDep, current_user: CurrentUser
):
    """Delete multiple bookmarks at once."""
    # Query for all bookmarks that match the provided IDs AND belong to the current user
    bookmarks_to_delete = db.exec(
        select(Bookmark).where(
            Bookmark.id.in_(delete_in.bookmark_ids), Bookmark.user_id == current_user.id
        )
    ).all()

    if not bookmarks_to_delete:
        # You can choose to raise an error or just do nothing
        return

    for bookmark in bookmarks_to_delete:
        db.delete(bookmark)

    db.commit()


@router.get("/stats")
def get_bookmark_stats(db: SessionDep, current_user: CurrentUser):
    """Get user's bookmark statistics"""
    total = db.exec(
        select(func.count(Bookmark.id)).where(Bookmark.user_id == current_user.id)
    ).one()

    favorites = db.exec(
        select(func.count(Bookmark.id))
        .where(Bookmark.user_id == current_user.id)
        .where(Bookmark.is_favorite)
    ).one()

    # Get tag counts
    tag_counts = db.exec(
        select(Tag.name, func.count(BookmarkTag.bookmark_id))
        .join(BookmarkTag)
        .join(Bookmark)
        .where(Bookmark.user_id == current_user.id)
        .group_by(Tag.name)
        .order_by(func.count(BookmarkTag.bookmark_id).desc())
    ).all()

    return {
        "total_bookmarks": total,
        "total_favorites": favorites,
        "tags": [{"name": name, "count": count} for name, count in tag_counts],
    }


@router.get("/{bookmark_id}", response_model=BookmarkRead)
def read_bookmark(bookmark_id: int, db: SessionDep, current_user: CurrentUser):
    """Get bookmark by ID"""
    bookmark = db.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found"
        )

    # Check ownership
    if bookmark.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this bookmark",
        )

    return BookmarkRead(
        **bookmark.model_dump(), tags=[tag.name for tag in bookmark.tags]
    )


@router.patch("/{bookmark_id}", response_model=BookmarkRead)
def update_bookmark(
    bookmark_id: int,
    bookmark_in: BookmarkUpdate,
    db: SessionDep,
    current_user: CurrentUser,
):
    """Update bookmark"""
    # Get bookmark
    bookmark = db.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found"
        )

    # Check ownership
    if bookmark.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this bookmark",
        )

    # Update fields
    update_data = bookmark_in.model_dump(exclude_unset=True)

    # Handle tags separately
    if "tags" in update_data:
        new_tags = update_data.pop("tags")

        # Remove existing tags
        db.exec(select(BookmarkTag).where(BookmarkTag.bookmark_id == bookmark_id)).all()
        for bt in db.exec(
            select(BookmarkTag).where(BookmarkTag.bookmark_id == bookmark_id)
        ).all():
            db.delete(bt)

        # Add new tags
        for tag_name in new_tags:
            tag = db.exec(select(Tag).where(Tag.name == tag_name.lower())).first()
            if not tag:
                tag = Tag(name=tag_name.lower())
                db.add(tag)
                db.commit()
                db.refresh(tag)

            bookmark_tag = BookmarkTag(bookmark_id=bookmark.id, tag_id=tag.id)
            db.add(bookmark_tag)

    # Update other fields
    for field, value in update_data.items():
        setattr(bookmark, field, value)

    from datetime import datetime

    bookmark.updated_at = datetime.utcnow()

    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    return BookmarkRead(
        **bookmark.model_dump(), tags=[tag.name for tag in bookmark.tags]
    )


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(bookmark_id: int, db: SessionDep, current_user: CurrentUser):
    """Delete bookmark"""
    bookmark = db.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found"
        )

    # Check ownership
    if bookmark.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this bookmark",
        )

    db.delete(bookmark)
    db.commit()


@router.get("/export/csv", response_class=StreamingResponse)
def export_bookmarks_csv(db: SessionDep, current_user: CurrentUser):
    """Export the user's bookmarks to a CSV file."""
    # Fetch all bookmarks for the user
    bookmarks = db.exec(
        select(Bookmark).where(Bookmark.user_id == current_user.id)
    ).all()

    # Use an in-memory text buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header row
    header = ["id", "url", "title", "description", "is_favorite", "created_at", "tags"]
    writer.writerow(header)

    # Write data rows
    for bookmark in bookmarks:
        # Join tags into a single string
        tag_str = ", ".join([tag.name for tag in bookmark.tags])
        row = [
            bookmark.id,
            bookmark.url,
            bookmark.title,
            bookmark.description,
            bookmark.is_favorite,
            bookmark.created_at.isoformat(),
            tag_str,
        ]
        writer.writerow(row)

    # The browser needs these headers to trigger a download
    headers = {
        "Content-Disposition": "attachment; filename=bookmarks_export.csv",
        "Content-Type": "text/csv",
    }

    # Move the buffer's cursor to the beginning
    output.seek(0)

    return StreamingResponse(output, headers=headers)
