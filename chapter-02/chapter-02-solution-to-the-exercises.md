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

-----

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

-----

### Solution 3: Add Validation for URLs

We can use Pydantic's built-in validation system to ensure that users can only submit valid-looking URLs. This is application-level validation and does not require a database migration.

#### Step 1: Add a Validator to the Bookmark Model

We'll add a validator function to the `BookmarkBase` model. This function will automatically run whenever a model that inherits from it (like `BookmarkCreate`) is created with user data.

Edit `app/models/bookmark.py`:

```python
# app/models/bookmark.py

# ... other imports
# Import validator from pydantic
from pydantic import validator

class BookmarkBase(SQLModel):
    """Shared properties for Bookmark models"""
    url: str = Field(index=True, max_length=2048)
    title: str = Field(max_length=200)
    # ... other fields

    # Add a validator for the 'url' field
    @validator("url")
    def validate_url_format(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

# ... rest of the file
```

**Dissecting the Change** 🧐
The `@validator("url")` decorator from Pydantic tells SQLModel that the `validate_url_format` function should be used to validate the `url` field.

  - The function receives the value of the URL as its argument `v`.
  - We check if the string `v` starts with either `http://` or `https://`.
  - If it doesn't, we raise a `ValueError` with a helpful message. FastAPI will automatically catch this error and return a descriptive `422 Unprocessable Entity` response to the user.
  - If the validation passes, we must **return the value** so it can be assigned to the model.

Since this is a change to our application's data validation logic, not its database schema, **no migration is needed**.