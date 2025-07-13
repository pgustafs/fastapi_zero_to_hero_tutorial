# Chapter 2: Database Models with SQLModel

## What is SQLModel?

SQLModel is a library that combines SQLAlchemy (database ORM) with Pydantic (data validation). It's like having one tool that handles both your database tables AND your API validation - created by the same author as FastAPI\!

## Why SQLModel Matters

1.  **Single source of truth**: One model for both database and API
2.  **Type safety**: Full type hints and validation
3.  **Less code**: No need to maintain separate database and Pydantic models
4.  **FastAPI integration**: Designed to work perfectly with FastAPI

## How SQLModel Works

SQLModel creates classes that are:

  - SQLAlchemy models (for database operations)
  - Pydantic models (for validation and serialization)
  - Regular Python classes (with full type support)

## Let's Build: Creating Our Database Models

### Step 1: Design Our Data Structure

Our bookmark system needs:

  - **Users**: Who can create and manage bookmarks
  - **Bookmarks**: The actual saved URLs with metadata
  - **Tags**: Categories to organize bookmarks
  - **BookmarkTags**: Many-to-many relationship

-----

#### Dissecting the Design 🧐

Before writing code, we've outlined our four core components. **Users** are the actors in our system. **Bookmarks** are the main objects they create. **Tags** help organize the bookmarks. Because one bookmark can have many tags, and one tag can be on many bookmarks, we need the **BookmarkTags** table to create a many-to-many relationship between them. This planning phase is crucial for building a solid application foundation.

-----

### Step 2: Create the User Model

Create `app/models/user.py`:

```python
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

# Add this block to help the ruff linter understand the 'Bookmark' type
if TYPE_CHECKING:
    from .bookmark import Bookmark

class UserBase(SQLModel):
    """Shared properties for User models"""
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    """Database model for users"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    bookmarks: List["Bookmark"] = Relationship(back_populates="owner")


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(min_length=8, max_length=100)


class UserRead(UserBase):
    """Schema for reading user data"""
    id: int
    created_at: datetime
    updated_at: datetime


class UserUpdate(SQLModel):
    """Schema for updating user data"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
```

#### Dissecting the User Models 🧐

This file perfectly illustrates the power of **SQLModel**. It allows us to define different "views" of our data for different purposes—some for the database and others for our API—all while reusing code.

  - **`UserBase(SQLModel)`**: This is our shared "blueprint." It doesn't represent a database table itself. Instead, it holds the common fields (`username`, `email`, etc.) that will be inherited by our other models. This keeps our code DRY (Don't Repeat Yourself).

  - **`User(UserBase, table=True)`**: This is our **database table model**. The key here is `table=True`, which tells SQLModel to treat this as a table definition. It inherits the fields from `UserBase` and adds columns that should only exist in the database, like `id` and `hashed_password`. It also defines the `Relationship` to the `Bookmark` model.

  - **`UserCreate(UserBase)`** and **`UserRead(UserBase)`**: These are **API data schemas**. They are not database tables.

      - `UserCreate` defines the data we expect when a new user signs up. It includes a plaintext `password` field, which we'll receive from the API but won't save directly to the database.
      - `UserRead` defines the data we send back to the client. It inherits the base fields, adds the `id` and timestamps, but crucially **omits the `hashed_password`** for security.

  - **`UserUpdate(SQLModel)`**: This is another API schema, designed for partial updates (e.g., `PATCH` requests). All its fields are `Optional`, meaning a client can send just the fields they want to change without having to provide the

-----

### Step 3: Create the Bookmark Model

Create `app/models/bookmark.py`:

```python
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

# Import the link model
from .bookmark_tag import BookmarkTag

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from .user import User
    from .tag import Tag


class BookmarkBase(SQLModel):
    """Shared properties for Bookmark models"""
    url: str = Field(index=True, max_length=2048)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_favorite: bool = Field(default=False)


class Bookmark(BookmarkBase, table=True):
    """Database model for bookmarks"""
    __tablename__ = "bookmarks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    owner: Optional["User"] = Relationship(back_populates="bookmarks")
    tags: List["Tag"] = Relationship(
        back_populates="bookmarks",
        link_model=BookmarkTag,
        # enable cascading deletes
        sa_relationship_kwargs={"cascade": "all, delete"}
    )


class BookmarkCreate(BookmarkBase):
    """Schema for creating a bookmark"""
    tags: Optional[List[str]] = Field(default=[], max_items=10)


class BookmarkRead(BookmarkBase):
    """Schema for reading bookmark data"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []


class BookmarkUpdate(SQLModel):
    """Schema for updating bookmark data"""
    url: Optional[str] = Field(None, max_length=2048)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_favorite: Optional[bool] = None
    tags: Optional[List[str]] = Field(None, max_items=10)
```

#### Dissecting the Bookmark Models 🧐

  - `BookmarkBase`: Holds the core properties of a bookmark.
  - `Bookmark`: The database table model (`table=True`). It includes the `user_id` with a `foreign_key="users.id"` to link each bookmark to its owner.
  - **Relationships**: We define two crucial relationships here.
      - `owner`: A link back to the `User` who owns the bookmark.
      - `tags`: The many-to-many relationship to `Tag`s. We tell SQLModel to use our `BookmarkTag` class as the `link_model`. We also add `sa_relationship_kwargs={"cascade": "all, delete"}` to automatically delete the link table entries if a bookmark is deleted.
  - `TYPE_CHECKING`: The `if TYPE_CHECKING:` block prevents circular import errors. The code inside only runs during type checking, not at runtime, allowing our tools to understand the model relationships without the program crashing.

### Step 4: Create the Tag Model

Create `app/models/tag.py`:

```python
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

# Import the link model
from .bookmark_tag import BookmarkTag

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from .bookmark import Bookmark


class TagBase(SQLModel):
    """Shared properties for Tag models"""
    name: str = Field(unique=True, index=True, max_length=50)


class Tag(TagBase, table=True):
    """Database model for tags"""
    __tablename__ = "tags"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    bookmarks: List["Bookmark"] = Relationship(
        back_populates="tags",
        link_model=BookmarkTag,
        sa_relationship_kwargs={"cascade": "all, delete"}
    )


class TagRead(TagBase):
    """Schema for reading tag data"""
    id: int
    created_at: datetime
    bookmark_count: Optional[int] = 0
```

#### Dissecting the Tag Models 🧐

  - `TagBase`: Contains the essential `name` field for a tag, which we've made `unique` and indexed for fast lookups.
  - `Tag`: The database model (`table=True`). It defines the other side of the many-to-many relationship with `Bookmark`. The `back_populates="tags"` parameter links it to the `tags` attribute in the `Bookmark` model, making the relationship fully bidirectional.
  - `TagRead`: This schema defines what a tag looks like when we send it to a client. We've added a `bookmark_count`, a useful piece of data that we can compute later.


### Step 5: Create the Link Model for the Many-to-Many Relationship

Our application needs to support a **many-to-many relationship**: a single bookmark can have multiple tags, and a single tag can be applied to multiple bookmarks.

In a SQL database, you can't link these two tables directly. You need a special table that sits in the middle, often called an **association table** or a **link table**. Its only job is to connect the `bookmarks` table and the `tags` table.

Let's create this model.

Create a new file, `app/models/bookmark_tag.py`:

```python
from typing import Optional
from sqlmodel import Field, SQLModel

# Link table for many-to-many relationship
class BookmarkTag(SQLModel, table=True):
    """Link table for bookmark-tag relationship"""
    __tablename__ = "bookmark_tags"
    
    bookmark_id: Optional[int] = Field(
        default=None, foreign_key="bookmarks.id", primary_key=True
    )
    tag_id: Optional[int] = Field(
        default=None, foreign_key="tags.id", primary_key=True
    )
```

#### Dissecting the `BookmarkTag` Model 🧐

  * **`table=True`**: This tells SQLModel to create a database table for this model.
  * **`bookmark_id` & `tag_id`**: These two columns will store the IDs of the bookmark and tag we want to connect.
  * **`foreign_key`**: Each field is a foreign key, pointing to the `id` column in the `bookmarks` and `tags` tables, respectively. This enforces data integrity.
  * **`primary_key=True`**: Both fields are marked as primary keys. When combined, this is a **composite primary key**. It ensures that a specific bookmark-and-tag pair can only exist once in the table. You can't tag the same bookmark with the exact same tag twice.

By creating this link model first, we can now cleanly connect our `Bookmark` and `Tag` models without running into circular import errors. Let's update them in the next step\!

-----

### Step 6: Fix Circular Imports

Create `app/models/__init__.py`:

```python
# Import models in an order that resolves dependencies

# Base models without relationships first (or stand-alone)
from .user import User, UserCreate, UserRead, UserUpdate

# Import the link model before the models that use it
from .bookmark_tag import BookmarkTag

# Import the models that have relationships
from .tag import Tag, TagRead
from .bookmark import Bookmark, BookmarkCreate, BookmarkRead, BookmarkUpdate


# This ensures all models are available when importing from app.models
__all__ = [
    "User", "UserCreate", "UserRead", "UserUpdate",
    "Bookmark", "BookmarkCreate", "BookmarkRead", "BookmarkUpdate",
    "Tag", "TagRead",
    "BookmarkTag",
]
```

#### Dissecting the `__init__.py` File 🧐

This file turns the `models` directory into a Python package. Its purpose here is twofold:

1.  **Control Import Order**: We import our models in a very specific sequence. We import `User` first, then the `BookmarkTag` link model, and finally the `Tag` and `Bookmark` models that depend on it. This solves the circular dependency problem definitively.
2.  **Simplify Imports**: By defining `__all__`, we specify a public API for our models package. This allows us to use a simple import statement like `from app.models import User, Bookmark` elsewhere in our application, making the code cleaner and easier to read.


### Step 7: Database Configuration

Create `app/core/database.py`:

```python
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
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL settings
    engine = create_engine(
        settings.DATABASE_URL,
        echo=True,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,         # Number of connections to maintain
        max_overflow=10      # Maximum overflow connections
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
```


#### Dissecting the Database Configuration 🧐

This file is the heart of our database connection.

  - `create_engine`: This function from SQLModel (via SQLAlchemy) creates the **engine**, which is the central point of communication with the database. We check if the `DATABASE_URL` is for SQLite or something else (like PostgreSQL) to apply specific connection settings. `echo=True` is great for development as it prints all the SQL queries being executed.
  - `init_db()`: A simple function that finds all our classes that inherit from `SQLModel` with `table=True` and creates the corresponding tables in the database.
  - `get_session()`: This is a generator function designed to be used as a FastAPI **dependency**. For each incoming API request, it will create a new database `Session`, `yield` it to the path operation function, and then automatically close the session when the request is finished. This ensures database connections are managed efficiently and safely.

### Step 8: Test Database Creation

Create `test_db.py` in your project root:

```python
from app.core.database import init_db, engine
from app.models import * # Import all models
from sqlmodel import Session, select

# Initialize database
init_db()
print("✅ Database tables created!")

# Test creating data
with Session(engine) as session:
    # Create a user
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="dummy_hash"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"✅ Created user: {user.username} (ID: {user.id})")
    
    # Create a bookmark
    bookmark = Bookmark(
        url="https://fastapi.tiangolo.com",
        title="FastAPI Documentation",
        description="Modern web framework for building APIs",
        user_id=user.id
    )
    session.add(bookmark)
    
    # Create tags
    python_tag = Tag(name="python")
    webdev_tag = Tag(name="webdev")
    session.add(python_tag)
    session.add(webdev_tag)
    session.commit()
    
    # Link bookmark to tags
    bookmark_tag1 = BookmarkTag(bookmark_id=bookmark.id, tag_id=python_tag.id)
    bookmark_tag2 = BookmarkTag(bookmark_id=bookmark.id, tag_id=webdev_tag.id)
    session.add(bookmark_tag1)
    session.add(bookmark_tag2)
    session.commit()
    
    print(f"✅ Created bookmark: {bookmark.title}")
    print(f"✅ Created tags: {python_tag.name}, {webdev_tag.name}")
    
    # Test querying
    statement = select(Bookmark).where(Bookmark.user_id == user.id)
    bookmarks = session.exec(statement).all()
    print(f"✅ Found {len(bookmarks)} bookmarks for user")
    
    # Clean up
    session.delete(bookmark)
    session.delete(python_tag)
    session.delete(webdev_tag)
    session.delete(user)
    session.commit()
    print("✅ Cleanup complete!")
```

Run the test:

```bash
python test_db.py
```

#### Dissecting the Test Script 🧐

This script is a "smoke test" to ensure everything we've built so far works together.

1.  **Initialization**: It first calls `init_db()` to create all the database tables from our models.
2.  **Data Creation**: It uses a `Session` to talk to the database. We create instances of our `User`, `Bookmark`, and `Tag` models.
3.  **`session.add()` & `session.commit()`**: We `add()` objects to the session to stage them for saving, and then `commit()` writes all staged changes to the database in a single transaction. Note that we `commit` multiple times to ensure we get the IDs generated by the database (`user.id`, `bookmark.id`, etc.) which are needed for subsequent steps.
4.  **Why Multiple Commits?**: We `commit()` after creating the `user` and `tags` so that the database can generate their primary key IDs. We need those `id`s available before we can create the `BookmarkTag` links, which rely on them as foreign keys.
5.  **Linking**: The crucial step where we create `BookmarkTag` instances to manually link the bookmark to its tags.
6.  **Querying**: We use `select()` to build a query and `session.exec()` to run it, verifying that we can retrieve the data we just created.
7.  **Cleanup**: We delete the objects we created to leave the database clean. Because we configured `cascade="all, delete"` on our `Bookmark` model's `tags` relationship, we only need to delete the main `Bookmark` object, and the `BookmarkTag` link entries are deleted automatically.

### 🧪 Explore Your Database

**For SQLite:**

1.  Install `DB Browser for SQLite` or the `SQLite Viewer` extension in VS Code
2.  Open `bookmarks.db` in your project folder
3.  Explore the tables and relationships

**For PostgreSQL:**

```bash
# Connect to PostgreSQL
psql -U your_username -d your_database

# List tables
\dt

# Describe a table
\d users
\d bookmarks
\d tags
\d bookmark_tags

# Exit
\q
```

### Step 9: Database Migrations with Alembic

Now that our models are defined, we'll set up **Alembic** for database version control. This allows us to apply incremental changes to our database schema as our application evolves, which is essential for any production application.

First, make sure you are in your project's **root directory** (the `smart-bookmarks` folder). This is where the `alembic` configuration should live.

Now, set up Alembic for database version control:

```bash
# In your project's root directory, run:
alembic init alembic
```

Running this command creates a new `alembic` directory and an `alembic.ini` configuration file at the top level of your project.

**Your folder structure should now look like this:**

```
smart-bookmarks/
├── alembic/         <-- Alembic created this directory
├── alembic.ini      <-- ...and this configuration file
├── .env
├── .gitignore
├── app/
├── requirements.txt
└── venv/
```

#### Dissecting the Alembic Setup 🧐

The `alembic init alembic` command creates a new `alembic` directory in our project. This directory contains configuration files and a `versions` folder. Alembic uses these files to manage our database schema. Instead of dropping and recreating tables every time we make a change, Alembic allows us to create incremental "migration" scripts, giving us version control for our database structure.

Next, update `alembic/env.py` to connect Alembic to our app's models and database configuration.

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from sqlmodel import SQLModel
# Add a comment to tell the ruff linter to ignore this line
from app.models import *  # noqa: F403
from app.core.config import settings

config = context.config

# Set database URL from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the crucial line: it points Alembic to our SQLModel models
target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

#### Dissecting `alembic/env.py` 🧐

The `env.py` file is the main configuration script for Alembic. The key changes we made are:

1.  **Import Models and Config**: We import our `settings` to get the database URL and `from app.models import *` to make Alembic aware of all our table definitions.
2.  **Set Database URL**: We dynamically set the `sqlalchemy.url` for Alembic using the URL from our application's settings, ensuring they always use the same database.
3.  **Set `target_metadata`**: This is the most important part. We point `target_metadata` to `SQLModel.metadata`. This tells Alembic to look at all the tables defined by our SQLModel classes when it compares our models to the current state of the database to auto-generate migration scripts.

Finally, create your first migration to generate the tables in the database.

```bash
# Create migration
alembic revision --autogenerate -m "Initial tables"

# Apply migration
alembic upgrade head

# Check status
alembic current
```

#### Dissecting the Migration Commands 🧐

  - `alembic revision --autogenerate -m "Initial tables"`: This command compares our SQLModels against the (currently empty) database. It sees that the `users`, `tags`, `bookmarks`, and `bookmark_tags` tables are missing and **auto-generates** a new Python script in the `alembic/versions` folder. This script contains the `upgrade()` and `downgrade()` functions to create or drop these tables. The `-m` flag adds a descriptive message.
  - `alembic upgrade head`: This command takes the latest migration script (referenced by `head`) and executes its `upgrade()` function, applying the changes to our database. In this case, it will run the `CREATE TABLE` commands.
  - `alembic current`: A utility command to show which migration version is currently applied to the database.

Of course. Here is the finalized version of Chapter 2, updated with a new section on automated model testing with `pytest` and a final step to commit your progress to Git.

### Step 10: Automated Tests for Models

The `test_db.py` script is great for a quick manual check, but for a robust application, we need automated tests. We'll use `pytest` to create unit tests for our models to verify that the fields, relationships, and database constraints work as expected.

**Why Test Models?**
While API tests check the whole system, model tests are focused and fast. They confirm the correctness of your data structure—the very foundation of your application—in isolation.

#### Create a Shared Test Fixture

To avoid duplicating code, we'll place our test database fixture in a special `pytest` file called `conftest.py`. Fixtures in this file are automatically available to all tests.

Create a new file, `app/tests/conftest.py`:

```python
import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

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
```

#### Dissecting `conftest.py` 🧐

  - **`conftest.py`**: This is a special `pytest` file. Any fixtures you define here are automatically discovered and can be used by any test file in the same directory and subdirectories without needing to be imported. It's the perfect place for shared setup code like a database connection.
  - **`session_fixture`**: This fixture sets up a clean, in-memory SQLite database, creates all your SQLModel tables, yields a session for the test to use, and then tears down the entire database afterward. This ensures every single test runs in complete isolation.

#### Create the Model Test File

Now, let's write the actual tests.

Create a new file, `app/tests/test_models.py`:

```python
from sqlmodel import Session
from app.models import User, Bookmark, Tag, BookmarkTag

def test_create_user(session: Session):
    """Test creating a User model and saving it to the database."""
    user = User(
        username="testuser", 
        email="test@example.com", 
        hashed_password="fakehash"
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    assert user.username == "testuser"
    assert user.created_at is not None

def test_create_bookmark(session: Session):
    """Test creating a Bookmark linked to a User."""
    user = User(
        username="testuser2", 
        email="test2@example.com", 
        hashed_password="fakehash"
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    bookmark = Bookmark(
        url="https://example.com",
        title="Example",
        user_id=user.id,
        owner=user
    )
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    assert bookmark.id is not None
    assert bookmark.user_id == user.id
    assert bookmark.owner.username == "testuser2"

def test_create_bookmark_with_tags(session: Session):
    """Test creating a bookmark with a many-to-many tag relationship."""
    # 1. Arrange: Create and commit the user first to get an ID
    user = User(username="taguser", email="tag@example.com", hashed_password="hash")
    session.add(user)
    session.commit()
    session.refresh(user)

    # 2. Now create the other objects using the valid user.id
    tag1 = Tag(name="python")
    tag2 = Tag(name="fastapi")
    bookmark = Bookmark(url="https://tiangolo.com", title="Typer", user_id=user.id)
    
    # 3. Add the new objects and commit again
    session.add(tag1)
    session.add(tag2)
    session.add(bookmark)
    session.commit()
    
    # Refresh to make sure all objects have IDs from the DB
    session.refresh(tag1)
    session.refresh(tag2)
    session.refresh(bookmark)

    # 4. Link them using the association table
    link1 = BookmarkTag(bookmark_id=bookmark.id, tag_id=tag1.id)
    link2 = BookmarkTag(bookmark_id=bookmark.id, tag_id=tag2.id)
    session.add(link1)
    session.add(link2)
    session.commit()

    # Refresh the bookmark to load the 'tags' relationship
    session.refresh(bookmark)

    # 5. Assert: Check if the relationships work
    assert len(bookmark.tags) == 2
    assert bookmark.tags[0].name == "python"
    assert bookmark.tags[1].name == "fastapi"
```

#### Run Your New Tests

From your project's root directory, run the tests:

```bash
pytest app/tests/test_models.py -v
```

You should see all three tests pass\!

#### Dissecting the Model Tests 🧐

  - **Direct Database Interaction**: Unlike API tests which use an HTTP client, these tests interact directly with the database `session` provided by our fixture. This allows us to test the model layer in isolation.
  - **Arrange, Act, Assert**: Each test follows this classic pattern. We first arrange the data by creating model instances, then act by adding them to the session and committing, and finally assert that the results are what we expect.
  - **`session.commit()`**: This command saves all pending changes (like new objects) to the database and assigns database-generated values like primary keys (`id`).
  - **`session.refresh(obj)`**: After committing, we use `refresh()` to update our Python object (`user`, `bookmark`, etc.) with the new data from the database, such as the `id` and default `created_at` timestamp. This is essential for testing database-generated values.

### Step 11: Commit Your Progress

You've completed all the data modeling, database setup, and initial testing for the project. This is a perfect milestone to save your work to Git.

```bash
# Add all new and modified files to Git
git add .

# Create a commit with a descriptive message
git commit -m "feat: Add database models, migrations, and tests"

# Push your changes to your GitHub repository
git push origin main
```

Your CI pipeline on GitHub Actions will now run and should pass, confirming that your new tests work and your code quality checks are met.

### Understanding What We Built

**Key Concepts:**

1.  **Model inheritance**: Base models for shared fields
2.  **Relationships**: One-to-many and many-to-many
3.  **Indexes**: For query performance
4.  **Constraints**: Unique fields, max lengths
5.  **Type safety**: Full typing throughout

**Database Design Decisions:**

  - Users own bookmarks (one-to-many)
  - Bookmarks can have multiple tags (many-to-many)
  - Timestamps for audit trail
  - Indexes on frequently queried fields

### PostgreSQL vs SQLite

**SQLite** (Development):

  - File-based, no server needed
  - Great for development and testing
  - Limited concurrent writes

**PostgreSQL** (Production):

  - Full-featured database server
  - Better performance and concurrency
  - Advanced features (JSON fields, full-text search)

To switch to PostgreSQL:

1.  Update `.env`:

<!-- end list -->

```env
DATABASE_URL="postgresql://user:password@localhost/bookmarks_db"
```

2.  Create PostgreSQL database:

<!-- end list -->

```bash
createdb bookmarks_db
```

3.  Run migrations:

<!-- end list -->

```bash
alembic upgrade head
```

### Pro Tips

1.  **Always use migrations** in production
2.  **Index foreign keys** for better join performance
3.  **Set appropriate field lengths** to prevent abuse
4.  **Use timestamps** for audit trails
5.  **Plan relationships** before coding

### What's Next?

In Chapter 3, we'll build our API endpoints to perform CRUD operations on these models. You'll see how FastAPI and SQLModel work together seamlessly\!

### Exercises

1.  **Add a field**: Add a `views_count` field to the Bookmark model
2.  **Create an index**: Add a composite index on (user\_id, created\_at)
3.  **Add validation**: Ensure URLs start with http:// or https://

-----

💡 **Tip**: Understanding your data model is crucial. Spend time getting it right - it's harder to change later\!