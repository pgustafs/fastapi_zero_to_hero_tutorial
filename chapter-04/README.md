# Chapter 4: JWT Authentication with PyJWT

## What is JWT Authentication?

JWT (JSON Web Token) is a secure way to transmit information between parties as a JSON object. In our API:

1.  User logs in with credentials.
2.  Server creates and signs a JWT token.
3.  Client includes the token in subsequent requests.
4.  Server verifies the token and identifies the user.

## Why JWT Matters

1.  **Stateless**: No need to store sessions on the server.
2.  **Scalable**: Works across multiple servers.
3.  **Secure**: Cryptographically signed.
4.  **Self-contained**: Contains user information.
5.  **Standard**: Works with any client.

## How JWT Works

A JWT has three parts separated by dots:

  - **Header**: Token type and algorithm.
  - **Payload**: User data and claims.
  - **Signature**: Ensures the token hasn't been tampered with.

Example: `xxxxx.yyyyy.zzzzz`

## Let's Build: Implementing Authentication

### Step 1: Update Security Configuration

We'll expand our security utilities to include functions for creating and decoding JWTs.

Update `app/core/security.py`:

```python
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        subject: Usually the user ID or username
        expires_delta: Token expiration time
    
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Create JWT payload
    to_encode = {
        "sub": subject,  # Subject (user identifier)
        "exp": expire,   # Expiration time
        "iat": datetime.now(timezone.utc),  # Issued at
        "type": "access"
    }
    
    # Encode token
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token to decode
        
    Returns:
        Token payload
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")
```

#### Dissecting the Security Utilities 🧐

We've added two core functions for handling JWTs:

  - **`create_access_token`**: This function generates a new JWT. It creates a **payload** (a dictionary) with standard claims: `sub` (the subject, our user's identifier), `exp` (an expiration timestamp to make the token temporary), and `iat` (the time the token was issued). It then uses `jwt.encode()` to sign this payload with our `SECRET_KEY` from the settings, ensuring its integrity.
  - **`decode_access_token`**: This is the counterpart function. It takes a token string and uses `jwt.decode()` to verify its signature and check if it has expired. If the token is valid, it returns the payload. If not, `PyJWT` raises an error, which we catch and re-raise with a user-friendly message.


### Step 2: Create Authentication Schemas

We need Pydantic models to define the data structures for login, registration, and tokens. It's good practice to place these in a separate `schemas` directory, as they are not database models.

First, create `app/schemas/__init__.py` to make it a package. Then, create `app/schemas/auth.py`:

```python
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
```

#### Dissecting the Authentication Schemas 🧐

These Pydantic models define the "shape" of our authentication-related data for validation and serialization.

  - **`Token`**: Defines the structure of the response we send back after a successful login.
  - **`TokenPayload`**: Provides type safety for the data we get *after* decoding a token.
  - **`LoginRequest` & `RegisterRequest`**: Define the expected request bodies for their respective endpoints. FastAPI will use these to automatically validate incoming JSON, ensuring, for example, that a password meets the minimum length or that an email is in a valid format thanks to `EmailStr`.


### Step 3: Update Dependencies

Now we'll replace our placeholder `get_current_user` dependency with the real implementation that validates the JWT.

Update `app/api/deps.py`:

```python
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import decode_access_token
from app.models import User

# JWT bearer in “Authorization: Bearer <token>”
security = HTTPBearer(
    scheme_name="JWT",
    description="Enter: **Bearer <JWT>**",
    auto_error=False,
)

# Alias for DB session dependency
SessionDep = Annotated[Session, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: SessionDep,
) -> User:
    """
    Validate JWT and return the active User.

    Raises 403 if token is missing, 401 if invalid, 400 if inactive.
    """
    # No credentials → forbidden
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if not username:
            raise ValueError("Missing subject")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: SessionDep = Depends(get_session),
) -> Optional[User]:
    """
    Return User if a valid token is provided, else None.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# Annotated shortcuts for your routes
CurrentUser     = Annotated[User, Depends(get_current_user)]
OptionalUser    = Annotated[Optional[User], Depends(get_current_user_optional)]
```

#### Dissecting the Authentication Dependencies 🧐

This step replaces our temporary placeholder with real authentication logic.

  - **`get_current_user`**: This is now the real deal. It extracts the token string from the `Authorization: Bearer <token>` header, uses our `decode_access_token` utility to validate it, and then fetches the corresponding user from the database. It includes crucial checks to ensure the user exists and is active.
  - **Error Handling**: The `try...except` block is vital. It catches any `InvalidTokenError` from our security utility and converts it into a clean `HTTPException` with a `401 UNAUTHORIZED` status code, which is the correct response for invalid credentials.
  - **`get_current_user_optional`**: This is a new, useful dependency. It's for public endpoints that might change their behavior if a user is logged in (e.g., showing a "like" button). It attempts to get the current user, but if authentication fails for any reason (no token, invalid token), it simply returns `None` instead of raising an error.


### Step 4: Create Authentication Endpoints

These are the public endpoints that users will interact with to register, log in, and refresh their tokens.

Create `app/api/routes/auth.py`:

```python
from datetime import timedelta

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
    Depends,
)
from sqlmodel import Session, select, or_

from app.core.config import settings
from app.core.database import get_session
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
)
from app.api.deps import SessionDep, CurrentUser
from app.models import User, UserRead
from app.schemas.auth import Token, LoginRequest, RegisterRequest

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: RegisterRequest,
    db: SessionDep,
):
    """
    Register a new user

    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: At least 8 characters
    - **full_name**: Optional full name
    """
    # Check if user exists
    existing = db.exec(
        select(User).where(
            or_(
                User.username == user_in.username,
                User.email == user_in.email,
            )
        )
    ).first()
    if existing:
        detail = (
            "Username already registered"
            if existing.username == user_in.username
            else "Email already registered"
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=detail)

    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: LoginRequest,
    request: Request,
    db: SessionDep,
):
    """
    Login to get access token

    - **username**: Username or email
    - **password**: User password

    Returns JWT access token
    """

    user = db.exec(
        select(User).where(
            or_(
                User.username == form_data.username,
                User.email == form_data.username,
            )
        )
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = create_access_token(
        subject=user.username,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/refresh", response_model=Token)
def refresh_token(
    current_user: CurrentUser,
):
    """
    Refresh access token — requires a valid current token
    """
    access_token = create_access_token(
        subject=current_user.username,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
def read_users_me(
    current_user: CurrentUser,
):
    """
    Get the current authenticated user — 403 if no token, 401 if invalid
    """
    return current_user
```

#### Dissecting the Authentication Endpoints 🧐

This file creates the public-facing API for user authentication.

  - **`/register`**: Uses the `RegisterRequest` schema to validate new user data, checks for duplicate usernames or emails, and uses our `get_password_hash` utility before saving the new user.
  - **`/login`**: This is the core authentication endpoint. It finds the user by username or email, uses `verify_password` to check credentials, and if everything is correct, calls `create_access_token` to generate the JWT that the client will use for all future requests.
  - **`/refresh`**: This is a convenience endpoint. It requires a valid, existing token (via the `CurrentUser` dependency) and simply issues a *new* token with a new expiration time. This allows a client to extend a session without forcing the user to log in again.
  - **`/me`**: A simple protected endpoint that uses the `CurrentUser` dependency to identify the user from their token and return their profile information. It's a great way to test that a token is working.

-----

### Step 5: Update Main App

We need to wire up our new authentication router in the main API router.

Update `app/api/routes/__init__.py`:

```python
from fastapi import APIRouter
from app.api.routes import users, bookmarks, tags, auth # Add auth

api_router = APIRouter()

# Add auth route modules
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# ...
```

#### Dissecting the Router Update 🧐

This is a simple but important step. We import our new `auth` router and use `api_router.include_router()` to add it to our application's API. We give it a `/auth` prefix, so all endpoints inside it (like `/login`) will be accessible at `/api/v1/auth/login`. We also tag it as `"authentication"` to keep our auto-generated docs organized.

-----

### Step 6: Add Login Rate Limiting

To prevent brute-force attacks, we'll add a simple in-memory rate limiter to our login endpoint.

Create `app/core/rate_limit.py`:

```python
from typing import Dict, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request


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
                attempt for attempt in self.attempts[key]
                if now - attempt < self.window
            ]
        
        # Check limit
        if key in self.attempts and len(self.attempts[key]) >= self.max_attempts:
            wait_time = (self.attempts[key][0] + self.window - now).seconds // 60
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {wait_time} minutes."
            )
    
    def add_attempt(self, key: str) -> None:
        """Record an attempt"""
        if key not in self.attempts:
            self.attempts[key] = []
        self.attempts[key].append(datetime.now())


# Global rate limiter instance
login_limiter = RateLimiter(max_attempts=5, window_minutes=15)
```

Update the login endpoint in `app/api/routes/auth.py` to use the limiter:

```python
# ....
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
)
from app.core.rate_limit import login_limiter  # New Line
from app.api.deps import SessionDep, CurrentUser

# ...

@router.post("/login", response_model=Token)
def login(
    form_data: LoginRequest,
    request: Request,
    db: SessionDep,
):
    """
    Login to get access token

    - **username**: Username or email
    - **password**: User password

    Returns JWT access token
    """
    client_ip = request.client.host # New Line
    login_limiter.check_rate_limit(client_ip) # New Line

    user = db.exec(
        select(User).where(
            or_(
                User.username == form_data.username,
                User.email == form_data.username,
            )
        )
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        login_limiter.add_attempt(client_ip) # New Line
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = create_access_token(
        subject=user.username,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")
```

#### Dissecting the Rate Limiter 🧐

  - **Purpose**: Rate limiting is a crucial security feature that prevents attackers from making thousands of login attempts to guess a user's password (a "brute-force" attack).
  - **In-Memory Implementation**: This `RateLimiter` class is a simple example that stores login attempts in a Python dictionary in memory. It tracks attempts by a key (we use the client's IP address). **Note**: For a real production application with multiple servers, you would use a shared store like Redis instead of an in-memory dictionary.
  - **Logic**: Before trying to log a user in, `check_rate_limit` is called. If too many recent attempts have been made from that IP, it raises a `429 TOO_MANY_REQUESTS` error. If the login credentials are *incorrect*, `add_attempt` is called to record the failure.

### Step 7: Create Authentication Tests

Testing our authentication flow is critical to ensure it's secure and works as expected.

Edit `app/tests/conftest.py` and update the `auth_headers` fixture to perform a real login and return a real token:

```python

# ...

@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, test_user: User) -> dict:
    """
    Perform a real login to get a valid JWT token.
    """
    login_data = {"username": "testuser", "password": "testpass123"}
    response = client.post("/api/v1/auth/login", json=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

Create `app/tests/test_auth.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_session
from app.models import User
from app.core.security import get_password_hash
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

def test_register_user(client: TestClient):
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User"
        }
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
        hashed_password=get_password_hash("password")
    )
    session.add(user)
    session.commit()
    
    # Try to register with same username
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "existing",
            "email": "new@example.com",
            "password": "newpass123"
        }
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client: TestClient, session: Session):
    """Test successful login"""
    # Create user
    user = User(
        username="logintest",
        email="login@example.com",
        hashed_password=get_password_hash("correctpass")
    )
    session.add(user)
    session.commit()
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "logintest",
            "password": "correctpass"
        }
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
        hashed_password=get_password_hash("testpass")
    )
    session.add(user)
    session.commit()
    
    # Login with email
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "email@example.com",  # Using email
            "password": "testpass"
        }
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client: TestClient, session: Session):
    """Test login with wrong password"""
    # Create user
    user = User(
        username="wrongpass",
        email="wrong@example.com",
        hashed_password=get_password_hash("correctpass")
    )
    session.add(user)
    session.commit()
    
    # Login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "wrongpass",
            "password": "wrongpass"
        }
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_access_protected_endpoint(client: TestClient, session: Session):
    """Test accessing protected endpoint with token"""
    # Create user and login
    user = User(
        username="authtest",
        email="auth@example.com",
        hashed_password=get_password_hash("authpass")
    )
    session.add(user)
    session.commit()
    
    # Login to get token
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "authtest",
            "password": "authpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # Access protected endpoint
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
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
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401
```

Run tests:

```bash
pytest app/tests/test_auth.py -v
```

#### Dissecting the Authentication Tests 🧐

  - **Test Database**: The `session_fixture` creates a completely separate, clean, in-memory SQLite database for each test run. This is a critical testing pattern that ensures tests are isolated and don't interfere with each other or your real development database.
  - **Dependency Overrides**: The `client_fixture` uses `app.dependency_overrides`. This powerful FastAPI feature lets us replace a production dependency (like `get_db` which connects to our real DB) with a test-specific one (our `session_fixture`'s in-memory DB) for the duration of a test.
  - **Testing Scenarios**: We test both the "happy path" (successful registration and login) and failure cases (duplicate username, wrong password, invalid token). This ensures our error handling and security logic work as expected.
  - **End-to-End Test**: `test_access_protected_endpoint` is a full end-to-end test. It creates a user, logs them in through the API to get a real token, and then uses that token to access a protected endpoint, verifying the entire authentication flow.

### Step 8: Update Bookmarks Tests

Update our Bookmarks Test with authentication and works as expected.

Update `app/tests/test_bookmarks.py`:

```python
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User, Bookmark, Tag


def test_create_bookmark(client: TestClient, test_user: User, auth_headers: dict):
    """Test creating a bookmark with authentication."""
    response = client.post(
        "/api/v1/bookmarks/",
        headers=auth_headers,
        json={"url": "https://test.com", "title": "Test Bookmark", "tags": ["testing"]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Bookmark"
    assert data["user_id"] == test_user.id
    assert data["tags"] == ["testing"]


def test_read_bookmarks(client: TestClient, session: Session, test_user: User, auth_headers: dict):
    """Test reading a list of bookmarks with authentication."""
    b1 = Bookmark(url="https://site1.com", title="Site 1", user_id=test_user.id)
    b2 = Bookmark(url="https://site2.com", title="Site 2", user_id=test_user.id)
    session.add_all([b1, b2])
    session.commit()

    response = client.get("/api/v1/bookmarks/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Site 2"
    assert data[1]["title"] == "Site 1"


def test_update_bookmark(client: TestClient, session: Session, test_user: User, auth_headers: dict):
    """Test updating a user's own bookmark."""
    bookmark = Bookmark(url="https://original.com", title="Original Title", user_id=test_user.id)
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    response = client.patch(
        f"/api/v1/bookmarks/{bookmark.id}",
        headers=auth_headers,
        json={"title": "Updated Title", "is_favorite": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["is_favorite"] is True


def test_delete_bookmark(client: TestClient, session: Session, test_user: User, auth_headers: dict):
    """Test deleting a user's own bookmark."""
    bookmark = Bookmark(url="https://todelete.com", title="To Delete", user_id=test_user.id)
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    response = client.delete(f"/api/v1/bookmarks/{bookmark.id}", headers=auth_headers)
    assert response.status_code == 204

    deleted_bookmark = session.get(Bookmark, bookmark.id)
    assert deleted_bookmark is None


def test_fail_to_access_other_user_bookmark(client: TestClient, session: Session, auth_headers: dict):
    """Test that a user cannot access another user's bookmark."""
    other_user = User(username="otheruser", email="other@example.com", hashed_password="hash")
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    other_bookmark = Bookmark(url="https://secret.com", title="Secret", user_id=other_user.id)
    session.add(other_bookmark)
    session.commit()
    session.refresh(other_bookmark)

    response = client.get(
        f"/api/v1/bookmarks/{other_bookmark.id}",
        headers=auth_headers,
    )
    assert response.status_code == 403

def test_read_bookmarks_sorting(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test sorting bookmarks by title in ascending order."""
    # Arrange: Create bookmarks in a non-alphabetical order
    b1 = Bookmark(url="https://site-b.com", title="B Bookmark", user_id=test_user.id)
    b2 = Bookmark(url="https://site-a.com", title="A Bookmark", user_id=test_user.id)
    session.add_all([b1, b2])
    session.commit()

    # Act: Request bookmarks sorted by title, ascending
    response = client.get(
        "/api/v1/bookmarks/?sort_by=title&sort_order=asc", headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "A Bookmark"
    assert data[1]["title"] == "B Bookmark"


def test_bulk_delete_bookmarks(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test bulk deleting bookmarks, ensuring ownership is respected."""
    # Arrange: Create bookmarks for the test_user and another user
    other_user = User(username="other", email="other@example.com", hashed_password="pw")
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    b1_todelete = Bookmark(url="https://s1.com", title="S1", user_id=test_user.id)
    b2_tokeep = Bookmark(url="https://s2.com", title="S2", user_id=test_user.id)
    b3_otheruser = Bookmark(url="https://s3.com", title="S3", user_id=other_user.id)
    session.add_all([b1_todelete, b2_tokeep, b3_otheruser])
    session.commit()
    session.refresh(b1_todelete)
    session.refresh(b2_tokeep)
    session.refresh(b3_otheruser)

    # Act: Request to delete one of test_user's bookmarks and the other_user's bookmark
    response = client.post(
        "/api/v1/bookmarks/bulk-delete",
        headers=auth_headers,
        json={"bookmark_ids": [b1_todelete.id, b3_otheruser.id]},
    )

    # Assert
    assert response.status_code == 204
    assert session.get(Bookmark, b1_todelete.id) is None
    assert session.get(Bookmark, b2_tokeep.id) is not None
    assert session.get(Bookmark, b3_otheruser.id) is not None


def test_export_bookmarks_csv(
    client: TestClient, session: Session, test_user: User, auth_headers: dict
):
    """Test exporting bookmarks to a CSV file."""
    # Arrange
    bookmark = Bookmark(url="https://test.com", title="CSV Test", user_id=test_user.id)
    tag = Tag(name="csv")
    bookmark.tags.append(tag)
    session.add(bookmark)
    session.commit()

    # Act
    response = client.get("/api/v1/bookmarks/export/csv", headers=auth_headers)

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv"
    assert (
        "attachment; filename=bookmarks_export.csv"
        in response.headers["content-disposition"]
    )

    # Check the content of the CSV
    content = response.text
    assert "id,url,title,description,is_favorite,created_at,tags" in content
    assert "CSV Test" in content
    assert "csv" in content
```

#### Dissecting the Update 🧐

  - **Consistent Authentication**: Every test function that accesses a protected bookmark endpoint now includes the `auth_headers` fixture in its signature.
  - **Real-World Simulation**: We've replaced `headers={"Authorization": "Bearer test"}` with `headers=auth_headers`. This means that before each test runs, your `auth_headers` fixture performs a real login for the `test_user` and injects a valid JWT into the request.
  - **Increased Confidence**: Your tests are now more valuable because they don't just check the bookmark logic; they verify that the bookmark logic works correctly *behind your real authentication system*.

Run tests:

```bash
pytest app/tests/test_bookmarks.py -v
```

Excellent. Now that you have a working `auth_headers` fixture that provides a real JWT, the final step is to update your remaining tests to use it. This will complete the transition from placeholder authentication to a fully tested, secure system.


### Step 9: Update Remaining Tests to Use Real Authentication

Our `test_users.py` and `test_tags.py` files are still using the old placeholder header (`"Authorization": "Bearer test"`). We need to update them to use our new `auth_headers` fixture, ensuring they test the real authentication flow.

#### 1\. Update the User Tests

In `app/tests/test_users.py`, we need to update all tests for protected endpoints (`/me`, `update`, and `delete`).

**In `app/tests/test_users.py`:**

  - For the functions `test_read_user_me`, `test_update_user`, and `test_delete_user`, add `auth_headers: dict` to the function signature.
  - In each of those functions, replace `headers={"Authorization": "Bearer test"}` with `headers=auth_headers`.

**Example for `test_read_user_me`:**

```python
# Before
def test_read_user_me(client: TestClient, test_user: User):
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer test"})
    # ...

# After
def test_read_user_me(client: TestClient, test_user: User, auth_headers: dict):
    response = client.get("/api/v1/users/me", headers=auth_headers)
    # ...
```

#### 2\. Update the Tag Tests

Next, update the user-specific tag test in `app/tests/test_tags.py`.

**In `app/tests/test_tags.py`:**

  - For the function `test_read_user_tags`, add `auth_headers: dict` to the function signature.
  - Replace `headers={"Authorization": "Bearer test"}` with `headers=auth_headers`.

**Example:**

```python
# Before
def test_read_user_tags(client: TestClient, session: Session, test_user: User):
    # ...
    response = client.get("/api/v1/tags/", headers={"Authorization": "Bearer test"})
    # ...

# After
def test_read_user_tags(client: TestClient, session: Session, test_user: User, auth_headers: dict):
    # ...
    response = client.get("/api/v1/tags/", headers=auth_headers)
    # ...
```

After making these changes, your entire test suite now uses the real authentication system, providing much higher confidence that your API is both functional and secure.

#### 3\. Run all tests

```bash
pytest app/tests
```

### 🧪 Interactive Testing

1.  **Start your server**:

```bash
fastapi dev app/main.py
```

2.  **Register a new user**:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepass123",
    "full_name": "John Doe"
  }'
```

3.  **Login to get token**:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "securepass123"
  }'

# Save the access_token from the response!
```

4.  **Use the token to access protected endpoints**:

```bash
# Replace YOUR_TOKEN with the actual token
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create a bookmark
curl -X POST "http://localhost:8000/api/v1/bookmarks/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "title": "Example Site",
    "description": "My first authenticated bookmark!",
    "tags": ["test", "example"]
  }'
```

5.  **Test in the docs**: http://localhost:8000/docs
      - Click the "Authorize" button at the top right.
      - In the popup, paste your full token (including the word "Bearer") like this: `Bearer YOUR_TOKEN`
      - Now you can use the "Try it out" feature on all the protected endpoints\!


### Step 9: Commit Your Work

You have successfully implemented and tested a robust JWT authentication system. This is a major milestone and a great place to save your progress.

**1. Add Your Changes**
Stage all the new and modified files for the commit.

```bash
git add .
```

**2. Commit with a Descriptive Message**
Use a conventional commit message that clearly summarizes the new feature.

```bash
git commit -m "feat(auth): Implement JWT authentication and rate limiting"
```

**3. Push to GitHub**
Push your new feature to the remote repository. This will also trigger your CI pipeline to run all the tests.

```bash
git push origin main
```

#### Dissecting the Commit Message 🧐

A good commit message tells a story. The format `feat(auth): Implement JWT authentication and rate limiting` is a great example:

  - **`feat`**: The "type" of the commit, indicating a new feature.
  - **`(auth)`**: The "scope," specifying which part of the application was affected.
  - **The message**: A concise, imperative summary of what was accomplished.

This structured approach makes your Git history clean, professional, and easy for others (and your future self) to understand.

### Understanding JWT Security

**Best Practices Implemented:**

1.  **Secure Secret Key**: Using a strong, random secret from our settings.
2.  **Token Expiration**: Tokens are temporary and expire after 30 minutes.
3.  **Password Hashing**: Using Bcrypt with a salt to protect stored passwords.
4.  **Rate Limiting**: Preventing brute-force attacks on the login endpoint.
5.  **HTTPS Only**: In a production environment, you should always serve your API over HTTPS to prevent tokens from being intercepted.

**Security Considerations:**

1.  **Store tokens securely**: On the client-side, tokens should be stored securely (e.g., in httpOnly cookies for web clients or in a secure keychain for mobile apps).
2.  **Token refresh strategy**: For better user experience, apps often use short-lived access tokens and longer-lived "refresh tokens" to get new access tokens without forcing the user to log in again.
3.  **Logout implementation**: The simplest logout is for the client to just delete the token. For higher security, a server-side token blacklist (e.g., using Redis) can be implemented to immediately invalidate a token.

### A Deeper Look at the `SECRET_KEY`

The **`SECRET_KEY`** is arguably the most important piece of your authentication setup. Let's break down what it is, how to manage it, and why it's so critical.

#### What is the `SECRET_KEY`?

The `SECRET_KEY` is a long, random string of characters that only your server knows. It's not a password; it's a **signing key**. When your API creates a JWT, it uses this key to generate the token's unique cryptographic **signature**.

When a token comes back in a future request, the server uses the same `SECRET_KEY` to verify that the signature is valid. If the signature doesn't match—or if the token was altered in any way—the verification fails. This is how you can be sure that the token is authentic and hasn't been tampered with.

#### How to Generate a Secure Key

A simple, guessable key like `"your-secret-key-here"` is fine for a tutorial but **dangerously insecure** for a real application. A strong secret key should be long and completely random.

An easy way to generate a strong, cryptographically secure key is to use `openssl`, which is available on most operating systems (macOS, Linux, and Windows with Git Bash).

Run this command in your terminal:

```bash
openssl rand -hex 32
```

This will generate a 64-character random hexadecimal string, which is an excellent format for a secret key.

**Example Output:**

```
c1a7c3a0b6d2e8f1a9b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5
```

#### Where to Set and How to Change the Key

The `SECRET_KEY` should **always** be managed as an **environment variable** and never be hardcoded into your application or committed to version control.

As we set up in Chapter 1, you should:

1.  Generate a new secure key using the `openssl` command above.
2.  Open your `.env` file (which is safely ignored by Git).
3.  Set the `SECRET_KEY` value to your newly generated key.

**Your `.env` file should look like this:**

```env
# ... other variables
SECRET_KEY="c1a7c3a0b6d2e8f1a9b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5"
```

4.  Restart your FastAPI server. The application will automatically pick up the new key from the `.env` file.

Changing the key is as simple as generating a new one and replacing the old value in your `.env` file. Be aware that changing the key will immediately invalidate all existing JWTs that were signed with the old key, forcing all users to log in again.

### Pro Tips

1.  **Never log tokens**: They are secrets and should not appear in your server logs.
2.  **Use environment variables**: Your `SECRET_KEY` should always come from environment variables in production.
3.  **Monitor failed logins**: This can help you detect potential brute-force attacks.

### What's Next?

In Chapter 5, we'll add logging and monitoring to track what's happening in our API\!

### Exercises

1.  **Add password reset**: Implement a "forgot password" flow.
2.  **Add email verification**: Require users to confirm their email address after registering.
3.  **Add OAuth**: Support logging in with third-party providers like Google or GitHub.
4.  **Add 2FA**: Implement two-factor authentication for enhanced security.