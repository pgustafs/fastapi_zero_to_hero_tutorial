Of course. Here is Chapter 3, updated with a "dissecting" section for each step to explain the implementation in detail and ensure it aligns with the concepts from previous chapters.

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
from app.core.database import engine
from app.core.config import settings
from app.core.database import get_session
from app.models import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Security scheme for JWT
security = HTTPBearer()


# Alias for DB session dependency
SessionDep = Annotated[Session, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: SessionDep
) -> User:
    """Get current authenticated user (placeholder for now)"""
    # We'll implement this properly in the authentication chapter
    # For now, return a mock user for testing
    from sqlmodel import select
    
    # This is temporary - we'll replace with real JWT validation
    user = db.exec(select(User).where(User.username == "testuser")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


# Type alias for current user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]
```

#### Dissecting the Dependencies 🧐

This file is central to FastAPI's **Dependency Injection** system. We create small, reusable functions that FastAPI will automatically run for us.

  - **`get_db()`**: This is a generator function that provides a database `Session` for a single request and guarantees it's closed afterward. This is the standard, robust pattern for managing database connections in FastAPI.
  - **`typing.Annotated`**: We use this modern Python feature to create clean type aliases for our dependencies. `SessionDep` now clearly represents a database session dependency. This makes our endpoint function signatures much easier to read.
  - **`get_current_user()`**: This function is a placeholder for our authentication logic. It demonstrates how one dependency (`get_current_user`) can depend on another (`db: SessionDep`). For now, it simply fetches our "testuser" from the database to simulate a logged-in user. We'll replace this with real JWT token validation in a later chapter.

-----

### Step 2: Create Security Utilities

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

-----

### Step 3: Create User Endpoints

Now we'll build the CRUD endpoints for managing users, using the dependencies and security utilities we just created.

Create `app/api/routes/users.py`:

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

#### Dissecting the User Endpoints 🧐

This file puts all our previous chapters' work into practice.

  - **Clear CRUD Patterns**: Each function maps to a specific action (Create, Read, Update, Delete). Notice the HTTP method decorators (`@router.post`, `@router.get`, etc.) and the use of proper HTTP status codes (`status.HTTP_201_CREATED`, `status.HTTP_204_NO_CONTENT`).
  - **Dependency Injection in Action**: Look at the function signatures, like `def create_user(user_in: UserCreate, db: SessionDep)`. FastAPI sees `db: SessionDep` and automatically calls our `get_db` dependency to provide a database session. It's clean and requires no extra code inside the function.
  - **Using Different Schemas**: The `create_user` endpoint is a perfect example of using the models from Chapter 2. It accepts a `UserCreate` model (with a plaintext password), creates a `User` table model (with a hashed password), and returns a `UserRead` model (which hides the password). This ensures security and a clean API contract.
  - **Authorization**: The `update_user` and `delete_user` endpoints check if `current_user.id == user_id`. This is a basic but critical authorization check to ensure users can only modify their own profiles.

-----

### Step 4: Create Bookmark Endpoints

These endpoints are more complex as they involve handling the many-to-many relationship with tags.

Create `app/api/routes/bookmarks.py`:

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
    # Create bookmark
    bookmark = Bookmark(
        **bookmark_in.model_dump(exclude={"tags"}),
        user_id=current_user.id
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    
    # Handle tags
    if bookmark_in.tags:
        for tag_name in bookmark_in.tags:
            # Get or create tag
            tag = db.exec(select(Tag).where(Tag.name == tag_name.lower())).first()
            if not tag:
                tag = Tag(name=tag_name.lower())
                db.add(tag)
                db.commit()
                db.refresh(tag)
            
            # Create bookmark-tag relationship
            bookmark_tag = BookmarkTag(
                bookmark_id=bookmark.id,
                tag_id=tag.id
            )
            db.add(bookmark_tag)
        
        db.commit()
        # Refresh the bookmark again to load the new tag relationships
        db.refresh(bookmark)
    
    # Exclude the 'tags' relationship from the model_dump
    return BookmarkRead(
        **bookmark.model_dump(exclude={"tags"}), 
        tags=[tag.name for tag in bookmark.tags]
    )


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

#### Dissecting the Bookmark Endpoints 🧐

  - **Managing Relationships**: The `create_bookmark` and `update_bookmark` endpoints show how to handle a many-to-many relationship. The logic involves two stages: first, creating the primary `Bookmark` object, and second, looping through the tag names to either find existing `Tag` records or create new ones, and finally creating the `BookmarkTag` entries to link them together.
  - **Complex Query Building**: The `read_bookmarks` endpoint demonstrates the power of SQLModel's query builder. We start with a base query and conditionally add more `.where()` clauses for filtering and `.join()` clauses to link tables for searching by tag. This is an efficient and readable way to build dynamic SQL queries.
  - **Aggregations for Stats**: The `/stats` endpoint uses `func.count()` to perform database-level aggregations. This is much more efficient than fetching all records and counting them in Python. It shows how to get total counts and even grouped counts for tag popularity.
  - **Ownership Checks**: Every endpoint that accesses a specific bookmark first fetches it and then verifies that `bookmark.user_id == current_user.id`. This is a critical security check to ensure users can only see and modify their own data.

-----

### Step 5: Create Tag Endpoints

These endpoints are read-only and provide insights into how tags are being used.

Create `app/api/routes/tags.py`:

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

#### Dissecting the Tag Endpoints 🧐

These endpoints demonstrate advanced, read-only data aggregation.

  - **Calculated Fields**: The main `GET /` endpoint calculates the `bookmark_count` for each tag on the fly. It does this by joining across three tables (`Tag`, `BookmarkTag`, `Bookmark`) and using `func.count()` and `.group_by()` to get the count per tag. This is far more efficient than calculating it in Python.
  - **Custom Response Model**: The result of the query returns a tuple `(Tag, count)`. We then loop through these results and construct our `TagRead` Pydantic models to fit the desired response shape, which includes the calculated `bookmark_count`.
  - **Public Data**: The `/popular` endpoint is an example of an endpoint that doesn't depend on a `current_user`. It provides public, aggregated data on the most-used tags across the entire platform.

-----

### Step 6: Wire Up the Routes

Now we need to connect all our new `APIRouter` modules to the main FastAPI application.

Create `app/api/routes/__init__.py` to consolidate all routers:

```python
from fastapi import APIRouter
from app.api.routes import health, status, users, bookmarks, tags

api_router = APIRouter()

# Include all route modules
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(status.router, prefix="/status", tags=["status"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
```

Update the URL path in `app/routes/health.py`.

```python
from fastapi import APIRouter
from app.core.config import settings

# Create an API router
router = APIRouter()


@router.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME
    }
```

Update the URL path `app/routes/status.py`.

```python
import re
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.core.config import settings

# Create an API router
router = APIRouter()


# Define a Pydantic model for the response structure
class StatusResponse(BaseModel):
    current_time: datetime = Field(..., example="2025-07-11T12:00:00.000000Z")
    database_url: str = Field(..., example="sqlite:///./b********.db")


def mask_db_url(url: str) -> str:
    """Masks credentials and sensitive parts of a database URL."""
    if url.startswith("sqlite"):
        # Mask the filename part for SQLite
        return re.sub(r'(\w+)\.db', '********.db', url)
    # For postgresql, mysql, etc.
    return re.sub(r'://(.*?):(.*?)@', r'://********:********@', url)


@router.get("/", response_model=StatusResponse)
async def get_status():
    """
    Returns the current server time and a masked database URL for status checks.
    """
    current_time = datetime.now(timezone.utc)
    masked_url = mask_db_url(settings.DATABASE_URL)
    
    return {
        "current_time": current_time,
        "database_url": masked_url,
    }
```

Update `app/main.py` to use the main `api_router` and a `lifespan` event handler to create the database tables on startup.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown"""
    # Startup
    init_db()
    yield
    # Shutdown (cleanup if needed)


# Create FastAPI instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }

```

#### Dissecting the Routing Setup 🧐

This step organizes our entire API.

  - **`api_router`**: The `app/api/routes/__init__.py` file acts as a master router. It imports the individual routers for health, status, users, bookmarks, and tags and combines them into a single `api_router`.
  - **`prefix` and `tags`**: When we include each router, we use `prefix` to add a URL path segment to all its endpoints (e.g., all user endpoints will start with `/users`). The `tags` argument groups the endpoints under a specific heading in the interactive API documentation, making it much more organized.
  - **`lifespan` manager**: This is the modern way to handle startup/shutdown logic in FastAPI. By passing our `lifespan` function to the `FastAPI` instance, we ensure that `init_db()` is called exactly once when the application starts up. This is more robust than running a separate script.
  - **Main Router Inclusion**: In `main.py`, we include the master `api_router` and give it a global prefix from our settings (`/api/v1`). This means a user endpoint like `/users/{user_id}` will now be available at the full path `/api/v1/users/{user_id}`.

-----

### Step 7: Create Test Data

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

-----

### 🧪 Test Your API

1.  **Create test data**:

```bash
python create_test_data.py
```

2.  **Start the server**:

```bash
fastapi dev app/main.py
```

3.  **Use the interactive docs**: Go to http://localhost:8000/docs

      - This is the easiest way to test. The docs will show you all the new endpoints.
      - You can authorize by clicking the "Authorize" button and pasting in any non-empty string (like "test") for now, because our `get_current_user` dependency is just a placeholder.
      - Try creating, reading, updating, and deleting resources.

4.  **Test with curl** (optional):

```bash
# Create a user
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "new@example.com",
    "full_name": "New User",
    "password": "newpass123"
  }'

# Get bookmarks for our test user
# We can use any string for the Bearer token for now
curl -X GET "http://localhost:8000/api/v1/bookmarks/" \
  -H "Authorization: Bearer test"
```

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

---

💡 **Remember**: Good APIs are predictable. Follow REST conventions and your users will thank you!