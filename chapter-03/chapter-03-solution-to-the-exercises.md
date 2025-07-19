## Exercise Solutions

These solutions demonstrate how to extend the API with common, practical features like sorting, bulk operations, and data exporting.

### Solution 1: Add Sorting to Bookmarks

This exercise involves adding query parameters to allow clients to sort the list of bookmarks by different fields and in different orders.

#### Step 1: Define Sorting Options with an Enum

Using an `Enum` is the best practice for defining a fixed set of choices. It provides automatic validation and clear documentation.

Add this `Enum` to the top of your `app/api/routes/bookmarks.py` file:

```python
# app/api/routes/bookmarks.py
from enum import Enum
# ... other imports

class BookmarkSortField(str, Enum):
    """Fields to sort bookmarks by."""
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    TITLE = "title"
    IS_FAVORITE = "is_favorite"

# ... router = APIRouter()
```

#### Step 2: Update the `read_bookmarks` Endpoint

Modify the `read_bookmarks` function to accept two new query parameters: `sort_by` and `sort_order`. Then, apply the sorting to the database query.

```python
# In app/api/routes/bookmarks.py

@router.get("/", response_model=List[BookmarkRead])
def read_bookmarks(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search in title and description"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    is_favorite: Optional[bool] = Query(None, description="Filter favorites only"),
    # Add new sorting parameters
    sort_by: BookmarkSortField = Query(BookmarkSortField.CREATED_AT, description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)", pattern="^(asc|desc)$")
):
    """Get user's bookmarks with optional filtering and sorting"""
    # ... (Base query and filters remain the same)
    query = select(Bookmark).where(Bookmark.user_id == current_user.id)
    # ... (if search:, if is_favorite:, if tag: blocks remain the same)

    # Add sorting logic
    sort_column = getattr(Bookmark, sort_by.value)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Execute query
    bookmarks = db.exec(
        query
        .offset(skip)
        .limit(limit)
    ).all()
    
    # ... (response formatting remains the same)
    result = []
    for bookmark in bookmarks:
        bookmark_dict = bookmark.model_dump()
        bookmark_dict["tags"] = [tag.name for tag in bookmark.tags]
        result.append(BookmarkRead(**bookmark_dict))
    
    return result
```

#### Dissecting the Solution 🧐

  - **`Enum` for Validation**: `BookmarkSortField` ensures that users can only provide valid field names for sorting. FastAPI uses this to generate a dropdown list in the interactive docs.
  - **Dynamic `order_by`**: We use `getattr(Bookmark, sort_by.value)` to dynamically get the correct column object from our `Bookmark` model based on the user's input. This avoids a large `if/elif/else` block and makes the code cleaner.
  - **Sort Order**: We apply `.desc()` or `.asc()` based on the `sort_order` parameter to control the direction of the sort.

**To Test**: Go to your docs at `http://localhost:8000/docs`, expand the `GET /bookmarks/` endpoint, and try out the new `sort_by` and `sort_order` fields.


### Solution 2: Bulk Delete Bookmarks

This exercise requires a new endpoint that can accept a list of bookmark IDs and delete them all in a single operation.

#### Step 1: Create a Request Body Model

We need a Pydantic model to define the shape of our request body.

Add this class to `app/models/bookmark.py`:

```python
# In app/models/bookmark.py

class BookmarkBulkDelete(SQLModel):
    """Schema for bulk deleting bookmarks."""
    bookmark_ids: List[int]
```

Don't forget to import it in `app/api/routes/bookmarks.py` and `app/models/__init__.py`.

#### Step 2: Create the Bulk Delete Endpoint

Add this new endpoint to `app/api/routes/bookmarks.py`. A `POST` request to a specific path like `/bulk-delete` is a common pattern for this type of operation.

```python
# In app/api/routes/bookmarks.py
# ... other imports from app.models
from app.models import BookmarkBulkDelete

# ... after the last endpoint function

@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
def bulk_delete_bookmarks(
    delete_in: BookmarkBulkDelete,
    db: SessionDep,
    current_user: CurrentUser
):
    """Delete multiple bookmarks at once."""
    # Query for all bookmarks that match the provided IDs AND belong to the current user
    bookmarks_to_delete = db.exec(
        select(Bookmark).where(
            Bookmark.id.in_(delete_in.bookmark_ids),
            Bookmark.user_id == current_user.id
        )
    ).all()

    if not bookmarks_to_delete:
        # You can choose to raise an error or just do nothing
        return

    for bookmark in bookmarks_to_delete:
        db.delete(bookmark)
    
    db.commit()
```

#### Dissecting the Solution 🧐

  - **Request Body Schema**: The `BookmarkBulkDelete` model ensures we receive a valid JSON object with a list of integer IDs.
  - **Security Check**: The query `select(Bookmark).where(Bookmark.id.in_(...), Bookmark.user_id == ...)` is critical. It fetches only the bookmarks that are both in the requested list **and** owned by the current user. This prevents a user from deleting another user's bookmarks.
  - **Efficient Deletion**: We fetch all valid bookmarks to be deleted in one query. Then we loop through them and call `db.delete()`. `db.commit()` finalizes the transaction, deleting all of them at once.
  - **`204 No Content`**: This is the appropriate HTTP status code for a successful `DELETE` operation that doesn't return any content.

**To Test**: Use the interactive docs to call the new `POST /bookmarks/bulk-delete` endpoint. Provide a JSON body like: `{ "bookmark_ids": [1, 2] }`.

### Solution 3: Export Bookmarks as CSV

This exercise involves creating an endpoint that returns all of a user's bookmarks as a downloadable CSV file.

#### Step 1: Create the Export Endpoint

This endpoint will query the data and use Python's built-in `csv` module to generate the file content. We'll use FastAPI's `StreamingResponse` to send the file to the client.

Add this new endpoint to `app/api/routes/bookmarks.py`:

```python
# In app/api/routes/bookmarks.py
# Add these imports to the top
import csv
import io
from fastapi.responses import StreamingResponse

# ... after the last endpoint function

@router.get("/export/csv", response_class=StreamingResponse)
def export_bookmarks_csv(
    db: SessionDep,
    current_user: CurrentUser
):
    """Export the user's bookmarks to a CSV file."""
    # Fetch all bookmarks for the user
    bookmarks = db.exec(
        select(Bookmark).where(Bookmark.user_id == current_user.id)
    ).all()

    # Use an in-memory text buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header row
    header = ["id", "url", "title", "description", "is_favorite", "created_at", "tags"]
    writer.writerow(header)

    # Write data rows
    for bookmark in bookmarks:
        # Join tags into a single string
        tag_str = ", ".join([tag.name for tag in bookmark.tags])
        row = [
            bookmark.id,
            bookmark.url,
            bookmark.title,
            bookmark.description,
            bookmark.is_favorite,
            bookmark.created_at.isoformat(),
            tag_str
        ]
        writer.writerow(row)

    # The browser needs these headers to trigger a download
    headers = {
        "Content-Disposition": "attachment; filename=bookmarks_export.csv",
        "Content-Type": "text/csv",
    }
    
    # Move the buffer's cursor to the beginning
    output.seek(0)
    
    return StreamingResponse(output, headers=headers)
```

#### Dissecting the Solution 🧐

  - **`StreamingResponse`**: This special response class from FastAPI is designed to stream a file or any other iterator as the response body.
  - **`io.StringIO`**: This creates an in-memory text file. We use the `csv` module to write to this buffer just like we would write to a real file on disk.
  - **Headers for Download**:
      - `Content-Type: text/csv` tells the browser what kind of file it is.
      - `Content-Disposition: attachment; filename=...` is the crucial part that tells the browser to open a "Save As..." dialog to download the file, rather than trying to display it on the page.

**To Test**: Authenticate in your docs, then simply navigate to **http://localhost:8000/api/v1/bookmarks/export/csv** in your browser. It should trigger a file download.


### Step 4: Automated Tests for New Features

Whenever you add new features, you must also add new tests. This verifies that your logic is correct and protects against future changes accidentally breaking your work (regressions).

Edit, `app/tests/conftest.py`:

```python

# Add to the END

@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user: User) -> dict:
    """
    Returns a simple, non-validated Authorization header.
    This works with the Chapter 3 placeholder dependency.
    """
    # The 'test_user' fixture is included to ensure the user exists in the DB,
    # as the placeholder dependency will try to fetch it.
    return {"Authorization": "Bearer test"}
```

Edit, `app/tests/test_bookmark_exercises.py`:

```python
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User, Bookmark, Tag # Add Tag

# Add to the END

def test_read_bookmarks_sorting(client: TestClient, session: Session, test_user: User, auth_headers: dict):
    """Test sorting bookmarks by title in ascending order."""
    # Arrange: Create bookmarks in a non-alphabetical order
    b1 = Bookmark(url="https://site-b.com", title="B Bookmark", user_id=test_user.id)
    b2 = Bookmark(url="https://site-a.com", title="A Bookmark", user_id=test_user.id)
    session.add_all([b1, b2])
    session.commit()

    # Act: Request bookmarks sorted by title, ascending
    response = client.get(
        "/api/v1/bookmarks/?sort_by=title&sort_order=asc",
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "A Bookmark"
    assert data[1]["title"] == "B Bookmark"

def test_bulk_delete_bookmarks(client: TestClient, session: Session, test_user: User, auth_headers: dict):
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
        json={"bookmark_ids": [b1_todelete.id, b3_otheruser.id]}
    )

    # Assert
    assert response.status_code == 204
    assert session.get(Bookmark, b1_todelete.id) is None
    assert session.get(Bookmark, b2_tokeep.id) is not None
    assert session.get(Bookmark, b3_otheruser.id) is not None

def test_export_bookmarks_csv(client: TestClient, session: Session, test_user: User, auth_headers: dict):
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
    assert "attachment; filename=bookmarks_export.csv" in response.headers["content-disposition"]
    
    # Check the content of the CSV
    content = response.text
    assert "id,url,title,description,is_favorite,created_at,tags" in content
    assert "CSV Test" in content
    assert "csv" in content
```

Run your new tests:

```bash
pytest app/tests/test_bookmark_exercises.py -v
```

#### Dissecting the New Tests 🧐

  - **`test_read_bookmarks_sorting`**: This test specifically verifies our new sorting feature works as expected by creating data in one order and asserting that the API returns it in a different, correct order.
  - **`test_bulk_delete_bookmarks`**: This test is crucial as it verifies both functionality and security. It confirms that the endpoint deletes the requested bookmarks *but also* that it correctly ignores IDs for bookmarks that don't belong to the authenticated user.
  - **`test_export_bookmarks_csv`**: This test shows how to handle non-JSON responses. Instead of checking `response.json()`, we inspect the response **headers** and the raw text content (`response.text`) to ensure the CSV file is generated correctly.


### Step 5: Commit Your Solutions

You've successfully implemented and tested several new features for your API. It's time to save your progress to Git.

```bash
# Add all new and modified files
git add .

# Commit the changes with a descriptive message
git commit -m "feat(bookmarks): Add sorting, bulk delete, and CSV export"

# Push your changes to your GitHub repository
git push origin main
```