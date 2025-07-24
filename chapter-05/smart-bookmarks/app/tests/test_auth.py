from fastapi.testclient import TestClient
from app.models import User
from app.core.security import get_password_hash
from sqlmodel import Session


def test_register_user(client: TestClient):
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data


def test_register_duplicate_username(client: TestClient, session: Session):
    """Test registration with duplicate username"""
    # Create existing user
    user = User(
        username="existing",
        email="existing@example.com",
        hashed_password=get_password_hash("password"),
    )
    session.add(user)
    session.commit()

    # Try to register with same username
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "existing",
            "email": "new@example.com",
            "password": "newpass123",
        },
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client: TestClient, session: Session):
    """Test successful login"""
    # Create user
    user = User(
        username="logintest",
        email="login@example.com",
        hashed_password=get_password_hash("correctpass"),
    )
    session.add(user)
    session.commit()

    # Login
    response = client.post(
        "/api/v1/auth/login", json={"username": "logintest", "password": "correctpass"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_with_email(client: TestClient, session: Session):
    """Test login with email instead of username"""
    # Create user
    user = User(
        username="emailtest",
        email="email@example.com",
        hashed_password=get_password_hash("testpass"),
    )
    session.add(user)
    session.commit()

    # Login with email
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "email@example.com",  # Using email
            "password": "testpass",
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client: TestClient, session: Session):
    """Test login with wrong password"""
    # Create user
    user = User(
        username="wrongpass",
        email="wrong@example.com",
        hashed_password=get_password_hash("correctpass"),
    )
    session.add(user)
    session.commit()

    # Login with wrong password
    response = client.post(
        "/api/v1/auth/login", json={"username": "wrongpass", "password": "wrongpass"}
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_access_protected_endpoint(client: TestClient, session: Session):
    """Test accessing protected endpoint with token"""
    # Create user and login
    user = User(
        username="authtest",
        email="auth@example.com",
        hashed_password=get_password_hash("authpass"),
    )
    session.add(user)
    session.commit()

    # Login to get token
    login_response = client.post(
        "/api/v1/auth/login", json={"username": "authtest", "password": "authpass"}
    )
    token = login_response.json()["access_token"]

    # Access protected endpoint
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "authtest"


def test_access_without_token(client: TestClient):
    """Test accessing protected endpoint without token"""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 403  # Forbidden (no credentials)


def test_access_with_invalid_token(client: TestClient):
    """Test accessing protected endpoint with invalid token"""
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401
