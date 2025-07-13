import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool


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
