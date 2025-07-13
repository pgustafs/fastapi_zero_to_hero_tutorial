## Exercise Solution

The exercise was to add a new endpoint, `/api/v1/status`, that returns the current time and a masked version of the database URL. This solution follows the modular `APIRouter` pattern we established in the chapter.

### Step 1: Create the Response Schema

First, let's define the shape of our response data. Since this is a Pydantic model used for API validation and serialization (a "schema"), we'll place it in the `app/schemas/` directory.

Create a new file `app/schemas/status.py`:

```python
from datetime import datetime
from pydantic import BaseModel, Field

# Define a Pydantic model for the response structure
class StatusResponse(BaseModel):
    current_time: datetime = Field(..., json_schema_extra={"example": "2025-07-13T12:00:00.000000Z"})
    database_url: str = Field(..., json_schema_extra={"example": "sqlite:///./b********.db"})
```

### Step 2: Create the Status Endpoint

Now, let's create the endpoint itself. It will import the `StatusResponse` schema we just defined.

Create a new file, `app/api/routes/status.py`:

```python
import re
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings
# Import the response schema
from app.schemas.status import StatusResponse

# Create an API router
router = APIRouter()

def mask_db_url(url: str) -> str:
    """Masks credentials and sensitive parts of a database URL."""
    if not isinstance(url, str):
        return "Invalid URL format"
    if url.startswith("sqlite"):
        return re.sub(r'(\w+)\.db', '********.db', url)
    return re.sub(r'://(.*?):(.*?)@', r'://********:********@', url)


@router.get("/status", response_model=StatusResponse)
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

*Note: The path is `/status`, as the `/api/v1` prefix will be added later.*

-----

### Step 3: Include the New Router in the Main App

Now we need to tell the main FastAPI application to use our new `status` router.

Update `app/main.py` to import and include the `status` router:

```python
# app/main.py

# ... other imports
# Import the status router as well
from app.api.routes import health, status

# ... app = FastAPI(...)

# Include the routers
app.include_router(health.router)
# Add the new status router
app.include_router(status.router, prefix=settings.API_V1_STR)

# ... @app.get("/") ...
```

*Notice we add the `/api/v1` prefix here, so the final URL will be `/api/v1/status`.*

### Step 4: Test the New Endpoint

Restart your development server (`Ctrl+C` and then `fastapi dev app/main.py`).

You can test the endpoint in two primary ways:

#### Using a Browser

Visit the new endpoint in your browser: **http://localhost:8000/api/v1/status**

#### Using `curl`

Alternatively, you can test it directly from your command line:

```bash
curl -X GET "http://localhost:8000/api/v1/status"
```

#### Expected Response

No matter which method you use, you should see a response similar to this, with a pretty-printed version appearing in your browser:

```json
{
  "current_time": "2025-07-13T12:04:26.123456Z",
  "database_url": "sqlite:///./********.db"
}
```

### Step 5: Commit Your Work

You've successfully added a new feature\! It's time to save your progress to Git.

```bash
# Add all new and modified files to the staging area
git add app/

# Commit the changes with a descriptive message
git commit -m "feat: Add /api/v1/status endpoint"

check yaml...........................................(no files to check)Skipped
fix end of files.........................................................Passed
trim trailing whitespace.................................................Failed
- hook id: trailing-whitespace
- exit code: 1
- files were modified by this hook

Fixing app/api/routes/status.py

ruff (legacy alias)......................................................Failed
- hook id: ruff
- exit code: 1
- files were modified by this hook

Found 1 error (1 fixed, 0 remaining).

ruff format..............................................................Failed
- hook id: ruff-format
- files were modified by this hook

2 files reformatted, 1 file left unchanged
```

The errors from `git commit` is a great sign\! It means `pre-commit` is working perfectly. This is not an error, but the tool doing its job to automatically clean up your code.

### Dissecting the Output 🧐

  - **`Failed` and `files were modified by this hook`**: This means `pre-commit` found issues like extra whitespace or incorrect formatting and **fixed them for you** directly in your files.
  - **The commit was stopped**: By design, `pre-commit` stops the commit after making changes so that you can review them.

### What to Do Next: The Two-Step Fix

All you need to do is add the cleaned-up files and commit again.

**1. Stage the Automatic Fixes**
Use `git add` to stage the changes that `pre-commit` just made.

```bash
git add .
```

**2. Commit Again**
Run the exact same commit command again.

```bash
git commit -m "feat: Add /api/v1/status endpoint"
```

This time, `pre-commit` will run, see that the files are already clean, and allow the commit to succeed instantly.

You can now run `git push origin main` to upload your changes to GitHub, which will trigger your CI pipeline.

### Dissecting the Solution 🧐

  - **Schema Separation**: By creating `app/schemas/status.py`, you are following a clean architecture. This separates your data contracts (schemas) from your endpoint logic (routes), making the application easier to maintain.
  - **Response Model**: By setting `response_model=StatusResponse` in the decorator, FastAPI automatically validates your output, serializes the `datetime` object, and provides precise documentation for your API.
  - **Timezone-Aware Time**: We used `datetime.now(timezone.utc)` to get the current time. Using timezone-aware datetimes (especially UTC) is a crucial best practice.
  - **Security by Masking**: The `mask_db_url` function prevents leaking sensitive information like database credentials or file paths.
  - **Modular Routers**: Creating a new `status.py` file and including its router in `main.py` continues our scalable design.