from celery import Celery
from celery.signals import setup_logging
from logging.config import dictConfig
from app.core.logging_config import LOGGING_CONFIG
from app.core.config import settings


# This function will be called when the Celery worker starts
@setup_logging.connect
def configure_logging(**kwargs):
    """
    Apply the application's logging configuration to the Celery worker.
    """
    dictConfig(LOGGING_CONFIG)


celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.ai_tasks"],
)
