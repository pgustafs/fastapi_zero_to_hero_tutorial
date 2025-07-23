from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User


def test_create_user(client: TestClient):
    """Test creating a new user successfully."""
    response = client.post(
        "/api/v1/users/",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert "hashed_password" not in data


def test_read_user_me(client: TestClient, test_user: User, auth_headers: dict):
    """Test fetching the current user, which is mocked to be test_user."""
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username


def test_list_users(client: TestClient, session: Session, test_user: User):
    """Test listing users."""
    # The test_user fixture already created one user. Let's create another.
    user2 = User(username="user2", email="user2@example.com", hashed_password="hash")
    session.add(user2)
    session.commit()

    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["username"] == test_user.username
    assert data[1]["username"] == user2.username


def test_update_user(client: TestClient, test_user: User, auth_headers: dict):
    """Test updating the current user's profile."""
    new_full_name = "Updated Test User"
    response = client.patch(
        f"/api/v1/users/{test_user.id}",
        headers=auth_headers,
        json={"full_name": new_full_name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == new_full_name
    assert data["username"] == test_user.username


def test_delete_user(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test deleting the current user's profile."""
    response = client.delete(f"/api/v1/users/{test_user.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify the user is actually gone from the database
    deleted_user = session.get(User, test_user.id)
    assert deleted_user is None
