import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        # Make the request ID available to endpoints
        request.state.request_id = request_id

        # Log request details
        start_time = time.time()

        # Prepare a dictionary with extra info to pass to the logger
        log_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
        }
        logger.info("Request started", extra={"extra_info": log_extra})

        try:
            # Process the request
            response = await call_next(request)

            # Log response details
            duration_ms = (time.time() - start_time) * 1000
            log_extra["status_code"] = response.status_code
            log_extra["duration_ms"] = f"{duration_ms:.2f}"
            logger.info("Request completed", extra={"extra_info": log_extra})

            # Add request ID to response header for client-side correlation
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            # Log any unhandled exceptions
            log_extra["status_code"] = 500
            logger.exception(
                "Unhandled exception during request",
                exc_info=e,
                extra={"extra_info": log_extra},
            )
            # Re-raise the exception to be handled by FastAPI's error handling
            raise
