import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

# ✅ Import the global 'app' instance from your main application
from app.main import app
from app.core.database import get_session
from app.models import User
from app.core.security import get_password_hash


@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh, in-memory database session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Create a TestClient that uses the test_session fixture to override
    the get_session dependency in the global 'app' object.
    """

    def get_session_override():
        return session

    # Apply the override to the global app object
    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)
    yield client

    # Clean up the override after the test
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def user_fixture(session: Session) -> User:
    """Create and return a test user in the database."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user: User) -> dict:
    """
    Returns a simple, non-validated Authorization header.
    This works with the Chapter 3 placeholder dependency.
    """
    # The 'test_user' fixture is included to ensure the user exists in the DB,
    # as the placeholder dependency will try to fetch it.
    return {"Authorization": "Bearer test"}
