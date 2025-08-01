from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Token response model"""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token payload model"""

    sub: str
    exp: int
    iat: int
    type: str


class LoginRequest(BaseModel):
    """Login request model"""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """Registration request model"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=100)
