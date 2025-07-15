## Exercise Solutions

Here are the solutions and instructions for the exercises at the end of the chapter. These solutions build upon the existing code and demonstrate how to extend and refine your models.

-----

### Solution 1: Add a `views_count` Field to the Bookmark Model

This task involves adding a new field to track how many times a bookmark has been viewed. It requires a model change and a database migration.

#### Step 1: Update the Bookmark Models

First, we need to add the `views_count` field to our `Bookmark` models. We'll add it to the `BookmarkBase` class so it's included in all other models that inherit from it.

Edit `app/models/bookmark.py`:

```python
# app/models/bookmark.py

# ... other imports

class BookmarkBase(SQLModel):
    """Shared properties for Bookmark models"""

    url: str = Field(index=True, max_length=2048)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_favorite: bool = Field(default=False)
    # Add the new field with a default value of 0
    views_count: int = Field(default=0)
```

**Dissecting the Change** 🧐
By adding `views_count: int = Field(default=0)` to `BookmarkBase`, we ensure every bookmark will have this field. Setting `default=0` means new bookmarks will start with zero views automatically. Because `Bookmark` and `BookmarkRead` inherit from `BookmarkBase`, they get the new field without needing explicit changes.

#### Step 2: Create a Database Migration

Now that our model has changed, we need to update our database schema to match. Alembic makes this easy.

Run the following commands in your terminal:

```bash
# 1. Autogenerate a new migration script
alembic revision --autogenerate -m "Add views_count to Bookmark model"

# 2. Apply the migration to the database
alembic upgrade head
```

This will add the new `views_count` column with a `DEFAULT 0` value to your `bookmarks` table.

#### Dissecting the Migration File: Why Commit It? 🧐

**Yes, you should always commit your Alembic revision files to Git.** These files, found in `alembic/versions/`, are not temporary; they are a permanent record of your database's history.

  - **Importance:** Think of them as "version control for your database schema." By committing them alongside your code, you ensure that every developer on your team and every deployment environment (staging, production) can recreate the exact same database structure simply by running `alembic upgrade head`.
  - **In Production:** When you deploy new application code, part of your deployment process will be to run `alembic upgrade head` on your production database. This applies any new schema changes safely before the new code that relies on those changes is launched.

### Solution 2: Create a Composite Index on `(user_id, created_at)`

A **composite index** is an index on multiple columns. This is useful for queries that filter on one column and sort by another. In our case, we often want to find all bookmarks for a specific user (`user_id`) and sort them by creation date (`created_at`). This index will make that operation much faster.

#### Step 1: Update the Bookmark Table Model

We need to add a special `__table_args__` attribute to our `Bookmark` class. You'll also need to import `Index` from `sqlalchemy`.

Edit `app/models/bookmark.py`:

```python
# app/models/bookmark.py
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
# Import Index from sqlalchemy
from sqlalchemy import Index
from sqlmodel import Field, SQLModel, Relationship

# ... other code

class Bookmark(BookmarkBase, table=True):
    """Database model for bookmarks"""

    __tablename__ = "bookmarks"

    # Add __table_args__ to define the composite index
    __table_args__ = (
        Index("ix_bookmarks_user_id_created_at", "user_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    # ... rest of the class
```

**Dissecting the Change** 🧐
`__table_args__` is a special class attribute that SQLModel passes directly to SQLAlchemy. It's used for defining table-level configurations that aren't tied to a single column. Here, we create an `Index` object, give it a unique name (`ix_bookmarks_user_id_created_at`), and specify the columns it should span: `"user_id"` and `"created_at"`.

#### Step 2: Create a Database Migration

Just like before, this schema change requires a migration.

Run the following commands in your terminal:

```bash
# 1. Autogenerate the new migration
alembic revision --autogenerate -m "Add composite index to bookmarks"

# 2. Apply the migration
alembic upgrade head
```

Alembic will detect the new `__table_args__` and create a migration script to add the composite index to your database.

### Solution 3: Add Validation for URLs

We can use Pydantic's built-in validation system to ensure that users can only submit valid-looking URLs. This is application-level validation and does not require a database migration.

#### Step 1: Add a Validator to the Bookmark Model

We'll add a validator function to the `BookmarkBase` model. This function will automatically run whenever a model that inherits from it (like `BookmarkCreate`) is created with user data.

Edit `app/models/bookmark.py`:

```python
# app/models/bookmark.py

# ... other imports
# Import field_validator from pydantic
from pydantic import field_validator

class BookmarkBase(SQLModel):
    """Shared properties for Bookmark models"""
    url: str = Field(index=True, max_length=2048)
    title: str = Field(max_length=200)
    # ... other fields

    # Add a validator for the 'url' field
    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

# ... rest of the file
```

**Dissecting the Change** 🧐
The `@field_validator("url")` decorator tells SQLModel to run this function whenever the `url` field is set.

  - **Why `BookmarkBase` and not `Bookmark`?** We place the validator on the base class so the logic is **inherited**. This means the URL format will be checked automatically when a user *creates* a bookmark (using `BookmarkCreate`) and when they *update* one (using `BookmarkUpdate`), ensuring data consistency at all API entry points without repeating code.
  - The function receives the value of the URL as its argument `v`.
  - We check if the string `v` starts with either `http://` or `https://`.
  - If it doesn't, we raise a `ValueError` with a helpful message. FastAPI will automatically catch this error and return a descriptive `422 Unprocessable Entity` response to the user.
  - If the validation passes, we must **return the value** so it can be assigned to the model.

Since this is a change to our application's data validation logic, not its database schema, **no migration is needed**.

### Step 4: Testing the New Functionality

Whenever you add new features or change existing ones, you should add or update your automated tests. This verifies your new code works and prevents future changes from accidentally breaking it.

Edit, `app/tests/test_exercises.py`:

```python
import pytest # Add this line
from pydantic import ValidationError # Add this line
from sqlmodel import Session
from app.models import User, Bookmark, Tag, BookmarkTag, BookmarkCreate # Add BookmarkCreate to this line

# ... other tests

def test_views_count_default(session: Session):
    """Test that a new bookmark has a default views_count of 0."""
    user = User(username="testuser", email="test@example.com", hashed_password="hash")
    session.add(user)
    session.commit()
    session.refresh(user)

    bookmark = Bookmark(url="https://example.com", title="Test", user_id=user.id)
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    assert bookmark.views_count == 0

def test_url_validator_success():
    """Test that a valid URL passes Pydantic validation."""
    # This doesn't need the database, it just tests the schema
    data = {"url": "https://goodurl.com", "title": "Good"}
    bookmark = BookmarkCreate(**data)
    assert bookmark.url == "https://goodurl.com"

def test_url_validator_failure():
    """Test that an invalid URL correctly raises a validation error."""
    with pytest.raises(ValidationError) as excinfo:
        BookmarkCreate(url="ftp://badurl.com", title="Bad")
    
    # Check that the error message is what we expect
    assert "URL must start with http:// or https://" in str(excinfo.value)
```

#### Dissecting the New Tests 🧐

  - **`test_views_count_default`**: This is a simple integration test that verifies our database default value for `views_count` is working correctly.
  - **`test_url_validator_...`**: These are unit tests for our Pydantic schema. They don't even need a database connection because they are only testing the validation logic on the model itself.
  - **`pytest.raises`**: This is a special context manager from `pytest` used to test for expected errors. The test will only pass if the code inside the `with` block raises the specified exception (`ValidationError`). This is how you test that your validation is correctly rejecting bad data.

#### Run Your New Tests

From your project's root directory, run `pytest`:

```bash
pytest app/tests/test_models.py -v
```

### Step 5: Commit Your Solutions

Now that you've completed and tested the solutions for the exercises, save your progress to Git.

```bash
# Add all new and modified files to Git
git add .

# Create a commit with a descriptive message
git commit -m "feat: Enhance models with views_count, index, and url validation"

# Push your changes to your GitHub repository
git push origin main
```

