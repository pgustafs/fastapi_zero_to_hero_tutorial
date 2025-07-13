from sqlmodel import Session
from app.models import User, Bookmark, Tag, BookmarkTag


def test_create_user(session: Session):
    """Test creating a User model and saving it to the database."""
    user = User(
        username="testuser", email="test@example.com", hashed_password="fakehash"
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    assert user.username == "testuser"
    assert user.created_at is not None


def test_create_bookmark(session: Session):
    """Test creating a Bookmark linked to a User."""
    user = User(
        username="testuser2", email="test2@example.com", hashed_password="fakehash"
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    bookmark = Bookmark(
        url="https://example.com", title="Example", user_id=user.id, owner=user
    )
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    assert bookmark.id is not None
    assert bookmark.user_id == user.id
    assert bookmark.owner.username == "testuser2"


def test_create_bookmark_with_tags(session: Session):
    """Test creating a bookmark with a many-to-many tag relationship."""
    # 1. Arrange: Create and commit the user first to get an ID
    user = User(username="taguser", email="tag@example.com", hashed_password="hash")
    session.add(user)
    session.commit()
    session.refresh(user)

    # 2. Now create the other objects using the valid user.id
    tag1 = Tag(name="python")
    tag2 = Tag(name="fastapi")
    bookmark = Bookmark(url="https://tiangolo.com", title="Typer", user_id=user.id)

    # 3. Add the new objects and commit again
    session.add(tag1)
    session.add(tag2)
    session.add(bookmark)
    session.commit()

    # Refresh to make sure all objects have IDs from the DB
    session.refresh(tag1)
    session.refresh(tag2)
    session.refresh(bookmark)

    # 4. Link them using the association table
    link1 = BookmarkTag(bookmark_id=bookmark.id, tag_id=tag1.id)
    link2 = BookmarkTag(bookmark_id=bookmark.id, tag_id=tag2.id)
    session.add(link1)
    session.add(link2)
    session.commit()

    # Refresh the bookmark to load the 'tags' relationship
    session.refresh(bookmark)

    # 5. Assert: Check if the relationships work
    assert len(bookmark.tags) == 2
    assert bookmark.tags[0].name == "python"
    assert bookmark.tags[1].name == "fastapi"
