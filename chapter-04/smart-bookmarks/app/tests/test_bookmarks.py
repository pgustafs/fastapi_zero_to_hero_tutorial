from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User, Bookmark, Tag


def test_create_bookmark(client: TestClient, test_user: User, auth_headers: dict):
    """Test creating a bookmark with authentication."""
    response = client.post(
        "/api/v1/bookmarks/",
        headers=auth_headers,
        json={"url": "https://test.com", "title": "Test Bookmark", "tags": ["testing"]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Bookmark"
    assert data["user_id"] == test_user.id
    assert data["tags"] == ["testing"]


def test_read_bookmarks(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test reading a list of bookmarks with authentication."""
    b1 = Bookmark(url="https://site1.com", title="Site 1", user_id=test_user.id)
    b2 = Bookmark(url="https://site2.com", title="Site 2", user_id=test_user.id)
    session.add_all([b1, b2])
    session.commit()

    response = client.get("/api/v1/bookmarks/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Site 2"
    assert data[1]["title"] == "Site 1"


def test_update_bookmark(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test updating a user's own bookmark."""
    bookmark = Bookmark(
        url="https://original.com", title="Original Title", user_id=test_user.id
    )
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    response = client.patch(
        f"/api/v1/bookmarks/{bookmark.id}",
        headers=auth_headers,
        json={"title": "Updated Title", "is_favorite": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["is_favorite"] is True


def test_delete_bookmark(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test deleting a user's own bookmark."""
    bookmark = Bookmark(
        url="https://todelete.com", title="To Delete", user_id=test_user.id
    )
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    response = client.delete(f"/api/v1/bookmarks/{bookmark.id}", headers=auth_headers)
    assert response.status_code == 204

    deleted_bookmark = session.get(Bookmark, bookmark.id)
    assert deleted_bookmark is None


def test_fail_to_access_other_user_bookmark(
    client: TestClient, session: Session, auth_headers: dict
):
    """Test that a user cannot access another user's bookmark."""
    other_user = User(
        username="otheruser", email="other@example.com", hashed_password="hash"
    )
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    other_bookmark = Bookmark(
        url="https://secret.com", title="Secret", user_id=other_user.id
    )
    session.add(other_bookmark)
    session.commit()
    session.refresh(other_bookmark)

    response = client.get(
        f"/api/v1/bookmarks/{other_bookmark.id}",
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_read_bookmarks_sorting(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test sorting bookmarks by title in ascending order."""
    # Arrange: Create bookmarks in a non-alphabetical order
    b1 = Bookmark(url="https://site-b.com", title="B Bookmark", user_id=test_user.id)
    b2 = Bookmark(url="https://site-a.com", title="A Bookmark", user_id=test_user.id)
    session.add_all([b1, b2])
    session.commit()

    # Act: Request bookmarks sorted by title, ascending
    response = client.get(
        "/api/v1/bookmarks/?sort_by=title&sort_order=asc", headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "A Bookmark"
    assert data[1]["title"] == "B Bookmark"


def test_bulk_delete_bookmarks(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test bulk deleting bookmarks, ensuring ownership is respected."""
    # Arrange: Create bookmarks for the test_user and another user
    other_user = User(username="other", email="other@example.com", hashed_password="pw")
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    b1_todelete = Bookmark(url="https://s1.com", title="S1", user_id=test_user.id)
    b2_tokeep = Bookmark(url="https://s2.com", title="S2", user_id=test_user.id)
    b3_otheruser = Bookmark(url="https://s3.com", title="S3", user_id=other_user.id)
    session.add_all([b1_todelete, b2_tokeep, b3_otheruser])
    session.commit()
    session.refresh(b1_todelete)
    session.refresh(b2_tokeep)
    session.refresh(b3_otheruser)

    # Act: Request to delete one of test_user's bookmarks and the other_user's bookmark
    response = client.post(
        "/api/v1/bookmarks/bulk-delete",
        headers=auth_headers,
        json={"bookmark_ids": [b1_todelete.id, b3_otheruser.id]},
    )

    # Assert
    assert response.status_code == 204
    assert session.get(Bookmark, b1_todelete.id) is None
    assert session.get(Bookmark, b2_tokeep.id) is not None
    assert session.get(Bookmark, b3_otheruser.id) is not None


def test_export_bookmarks_csv(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test exporting bookmarks to a CSV file."""
    # Arrange
    bookmark = Bookmark(url="https://test.com", title="CSV Test", user_id=test_user.id)
    tag = Tag(name="csv")
    bookmark.tags.append(tag)
    session.add(bookmark)
    session.commit()

    # Act
    response = client.get("/api/v1/bookmarks/export/csv", headers=auth_headers)

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv"
    assert (
        "attachment; filename=bookmarks_export.csv"
        in response.headers["content-disposition"]
    )

    # Check the content of the CSV
    content = response.text
    assert "id,url,title,description,is_favorite,created_at,tags" in content
    assert "CSV Test" in content
    assert "csv" in content
