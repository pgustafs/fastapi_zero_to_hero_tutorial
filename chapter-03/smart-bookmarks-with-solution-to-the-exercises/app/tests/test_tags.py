from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User, Bookmark, Tag


def test_read_user_tags(client: TestClient, session: Session, test_user: User):
    """Test reading tags for the current user, ensuring it's scoped correctly."""
    # Arrange: Create data for two different users
    other_user = User(username="other", email="other@example.com", hashed_password="pw")
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    # Tags for test_user
    b1 = Bookmark(url="https://s1.com", title="S1", user_id=test_user.id)
    b2 = Bookmark(url="https://s2.com", title="S2", user_id=test_user.id)
    tag_python = Tag(name="python")
    tag_fastapi = Tag(name="fastapi")
    b1.tags.extend([tag_python, tag_fastapi])
    b2.tags.append(tag_python)

    # Tag for other_user
    b3 = Bookmark(url="https://s3.com", title="S3", user_id=other_user.id)
    tag_docker = Tag(name="docker")
    b3.tags.extend([tag_python, tag_docker])

    session.add_all([b1, b2, b3])
    session.commit()

    # Act: Fetch tags for 'test_user'
    response = client.get("/api/v1/tags/", headers={"Authorization": "Bearer test"})

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Should only return tags used by test_user ('python', 'fastapi')
    # and should not include 'docker'
    assert len(data) == 2

    # The default sort is by count descending
    assert data[0]["name"] == "python"
    assert data[0]["bookmark_count"] == 2
    assert data[1]["name"] == "fastapi"
    assert data[1]["bookmark_count"] == 1


def test_read_popular_tags(client: TestClient, session: Session, test_user: User):
    """Test the public popular tags endpoint."""
    # Arrange
    # Step 1: Create the 'other' user and commit to get its ID.
    other_user = User(username="other", email="other@example.com", hashed_password="pw")
    session.add(other_user)
    session.commit()
    session.refresh(other_user)  # Load the new ID into the object

    # Step 2: Now create bookmarks for both users with valid user_ids.
    b1 = Bookmark(url="https://s1.com", title="S1", user_id=test_user.id)
    b2 = Bookmark(
        url="https://s2.com", title="S2", user_id=other_user.id
    )  # Now uses a valid ID
    tag_python = Tag(name="python")
    tag_public = Tag(name="public")

    # Add to session and commit
    session.add_all([b1, b2, tag_python, tag_public])
    session.commit()

    # Step 3: Create the relationships
    b1.tags.append(tag_python)
    b1.tags.append(tag_public)
    b2.tags.append(tag_python)  # 'python' is used again
    session.add_all([b1, b2])
    session.commit()

    # Act: Fetch popular tags (no auth needed)
    response = client.get("/api/v1/tags/popular")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Create a dictionary for easier, order-independent checking
    tag_counts = {item["name"]: item["usage_count"] for item in data}
    assert tag_counts["python"] == 2
    assert tag_counts["public"] == 1
