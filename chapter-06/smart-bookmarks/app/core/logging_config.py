import logging.config
import json
from datetime import datetime
from pathlib import Path
from app.core.config import settings

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format."""

    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
        }
        if hasattr(record, "extra_info"):
            log_object.update(record.extra_info)

        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_object)


# This dictionary defines the entire logging configuration.
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "app.core.logging_config.JSONFormatter",
        },
    },
    "handlers": {
        "rich_console": {
            "class": "rich.logging.RichHandler",
            "level": settings.LOG_LEVEL.upper(),
            "rich_tracebacks": True,
            "tracebacks_show_locals": True,
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/app.log",
            "maxBytes": settings.LOG_ROTATION_SIZE_MB * 1024 * 1024,
            "backupCount": settings.LOG_ROTATION_BACKUP_COUNT,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "logs/errors.log",
            "maxBytes": settings.LOG_ROTATION_SIZE_MB * 1024 * 1024,
            "backupCount": settings.LOG_ROTATION_BACKUP_COUNT,
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["rich_console"], "level": "INFO", "propagate": False},
        "sqlalchemy": {
            "handlers": ["rich_console"],
            "level": "WARNING",
            "propagate": False,
        },
        "app": {
            "handlers": ["rich_console", "app_file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["rich_console", "app_file", "error_file"],
        "level": settings.LOG_LEVEL.upper(),
    },
}
