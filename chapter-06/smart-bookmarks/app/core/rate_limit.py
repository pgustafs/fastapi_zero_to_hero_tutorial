from typing import Dict
from datetime import datetime, timedelta
from fastapi import HTTPException, status


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
        self.attempts: Dict[str, list[datetime]] = {}

    def check_rate_limit(self, key: str) -> None:
        """
        Check if rate limit exceeded

        Args:
            key: Identifier (e.g., IP address or username)

        Raises:
            HTTPException: If rate limit exceeded
        """
        now = datetime.now()

        # Clean old attempts
        if key in self.attempts:
            self.attempts[key] = [
                attempt for attempt in self.attempts[key] if now - attempt < self.window
            ]

        # Check limit
        if key in self.attempts and len(self.attempts[key]) >= self.max_attempts:
            wait_time = (self.attempts[key][0] + self.window - now).seconds // 60
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {wait_time} minutes.",
            )

    def add_attempt(self, key: str) -> None:
        """Record an attempt"""
        if key not in self.attempts:
            self.attempts[key] = []
        self.attempts[key].append(datetime.now())


# Global rate limiter instance
login_limiter = RateLimiter(max_attempts=5, window_minutes=15)
