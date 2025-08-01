from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    PROJECT_NAME: str = "Smart Bookmarks API"
    PROJECT_DESCRIPTION: str = "A bookmark manager to organize your favorite links"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: Optional[str] = "sqlite:///./bookmarks.db"
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    LOG_ROTATION_SIZE_MB: int = 5
    LOG_ROTATION_BACKUP_COUNT: int = 3
    # Add Redis and AI Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    AI_ENABLED: bool = True
    AI_API_BASE_URL: str = "http://localhost:8080/v1"
    AI_API_KEY: Optional[str] = "secret_key"
    AI_MODEL: str = "qwen3"


settings = Settings()
