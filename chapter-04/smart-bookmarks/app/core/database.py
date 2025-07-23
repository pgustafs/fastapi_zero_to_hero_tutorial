from sqlmodel import create_engine, SQLModel, Session
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create engine based on database URL
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite specific settings
    engine = create_engine(
        settings.DATABASE_URL,
        echo=True,  # Log SQL queries (disable in production)
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL settings
    engine = create_engine(
        settings.DATABASE_URL,
        echo=True,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,  # Number of connections to maintain
        max_overflow=10,  # Maximum overflow connections
    )


def init_db():
    """Create all database tables"""
    logger.info("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created successfully!")


def get_session():
    """Dependency to get database session"""
    with Session(engine) as session:
        yield session
