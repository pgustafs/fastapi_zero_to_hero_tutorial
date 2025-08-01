from app.core.database import init_db, engine
from app.models import User, Bookmark, Tag, BookmarkTag
from sqlmodel import Session, select

# Initialize database
init_db()
print("✅ Database tables created!")

# Test creating data
with Session(engine) as session:
    # Create a user
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="dummy_hash",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"✅ Created user: {user.username} (ID: {user.id})")

    # Create a bookmark
    bookmark = Bookmark(
        url="https://fastapi.tiangolo.com",
        title="FastAPI Documentation",
        description="Modern web framework for building APIs",
        user_id=user.id,
    )
    session.add(bookmark)

    # Create tags
    python_tag = Tag(name="python")
    webdev_tag = Tag(name="webdev")
    session.add(python_tag)
    session.add(webdev_tag)
    session.commit()

    # Link bookmark to tags
    bookmark_tag1 = BookmarkTag(bookmark_id=bookmark.id, tag_id=python_tag.id)
    bookmark_tag2 = BookmarkTag(bookmark_id=bookmark.id, tag_id=webdev_tag.id)
    session.add(bookmark_tag1)
    session.add(bookmark_tag2)
    session.commit()

    print(f"✅ Created bookmark: {bookmark.title}")
    print(f"✅ Created tags: {python_tag.name}, {webdev_tag.name}")

    # Test querying
    statement = select(Bookmark).where(Bookmark.user_id == user.id)
    bookmarks = session.exec(statement).all()
    print(f"✅ Found {len(bookmarks)} bookmarks for user")

    # Clean up
    session.delete(bookmark)
    session.delete(python_tag)
    session.delete(webdev_tag)
    session.delete(user)
    session.commit()
    print("✅ Cleanup complete!")
