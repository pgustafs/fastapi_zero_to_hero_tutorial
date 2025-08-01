# Chapter 3: Building CRUD Operations

## What are CRUD Operations?

CRUD stands for Create, Read, Update, Delete—the four basic operations for managing data. In REST APIs, these map to HTTP methods:

  - **POST**: Create new resources
  - **GET**: Read/retrieve resources
  - **PUT/PATCH**: Update resources
  - **DELETE**: Remove resources

## Why CRUD Matters

1.  **Foundation of APIs**: Almost every API needs these operations.
2.  **RESTful design**: Following standards makes APIs predictable.
3.  **Separation of concerns**: Clean organization of functionality.
4.  **Reusable patterns**: Similar structure across different resources.

## How FastAPI Handles CRUD

FastAPI uses:

  - **Path operations**: Decorators like `@app.get()` define endpoints.
  - **Dependency injection**: Reusable components like database sessions.
  - **Type validation**: Automatic request/response validation.
  - **Status codes**: Proper HTTP status codes for each operation.

## Let's Build: Creating Our API Endpoints

### Step 1: Set Up API Dependencies

We'll start by creating a file for shared, reusable components—or "dependencies"—that our endpoints will need, like getting a database session or the current user.

Create `app/api/deps.py`:

```python
from typing import Annotated, Generator
from fastapi import Depends, HTTPException, status
from sqlmodel import Session
from app.core.database import get_session
from app.models import User

# Type alias for database session dependency
SessionDep = Annotated[Session, Depends(get_session)]


async def get_current_user(db: SessionDep) -> User:
    """
    A placeholder dependency to get a 'current user' without any authentication.
    It simply fetches the 'testuser' we'll create with a seeding script.
    """
    user = db.exec(select(User).where(User.username == "testuser")).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Test user not found. Please run the data seeding script."
        )
    return user


# Type alias for current user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]
```

#### Dissecting the Dependencies 🧐
This file is the heart of FastAPI's **Dependency Injection** system. We create small, reusable functions that FastAPI will automatically run for our endpoints, keeping our code clean and DRY (Don't Repeat Yourself).

-   **`SessionDep`**: This is a clean type alias for our database session dependency. We use `typing.Annotated` to tell FastAPI that whenever it sees a parameter with the type `SessionDep` (like `db: SessionDep`), it must execute the `get_session` function and inject the database `Session` that it yields. Crucially, we import `get_session` from our central `app.core.database` file, ensuring we have a single source of truth for database connections.

-   **`get_current_user`**: This function is a **placeholder** for our authentication logic. It demonstrates how one dependency can rely on another (`db: SessionDep`). For now, it simply fetches your "testuser" from the database, allowing you to test protected endpoints in this chapter without needing a real authentication system yet.

-   **`CurrentUser`**: Similar to `SessionDep`, this is a clean alias for the current user dependency. It makes our endpoint signatures more readable, allowing us to simply type `current_user: CurrentUser`.

### Step 2: Setting Up the Test Environment (`conftest.py`)

**First** Replace the entire content of `app/tests/conftest.py` with this updated version, which includes all the fixtures that will be shared across your different test files.

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

# Import the global 'app' instance from your main application
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
        hashed_password=get_password_hash("testpass123")
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
```


### Step 3: Create Security Utilities

Before creating endpoints that handle user passwords, we need functions to securely hash and verify them.

Create `app/core/security.py`:

```python
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)
```

#### Dissecting the Security Utilities 🧐

This file isolates all our password-related logic.

  - **`passlib`**: We use this industry-standard library for handling password hashing. It's important to never store passwords as plain text.
  - **`CryptContext`**: This is a configurable object from `passlib`. We've told it to use `"bcrypt"`, a strong, widely trusted hashing algorithm.
  - **`get_password_hash()`**: This function takes a plain text password and returns a secure hash. We'll use this when a user signs up.
  - **`verify_password()`**: This function compares a plaintext password attempt against a stored hash to see if they match. We'll use this for user login.

#### Testing the Security Utilities

Whenever you add new features or change existing ones, you should add or update your automated tests. This verifies your new code works and prevents future changes from accidentally breaking it.

Edit, `app/tests/test_security_utilities.py`:

```python
import re
import pytest

from app.core.security import verify_password, get_password_hash

PASSWORD = "SuperSecret123!"
OTHER     = "NotTheRightOne"


def test_get_password_hash_returns_string_and_is_not_plaintext():
    hashed = get_password_hash(PASSWORD)
    # It should be a string, and must not equal the raw password
    assert isinstance(hashed, str)
    assert hashed != PASSWORD


def test_verify_password_with_correct_and_wrong():
    hashed = get_password_hash(PASSWORD)
    # Correct password should verify
    assert verify_password(PASSWORD, hashed) is True
    # Wrong password should not
    assert verify_password(OTHER, hashed) is False


def test_hash_is_random_per_call_but_both_verify():
    # Each call salts freshly, so hashes differ
    h1 = get_password_hash(PASSWORD)
    h2 = get_password_hash(PASSWORD)
    assert h1 != h2

    # But both still verify correctly
    assert verify_password(PASSWORD, h1)
    assert verify_password(PASSWORD, h2)


@pytest.mark.parametrize("scheme", ["bcrypt"])
def test_hash_scheme_prefix(scheme):
    # Ensure that bcrypt hashes actually use the bcrypt prefix
    # passlib may produce "$2b$" or "$2a$" etc, so we allow either
    hashed = get_password_hash(PASSWORD)
    assert re.match(r"^\$2[abxy]\$\d{2}\$", hashed), "Expected bcrypt‐style prefix"
```

#### Run Your New Tests

From your project's root directory, run `pytest`:

```bash
pytest app/tests/test_security_utilities.py -v
```

### Step 4: Initial API Routing

Let's wire up the simple `health` and `status` endpoints from Chapter 1 to establish our master routing pattern.

Edit `app/api/routes/__init__.py`:

```python
from fastapi import APIRouter
from . import health, status

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(status.router, prefix="/status", tags=["status"])
```

Update `app/main.py` to use the main `api_router` and a `lifespan` event handler to create the database tables on startup.

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import init_db, get_session
from app.api.routes import api_router # Import the master router

# Add lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App startup...")
    if get_session not in app.dependency_overrides:
        init_db()
    yield
    print("App shutdown...")

app = FastAPI(
    title=settings.PROJECT_NAME,  # Change
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan, # Add this line
)

# ... CORS middleware ...

# Include the master API router with the global prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

# ... Root endpoint ...
```

#### Dissecting the Master Router Setup 🧐
This step establishes a clean and scalable routing system for your entire API.

-   **The Master Router (`api_router`)**: The `app/api/routes/__init__.py` file acts as a central hub. It creates a main `APIRouter` and uses `include_router` to gather all the individual endpoint files (like `health.py` and `status.py`) into a single, manageable unit. This keeps your main application file (`main.py`) simple, as it only needs to know about this one master router.

-   **Prefixes for Organization**: When including a router, the `prefix` argument adds a URL segment to all of its endpoints. For example, `prefix="/health"` means the `/` route inside `health.py` becomes `/health`. This is how you group related endpoints together (e.g., all user-related endpoints under `/users`).

-   **Tags for Documentation**: The `tags` argument groups the endpoints under a specific heading in the interactive API documentation (`/docs`), making it much more organized and easier to navigate.

-   **Global Version Prefix**: In `main.py`, we include this single `api_router` and apply a global prefix to it from our settings: `prefix=settings.API_V1_STR`. This is how all your API endpoints get the `/api/v1/` prefix, making it easy to version your API in the future.

#### Dissecting the lifespan Setup 🧐

The `lifespan` function is FastAPI's modern way to run code during your application's startup and shutdown events.

Think of it as the "setup" and "teardown" for your entire application.

* **On Startup (Code before `yield`):** This code runs once, right when you start the server with `fastapi dev`. It's the perfect place for tasks that need to happen before the API starts receiving requests, such as initializing database connections or, in our case, creating the database tables by calling `init_db()`.

* **On Shutdown (Code after `yield`):** This code runs once, right before the server stops completely (e.g., when you press `Ctrl+C`). It's used for cleanup tasks like gracefully closing database connections or releasing other resources.

* **The `init_db()` function** is safe to run even if your database already exists and contains data.

##### How it Works
The core of your `init_db()` function is the command `SQLModel.metadata.create_all(engine)`.

This function works idempotently:
1.  It first **inspects** the database to see which tables already exist.
2.  It then issues `CREATE TABLE` statements **only for tables that are missing**.
3.  It will **not** modify, alter, or delete any existing tables or the data within them.

So, if you run the app and your `users` and `bookmarks` tables are already there, `create_all()` will simply do nothing.

##### Important Consideration: Making Changes
If you later change a model (for example, by adding a new column), running the app again will **not** update the existing table. `create_all()` only creates missing tables; it does not handle updates.

This is exactly why we set up **Alembic** in Chapter 2. You must use Alembic migrations to apply changes to an existing database.

#### Refactor the health and status Endpoint Paths

To avoid creating a redundant URL like `/api/v1/health/health`, you should update the path in the endpoint decorator itself to be `/`.

The path defined in the endpoint is **relative** to the `prefix` it's included with.

##### The Correct Way

The prefix in the master router defines the resource's path, and the decorator in the route file defines the action on that resource.

**1. Update `app/api/routes/health.py`**
Change the path from `"/health"` to `"/"`.

```python
# ... imports
router = APIRouter()

@router.get("/") # ✅ Changed from "/health"
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "project": settings.PROJECT_NAME}
```

**2. Update `app/api/routes/status.py`**
Similarly, change the path from `"/status"` to `"/"`.

```python
# ... imports and other code
router = APIRouter()

@router.get("/", response_model=StatusResponse) # ✅ Changed from "/status"
async def get_status():
    # ...
```

##### How The Final URL is Assembled

FastAPI combines the paths like this:

`app.include_router(..., prefix="/api/v1")` + `api_router.include_router(..., prefix="/health")` + `@router.get("/")`  
➡️ Results in the final URL: `/api/v1/health`

This makes your code more modular and easier to read.

#### 🧪 Explore the Initial Endpoints

Start your server (`fastapi dev app/main.py`) and visit `http://localhost:8000/api/v1/health` and `http://localhost:8000/api/v1/status` to confirm the routing is working.

### Step 5: User Endpoints

Now we'll build, wire, and test the CRUD endpoints for managing users.

**1. Create `app/api/routes/users.py`**

```python
from typing import List
from fastapi import APIRouter, HTTPException, status, Query
from sqlmodel import select, func
from app.api.deps import SessionDep, CurrentUser
from app.models import User, UserCreate, UserRead, UserUpdate
from app.core.security import get_password_hash

router = APIRouter()


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: SessionDep
):
    """Create a new user"""
    # Check if user exists
    existing_user = db.exec(
        select(User).where(
            (User.username == user_in.username) | 
            (User.email == user_in.email)
        )
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    user = User(
        **user_in.model_dump(exclude={"password"}),
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/", response_model=List[UserRead])
def read_users(
    db: SessionDep,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of items to return"),
):
    """Get list of users"""
    users = db.exec(
        select(User)
        .offset(skip)
        .limit(limit)
    ).all()
    
    return users


@router.get("/me", response_model=UserRead)
def read_user_me(current_user: CurrentUser):
    """Get current user"""
    return current_user


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    db: SessionDep
):
    """Get user by ID"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: SessionDep,
    current_user: CurrentUser
):
    """Update user (only own profile)"""
    # Check if user can update this profile
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update own profile"
        )
    
    # Get user
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    from datetime import datetime
    user.updated_at = datetime.utcnow()
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: SessionDep,
    current_user: CurrentUser
):
    """Delete user (only own profile)"""
    # Check if user can delete this profile
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete own profile"
        )
    
    # Get user
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Delete user (cascade will handle bookmarks)
    db.delete(user)
    db.commit()
```

**2. Wire Up the User Router**
Update `app/api/routes/__init__.py`:

```python
from fastapi import APIRouter
from . import health, status, users # Add users

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(status.router, prefix="/status", tags=["status"])
api_router.include_router(users.router, prefix="/users", tags=["users"]) # Add this line
```

#### Dissecting the User Endpoints 🧐

This file puts all our previous chapters' work into practice.

  - **Clear CRUD Patterns**: Each function maps to a specific action (Create, Read, Update, Delete). Notice the HTTP method decorators (`@router.post`, `@router.get`, etc.) and the use of proper HTTP status codes (`status.HTTP_201_CREATED`, `status.HTTP_204_NO_CONTENT`).
  - **Dependency Injection in Action**: Look at the function signatures, like `def create_user(user_in: UserCreate, db: SessionDep)`. FastAPI sees `db: SessionDep` and automatically calls our `get_db` dependency to provide a database session. It's clean and requires no extra code inside the function.
  - **Using Different Schemas**: The `create_user` endpoint is a perfect example of using the models from Chapter 2. It accepts a `UserCreate` model (with a plaintext password), creates a `User` table model (with a hashed password), and returns a `UserRead` model (which hides the password). This ensures security and a clean API contract.
  - **Authorization**: The `update_user` and `delete_user` endpoints check if `current_user.id == user_id`. This is a basic but critical authorization check to ensure users can only modify their own profiles.

#### 🧪 Test Your User API

Start your server (`fastapi dev app/main.py`). The following `curl` commands will let you test all the user endpoints. Open your terminal to run them.

**1. Create a User**
This will create a new user. Note the `id` in the response, as you'll need it for the next steps.

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "testpass123"
  }'
```

*Expected Response (the `id` may vary):*

```json
{"username":"testuser","email":"test@example.com","full_name":"Test User","is_active":true,"id":1,"created_at":"...","updated_at":"..."}
```

**2. Get the Current User (`/me`)**
This endpoint uses our placeholder dependency. It will find the `testuser` we just created and return it. The `Authorization` header is required, but the token value doesn't matter for now.

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer anytoken"
```

**3. Update the User**
Let's update the user's full name. Use the `id` you received when creating the user.

```bash
# Replace {user_id} with the actual ID (e.g., 1)
curl -X PATCH "http://localhost:8000/api/v1/users/{user_id}" \
  -H "Authorization: Bearer anytoken" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Test User Updated"}'
```

*Expected Response:*

```json
{"username":"testuser","email":"test@example.com","full_name":"Test User Updated","is_active":true,"id":1,"created_at":"...","updated_at":"..."}
```

**4. Delete the User**
Finally, let's delete the user we created. A successful deletion returns no content.

```bash
# Replace {user_id} with the actual ID
curl -X DELETE "http://localhost:8000/api/v1/users/{user_id}" \
  -H "Authorization: Bearer anytoken"
```

You should receive no output and a `204 No Content` status, which you can see by adding the `-v` flag to curl: `curl -v -X DELETE ...`

#### 🤖 Automated Testing for Users

Create `app/tests/test_users.py`:

```python
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User

def test_create_user(client: TestClient):
    """Test creating a new user successfully."""
    response = client.post(
        "/api/v1/users/",
        json={"username": "newuser", "email": "new@example.com", "password": "newpassword123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert "hashed_password" not in data

def test_read_user_me(client: TestClient, test_user: User):
    """Test fetching the current user, which is mocked to be test_user."""
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username

def test_list_users(client: TestClient, session: Session, test_user: User):
    """Test listing users."""
    # The test_user fixture already created one user. Let's create another.
    user2 = User(username="user2", email="user2@example.com", hashed_password="hash")
    session.add(user2)
    session.commit()
    
    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["username"] == test_user.username
    assert data[1]["username"] == user2.username

def test_update_user(client: TestClient, test_user: User):
    """Test updating the current user's profile."""
    new_full_name = "Updated Test User"
    response = client.patch(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": "Bearer test"},
        json={"full_name": new_full_name}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == new_full_name
    assert data["username"] == test_user.username

def test_delete_user(client: TestClient, session: Session, test_user: User):
    """Test deleting the current user's profile."""
    response = client.delete(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code == 204

    # Verify the user is actually gone from the database
    deleted_user = session.get(User, test_user.id)
    assert deleted_user is None
```

#### Run Your New Tests

From your project's root directory, run `pytest`:

```bash
pytest app/tests/test_users.py -v
```

*(This test file uses the `client` and `test_user` fixtures from `conftest.py`)*

### Step 6: Bookmark Endpoints

Repeat the pattern for the `Bookmark` resource.

**1. Create `app/api/routes/bookmarks.py`** with all the bookmark CRUD endpoints. These endpoints are more complex as they involve handling the many-to-many relationship with tags.

```python
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from sqlmodel import select, func, or_
from app.api.deps import SessionDep, CurrentUser
from app.models import (
    Bookmark, BookmarkCreate, BookmarkRead, BookmarkUpdate,
    Tag, BookmarkTag
)

router = APIRouter()


@router.post("/", response_model=BookmarkRead, status_code=status.HTTP_201_CREATED)
def create_bookmark(
    bookmark_in: BookmarkCreate,
    db: SessionDep,
    current_user: CurrentUser
):
    """Create a new bookmark"""
    # Create the bookmark instance without the tags
    bookmark = Bookmark.model_validate(bookmark_in, update={"user_id": current_user.id})

    # Handle tags
    if bookmark_in.tags:
        for tag_name in set(bookmark_in.tags): # Use set to handle duplicate tags
            # Find existing tag or create a new one
            tag = db.exec(select(Tag).where(Tag.name == tag_name.lower())).first()
            if not tag:
                tag = Tag(name=tag_name.lower())
                # We don't need to commit here, the session tracks the new tag
            
            # Associate the tag with the bookmark
            bookmark.tags.append(tag)

    # Add the bookmark (with its relationships) to the session
    db.add(bookmark)
    # Commit once to save the bookmark, any new tags, and the relationships
    db.commit()
    # Refresh to get all the data back from the DB, including relationships
    db.refresh(bookmark)

    return bookmark


@router.get("/", response_model=List[BookmarkRead])
def read_bookmarks(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search in title and description"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    is_favorite: Optional[bool] = Query(None, description="Filter favorites only")
):
    """Get user's bookmarks with optional filtering"""
    # Base query
    query = select(Bookmark).where(Bookmark.user_id == current_user.id)
    
    # Apply filters
    if search:
        search_filter = or_(
            Bookmark.title.contains(search),
            Bookmark.description.contains(search),
            Bookmark.url.contains(search)
        )
        query = query.where(search_filter)
    
    if is_favorite is not None:
        query = query.where(Bookmark.is_favorite == is_favorite)
    
    if tag:
        # Join with tags
        query = query.join(BookmarkTag).join(Tag).where(Tag.name == tag.lower())
    
    # Execute query
    bookmarks = db.exec(
        query
        .order_by(Bookmark.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    
    # Format response with tags
    result = []
    for bookmark in bookmarks:
        bookmark_dict = bookmark.model_dump()
        bookmark_dict["tags"] = [tag.name for tag in bookmark.tags]
        result.append(BookmarkRead(**bookmark_dict))
    
    return result


@router.get("/stats")
def get_bookmark_stats(
    db: SessionDep,
    current_user: CurrentUser
):
    """Get user's bookmark statistics"""
    total = db.exec(
        select(func.count(Bookmark.id))
        .where(Bookmark.user_id == current_user.id)
    ).one()
    
    favorites = db.exec(
        select(func.count(Bookmark.id))
        .where(Bookmark.user_id == current_user.id)
        .where(Bookmark.is_favorite == True)
    ).one()
    
    # Get tag counts
    tag_counts = db.exec(
        select(Tag.name, func.count(BookmarkTag.bookmark_id))
        .join(BookmarkTag)
        .join(Bookmark)
        .where(Bookmark.user_id == current_user.id)
        .group_by(Tag.name)
        .order_by(func.count(BookmarkTag.bookmark_id).desc())
    ).all()
    
    return {
        "total_bookmarks": total,
        "total_favorites": favorites,
        "tags": [{"name": name, "count": count} for name, count in tag_counts]
    }


@router.get("/{bookmark_id}", response_model=BookmarkRead)
def read_bookmark(
    bookmark_id: int,
    db: SessionDep,
    current_user: CurrentUser
):
    """Get bookmark by ID"""
    bookmark = db.get(Bookmark, bookmark_id)
    
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    
    # Check ownership
    if bookmark.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this bookmark"
        )
    
    return BookmarkRead(
        **bookmark.model_dump(),
        tags=[tag.name for tag in bookmark.tags]
    )


@router.patch("/{bookmark_id}", response_model=BookmarkRead)
def update_bookmark(
    bookmark_id: int,
    bookmark_in: BookmarkUpdate,
    db: SessionDep,
    current_user: CurrentUser
):
    """Update bookmark"""
    # Get bookmark
    bookmark = db.get(Bookmark, bookmark_id)
    
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    
    # Check ownership
    if bookmark.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this bookmark"
        )
    
    # Update fields
    update_data = bookmark_in.model_dump(exclude_unset=True)
    
    # Handle tags separately
    if "tags" in update_data:
        new_tags = update_data.pop("tags")
        
        # Remove existing tags
        db.exec(
            select(BookmarkTag)
            .where(BookmarkTag.bookmark_id == bookmark_id)
        ).all()
        for bt in db.exec(
            select(BookmarkTag).where(BookmarkTag.bookmark_id == bookmark_id)
        ).all():
            db.delete(bt)
        
        # Add new tags
        for tag_name in new_tags:
            tag = db.exec(select(Tag).where(Tag.name == tag_name.lower())).first()
            if not tag:
                tag = Tag(name=tag_name.lower())
                db.add(tag)
                db.commit()
                db.refresh(tag)
            
            bookmark_tag = BookmarkTag(
                bookmark_id=bookmark.id,
                tag_id=tag.id
            )
            db.add(bookmark_tag)
    
    # Update other fields
    for field, value in update_data.items():
        setattr(bookmark, field, value)
    
    from datetime import datetime
    bookmark.updated_at = datetime.utcnow()
    
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    
    return BookmarkRead(
        **bookmark.model_dump(),
        tags=[tag.name for tag in bookmark.tags]
    )


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    bookmark_id: int,
    db: SessionDep,
    current_user: CurrentUser
):
    """Delete bookmark"""
    bookmark = db.get(Bookmark, bookmark_id)
    
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    
    # Check ownership
    if bookmark.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this bookmark"
        )
    
    db.delete(bookmark)
    db.commit()
```

**2. Wire Up the Bookmark Router**
Update `app/api/routes/__init__.py`:

```python
from fastapi import APIRouter
from . import health, status, users, bookmarks # Add bookmarks

api_router = APIRouter()
# ... other routers
api_router.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"]) # Add this line
```

#### Dissecting the Bookmark Endpoints 🧐

  - **Managing Relationships**: The `create_bookmark` and `update_bookmark` endpoints show how to handle a many-to-many relationship. The logic involves two stages: first, creating the primary `Bookmark` object, and second, looping through the tag names to either find existing `Tag` records or create new ones, and finally creating the `BookmarkTag` entries to link them together.
  - **Complex Query Building**: The `read_bookmarks` endpoint demonstrates the power of SQLModel's query builder. We start with a base query and conditionally add more `.where()` clauses for filtering and `.join()` clauses to link tables for searching by tag. This is an efficient and readable way to build dynamic SQL queries.
  - **Aggregations for Stats**: The `/stats` endpoint uses `func.count()` to perform database-level aggregations. This is much more efficient than fetching all records and counting them in Python. It shows how to get total counts and even grouped counts for tag popularity.
  - **Ownership Checks**: Every endpoint that accesses a specific bookmark first fetches it and then verifies that `bookmark.user_id == current_user.id`. This is a critical security check to ensure users can only see and modify their own data.

#### 🧪 Test Your Bookmark API

Start your server (`fastapi dev app/main.py`). The following `curl` commands will let you test the boomark endpoints.

**Prerequisites:**

Ensure `testuser` exists:

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "testpass123"
  }'
```

**1. Create a New Bookmark**
Use any non-empty string for the Bearer token. The placeholder dependency only requires the header to be present. Note the `id` from the response.

```bash
curl -X POST "http://localhost:8000/api/v1/bookmarks/" \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://sqlmodel.tiangolo.com/",
    "title": "SQLModel Docs",
    "tags": ["python", "orm"]
  }'
```

**2. List All Your Bookmarks**
This will retrieve all bookmarks associated with the placeholder `testuser`.

```bash
curl -X GET "http://localhost:8000/api/v1/bookmarks/" \
  -H "Authorization: Bearer test"
```

**3. Update a Bookmark**
Use the `id` you received when creating the bookmark.

```bash
# Replace {bookmark_id} with the actual ID
curl -X PATCH "http://localhost:8000/api/v1/bookmarks/{bookmark_id}" \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d '{"is_favorite": true}'
```

**4. Delete the Bookmark**
A successful deletion returns an empty response with a `204 No Content` status.

```bash
# Replace {bookmark_id} with the actual ID
curl -X DELETE "http://localhost:8000/api/v1/bookmarks/{bookmark_id}" \
  -H "Authorization: Bearer test"
```

#### 🤖 Automated Testing for Bookmarks

Create `app/tests/test_bookmarks.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User, Bookmark, Tag

# The 'client' and 'test_user' fixtures are used from your conftest.py

def test_create_bookmark(client: TestClient, test_user: User):
    """Test creating a bookmark for the current user."""
    response = client.post(
        "/api/v1/bookmarks/",
        # The header is required, but the token value doesn't matter for now
        headers={"Authorization": "Bearer test"},
        json={
            "url": "https://test.com", 
            "title": "Test Bookmark", 
            "tags": ["testing"]
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Bookmark"
    assert data["user_id"] == test_user.id
    assert data["tags"] == ["testing"]

def test_read_bookmarks(client: TestClient, session: Session, test_user: User):
    """Test reading a list of bookmarks."""
    b1 = Bookmark(url="https://site1.com", title="Site 1", user_id=test_user.id)
    b2 = Bookmark(url="https://site2.com", title="Site 2", user_id=test_user.id)
    session.add_all([b1, b2])
    session.commit()

    response = client.get("/api/v1/bookmarks/", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Assuming default sort is created_at descending
    assert data[0]["title"] == "Site 2"
    assert data[1]["title"] == "Site 1"

def test_update_bookmark(client: TestClient, session: Session, test_user: User):
    """Test updating a user's own bookmark."""
    bookmark = Bookmark(url="https://original.com", title="Original Title", user_id=test_user.id)
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    response = client.patch(
        f"/api/v1/bookmarks/{bookmark.id}",
        headers={"Authorization": "Bearer test"},
        json={"title": "Updated Title", "is_favorite": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["is_favorite"] is True

def test_delete_bookmark(client: TestClient, session: Session, test_user: User):
    """Test deleting a user's own bookmark."""
    bookmark = Bookmark(url="https://todelete.com", title="To Delete", user_id=test_user.id)
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    response = client.delete(f"/api/v1/bookmarks/{bookmark.id}", headers={"Authorization": "Bearer test"})
    assert response.status_code == 204

    # Verify it's gone
    deleted_bookmark = session.get(Bookmark, bookmark.id)
    assert deleted_bookmark is None

def test_fail_to_access_other_user_bookmark(client: TestClient, session: Session, test_user: User):
    """Test that a user cannot access another user's bookmark."""
    # The authenticated user is 'testuser'
    other_user = User(username="otheruser", email="other@example.com", hashed_password="hash")
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    other_bookmark = Bookmark(url="https://secret.com", title="Secret", user_id=other_user.id)
    session.add(other_bookmark)
    session.commit()
    session.refresh(other_bookmark)

    # 'testuser' tries to access other_bookmark
    response = client.get(f"/api/v1/bookmarks/{other_bookmark.id}", headers={"Authorization": "Bearer test"})
    assert response.status_code == 403 # Forbidden
```

#### Run Your New Tests

From your project's root directory, run `pytest`:

```bash
pytest app/tests/test_bookmarks.py -v
```

### Step 7: Tag Endpoints

Finally, add the endpoints for tags, these endpoints are read-only and provide insights into how tags are being used.

**1. Create `app/api/routes/tags.py`** with the tag listing endpoints.

```python
from typing import List
from fastapi import APIRouter, Query
from sqlmodel import select, func
from app.api.deps import SessionDep, CurrentUser
from app.models import Tag, TagRead, BookmarkTag, Bookmark

router = APIRouter()


@router.get("/", response_model=List[TagRead])
def read_tags(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """Get all tags used by the current user"""
    # Query tags with bookmark count
    tags_query = (
        select(
            Tag,
            func.count(BookmarkTag.bookmark_id).label("bookmark_count")
        )
        .join(BookmarkTag)
        .join(Bookmark)
        .where(Bookmark.user_id == current_user.id)
        .group_by(Tag.id)
        .order_by(func.count(BookmarkTag.bookmark_id).desc())
        .offset(skip)
        .limit(limit)
    )
    
    results = db.exec(tags_query).all()
    
    return [
        TagRead(
            id=tag.id,
            name=tag.name,
            created_at=tag.created_at,
            bookmark_count=count
        )
        for tag, count in results
    ]


@router.get("/popular", response_model=List[dict])
def read_popular_tags(
    db: SessionDep,
    limit: int = Query(10, ge=1, le=50),
):
    """Get most popular tags across all users"""
    popular_tags = db.exec(
        select(
            Tag.name,
            func.count(BookmarkTag.bookmark_id).label("usage_count")
        )
        .join(BookmarkTag)
        .group_by(Tag.name)
        .order_by(func.count(BookmarkTag.bookmark_id).desc())
        .limit(limit)
    ).all()
    
    return [
        {"name": name, "usage_count": count}
        for name, count in popular_tags
    ]
```

**2. Wire Up the Tag Router**
Update `app/api/routes/__init__.py`:

```python
from fastapi import APIRouter
from . import health, status, users, bookmarks, tags # Add tags

api_router = APIRouter()
# ... other routers
api_router.include_router(tags.router, prefix="/tags", tags=["tags"]) # Add this line
```
#### Dissecting the Tag Endpoints 🧐

These endpoints demonstrate advanced, read-only data aggregation.

  - **Calculated Fields**: The main `GET /` endpoint calculates the `bookmark_count` for each tag on the fly. It does this by joining across three tables (`Tag`, `BookmarkTag`, `Bookmark`) and using `func.count()` and `.group_by()` to get the count per tag. This is far more efficient than calculating it in Python.
  - **Custom Response Model**: The result of the query returns a tuple `(Tag, count)`. We then loop through these results and construct our `TagRead` Pydantic models to fit the desired response shape, which includes the calculated `bookmark_count`.
  - **Public Data**: The `/popular` endpoint is an example of an endpoint that doesn't depend on a `current_user`. It provides public, aggregated data on the most-used tags across the entire platform.

#### 🧪 Test Your Tag API with `curl`

The tag endpoints are read-only; tags are created when you create or update bookmarks. So first, we need to create some data.

**Prerequisites:**

Ensure `testuser` exists:

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "testpass123"
  }'
```

#### 1\. Add Bookmarks to Create Tags

Run these commands to create two bookmarks with some overlapping tags.

```bash
# Create first bookmark with tags 'python' and 'api'
curl -X POST "http://localhost:8000/api/v1/bookmarks/" \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://fastapi.tiangolo.com/",
    "title": "FastAPI",
    "tags": ["python", "api"]
  }'

# Create second bookmark with tags 'python' and 'sql'
curl -X POST "http://localhost:8000/api/v1/bookmarks/" \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://sqlmodel.tiangolo.com/",
    "title": "SQLModel",
    "tags": ["python", "sql"]
  }'
```

#### 2\. Test the User-Specific Tags Endpoint

This endpoint gets all tags used by the current user (`testuser`), along with how many of their bookmarks use each tag.

```bash
curl -X GET "http://localhost:8000/api/v1/tags/" \
  -H "Authorization: Bearer test"
```

*Expected Response (order may vary):*

```json
[
  {
    "name": "python",
    "id": 1,
    "created_at": "...",
    "bookmark_count": 2
  },
  {
    "name": "api",
    "id": 2,
    "created_at": "...",
    "bookmark_count": 1
  },
  {
    "name": "sql",
    "id": 3,
    "created_at": "...",
    "bookmark_count": 1
  }
]
```

#### 3\. Test the Popular Tags Endpoint

This endpoint is public and shows the most used tags across *all* users. No `Authorization` header is needed.

```bash
curl -X GET "http://localhost:8000/api/v1/tags/popular"
```

*Expected Response (will be the same as above since we only have one user):*

```json
[
  {
    "name": "python",
    "usage_count": 2
  },
  {
    "name": "api",
    "usage_count": 1
  },
  {
    "name": "sql",
    "usage_count": 1
  }
]
```

#### 🤖 Automated Testing for Tags

Create a new test file, `app/tests/test_tags.py`.

```python
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User, Bookmark, Tag

def test_read_user_tags(client: TestClient, session: Session, test_user: User):
    """Test reading tags for the current user, ensuring it's scoped correctly."""
    # Arrange: Create data for two different users
    other_user = User(username="other", email="other@example.com", hashed_password="pw")
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    # Tags for test_user
    b1 = Bookmark(url="https://s1.com", title="S1", user_id=test_user.id)
    b2 = Bookmark(url="https://s2.com", title="S2", user_id=test_user.id)
    tag_python = Tag(name="python")
    tag_fastapi = Tag(name="fastapi")
    b1.tags.extend([tag_python, tag_fastapi])
    b2.tags.append(tag_python)
    
    # Tag for other_user
    b3 = Bookmark(url="https://s3.com", title="S3", user_id=other_user.id)
    tag_docker = Tag(name="docker")
    b3.tags.extend([tag_python, tag_docker])

    session.add_all([b1, b2, b3])
    session.commit()

    # Act: Fetch tags for 'test_user'
    response = client.get("/api/v1/tags/", headers={"Authorization": "Bearer test"})
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    
    # Should only return tags used by test_user ('python', 'fastapi')
    # and should not include 'docker'
    assert len(data) == 2 
    
    # The default sort is by count descending
    assert data[0]["name"] == "python"
    assert data[0]["bookmark_count"] == 2
    assert data[1]["name"] == "fastapi"
    assert data[1]["bookmark_count"] == 1

def test_read_popular_tags(client: TestClient, session: Session, test_user: User):
    """Test the public popular tags endpoint."""
    # Arrange
    # Step 1: Create the 'other' user and commit to get its ID.
    other_user = User(username="other", email="other@example.com", hashed_password="pw")
    session.add(other_user)
    session.commit()
    session.refresh(other_user) # Load the new ID into the object

    # Step 2: Now create bookmarks for both users with valid user_ids.
    b1 = Bookmark(url="https://s1.com", title="S1", user_id=test_user.id)
    b2 = Bookmark(url="https://s2.com", title="S2", user_id=other_user.id) # Now uses a valid ID
    tag_python = Tag(name="python")
    tag_public = Tag(name="public")
    
    # Add to session and commit
    session.add_all([b1, b2, tag_python, tag_public])
    session.commit()

    # Step 3: Create the relationships
    b1.tags.append(tag_python)
    b1.tags.append(tag_public)
    b2.tags.append(tag_python) # 'python' is used again
    session.add_all([b1, b2])
    session.commit()

    # Act: Fetch popular tags (no auth needed)
    response = client.get("/api/v1/tags/popular")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Create a dictionary for easier, order-independent checking
    tag_counts = {item["name"]: item["usage_count"] for item in data}
    assert tag_counts["python"] == 2
    assert tag_counts["public"] == 1
```

#### Run Your New Tests

From your project's root directory, run `pytest`:

```bash
pytest app/tests/test_tags.py -v
```

#### Dissecting the Tag Tests 🧐

  - **Complex Scenarios**: The `test_read_user_tags` test is particularly important. It creates data for **two different users** to explicitly verify that the `/api/v1/tags/` endpoint correctly scopes the results to only the currently authenticated user.
  - **Testing Aggregations**: These tests verify the `func.count()` logic in your endpoints. We create a known number of bookmarks with specific tags and then assert that the `bookmark_count` and `usage_count` fields in the API response match what we expect.
  - **Public vs. Private**: We test both the protected endpoint (which requires a header) and the public `/popular` endpoint (which does not), ensuring both work as intended.


### Understanding the Implementation

**Key Patterns:**

1.  **Dependency Injection**: Reusable components like `SessionDep` and `CurrentUser` are injected into our endpoints, keeping them clean and testable.
2.  **Type Safety**: All request and response models are validated automatically by FastAPI, reducing bugs.
3.  **Error Handling**: We use `HTTPException` to return proper HTTP status codes and clear error messages to the client.
4.  **Query Building**: SQLModel provides a powerful and readable way to build simple and complex database queries with filtering, joins, and aggregations.

### Common CRUD Patterns

**CREATE (POST)**:

  - Validate input data using a `...Create` model.
  - Check for duplicates or other business rules.
  - Create the database object and return it using a `...Read` model.
  - Status: 201 Created

**READ (GET)**:

  - For lists, use pagination (`skip`, `limit`).
  - Allow for filtering and searching via query parameters.
  - Status: 200 OK

**UPDATE (PATCH/PUT)**:

  - Check that the resource exists.
  - Verify ownership or permissions.
  - Update only the fields provided in the `...Update` model.
  - Status: 200 OK

**DELETE (DELETE)**:

  - Check that the resource exists.
  - Verify ownership or permissions.
  - Remove the resource from the database.
  - Status: 204 No Content

### Pro Tips

1.  **Use PATCH for partial updates**: This is more user-friendly as it doesn't require sending the entire object.
2.  **Always paginate lists**: Never return an unbounded list of items from your database.
3.  **Check ownership on every relevant endpoint**: This is a critical security measure.
4.  **Return meaningful error messages**: This helps developers using your API to debug issues quickly.

### What's Next?

In Chapter 4, we'll implement proper JWT authentication so our API is actually secure. No more mock users\!

### Exercises

1.  **Add sorting**: Allow sorting bookmarks by date, title, or favorites.
2.  **Bulk operations**: Create an endpoint to delete multiple bookmarks at once.
3.  **Export endpoint**: Create an endpoint to export a user's bookmarks as JSON or CSV.

💡 **Remember**: Good APIs are predictable. Follow REST conventions and your users will thank you!


### Optional: Create Test Data

To make testing easier, we'll create a simple script to populate our database with a test user and some sample bookmarks.

Create `create_test_data.py` in your project root:

```python
from app.core.database import init_db, engine
from app.models import *
from app.core.security import get_password_hash
from sqlmodel import Session

# Initialize database
init_db()

with Session(engine) as session:
    # Create test user
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpass123")
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"Created user: {user.username}")
    
    # Create some bookmarks
    bookmarks_data = [
        {
            "url": "https://fastapi.tiangolo.com",
            "title": "FastAPI Documentation",
            "description": "Modern web framework for building APIs",
            "tags": ["python", "webdev", "api"]
        },
        {
            "url": "https://docs.python.org",
            "title": "Python Documentation",
            "description": "Official Python documentation",
            "tags": ["python", "documentation"]
        },
        {
            "url": "https://github.com",
            "title": "GitHub",
            "description": "Where the world builds software",
            "tags": ["development", "git", "opensource"]
        }
    ]
    
    for bm_data in bookmarks_data:
        tags = bm_data.pop("tags")
        bookmark = Bookmark(**bm_data, user_id=user.id)
        session.add(bookmark)
        session.commit()
        session.refresh(bookmark)
        
        # Add tags
        for tag_name in tags:
            tag = session.exec(select(Tag).where(Tag.name == tag_name)).first()
            if not tag:
                tag = Tag(name=tag_name)
                session.add(tag)
                session.commit()
                session.refresh(tag)
            
            bookmark_tag = BookmarkTag(bookmark_id=bookmark.id, tag_id=tag.id)
            session.add(bookmark_tag)
        
        session.commit()
        print(f"Created bookmark: {bookmark.title}")
    
    print("\nTest data created successfully!")
    print(f"Username: testuser")
    print(f"Password: testpass123")
```

#### Dissecting the Seeding Script 🧐

  - **Purpose**: This is a "seeding" script. Its only job is to populate a fresh database with some initial data so we can immediately start testing our API endpoints without having to manually create a user and bookmarks every time.
  - **Standalone Script**: This is not part of our FastAPI application; it's a separate, one-off script that we run from the command line. It imports our app's components (`engine`, models, `get_password_hash`) to interact directly with the database. This is a common pattern for setup and administrative tasks.
  - **`init_db()` call**: The script first calls `init_db()` to ensure the database and tables exist before it tries to add data.

