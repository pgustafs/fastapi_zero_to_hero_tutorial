# Chapter 6: Smart Bookmarks with AI Enhancement

## What are Smart Bookmarks?

Smart bookmarks automatically enrich your saved links with AI-generated summaries and tags. When you save a URL, the system can extract the content from the URL, generate a meaningful description, and suggest relevant tags, all in the background without slowing down your workflow.

## Why Smart Features Matter

1.  **Time-Saving**: No need to manually write descriptions or think of tags.
2.  **Better Organization**: Consistent, relevant tags improve searchability.
3.  **Async Processing**: Users get instant feedback while AI works in the background.

## Let's Build: AI-Enhanced Bookmarks

### Step 1: Install New Dependencies

We need several new libraries for background tasks, web scraping, and AI integration.

Update your `requirements.txt` file with these additions:

```txt
# ... (existing dependencies)

# AI Enhancement
beautifulsoup4>=4.13.4
docling>=2.42.2
openai>=1.97.1

# Background task processing
celery>=5.5.3
#redis>=6.2.0
```

Install the new packages:

```bash
pip install -r requirements.txt
```

#### Dissecting the Dependencies 🧐

  - **`beautifulsoup4`**: A powerful library for pulling data out of HTML (web scraping).
  - **`docling`**: A utility to convert HTML into cleaner formats like Markdown.
  - **`openai`**: The official Python client for interacting with OpenAI-compatible APIs, including many local LLMs.
  - **`celery`**: The industry-standard distributed task queue for Python. It will run our AI processing in the background.
  - **`redis`**: Celery requires a "broker" to pass messages between our API and its workers. Redis is a fast, popular, and easy-to-run choice.

### Step 2: Update the Bookmark Model

We need to add new fields to our `Bookmark` model to enable and track the status of AI processing.

**Update `app/models/bookmark.py`:**

```python
# ...
from sqlmodel import Field, SQLModel, Relationship, Column, Enum as SQLModelEnum # Add; Column, Enum as SQLModelEnum
from enum import Enum # Add

class ProcessingStatus(str, Enum):
    """Status of AI content processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped" # Default for non-AI bookmarks

class BookmarkBase(SQLModel):
    # ... (url, title, fields)
    description: Optional[str] = Field(default=None, max_length=2000) # Change max_lenght to 2000
    is_favorite: bool = Field(default=False)
    views_count: int = Field(default=0)
    ai_enabled: bool = Field(default=False, description="Enable AI content generation") # Add
    # ...

class Bookmark(BookmarkBase, table=True):
    # ... (id, user_id, created_at, updated_at)
    ai_status: ProcessingStatus = Field(
        default=ProcessingStatus.SKIPPED,
        sa_column=Column(SQLModelEnum(ProcessingStatus))
    )
    ai_error: Optional[str] = Field(default=None, max_length=500)
    # ... (relationships)

class BookmarkCreate(BookmarkBase):
    tags: Optional[List[str]] = Field(default=[])
    # Make AI enhancement on by default for new bookmarks
    ai_enabled: bool = Field(default=True) # Add

class BookmarkRead(BookmarkBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []
    ai_status: ProcessingStatus # Add
    # ... (other fields)

class BookmarkUpdate(SQLModel):
    """Schema for updating bookmark data"""

    # ...
    description: Optional[str] = Field(None, max_length=2000) # Change max_length to 2000
    # ...
```

#### update `app/models/__init__.py`
```python
# ...

from .bookmark import (
    Bookmark,
    BookmarkCreate,
    BookmarkRead,
    BookmarkUpdate,
    BookmarkBulkDelete,
    ProcessingStatus, # Add
)

# ...
__all__ = [
    "User",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "Bookmark",
    "BookmarkCreate",
    "BookmarkRead",
    "BookmarkUpdate",
    "Tag",
    "TagRead",
    "BookmarkTag",
    "BookmarkBulkDelete",
    "ProcessingStatus", # Add
]

```

#### Dissecting the Model Changes 🧐

-   **`ProcessingStatus`**: Using an `Enum` provides a set of fixed, readable statuses for our AI tasks. This makes the code easier to understand and prevents bugs from typos.
-   **`ai_enabled`**: This boolean flag allows the user (or client application) to decide on a per-bookmark basis whether to trigger the AI enhancement feature.
-   **State Tracking Fields**: The `ai_status` and `ai_error` fields are crucial for observability. They are added directly to the database table so the API can provide real-time feedback to the user about the state of their background job.
-   **Explicit Column Type**: The line `sa_column=Column(SQLModelEnum(ProcessingStatus))` is an important detail. It explicitly tells SQLAlchemy to use its `Enum` type, ensuring that string values from the database are correctly converted back into Python `Enum` members.

### Step 3: Create a Database Migration

Since we've changed our `Bookmark` table model, we need to apply this change to our database schema using Alembic.

Run these commands from your project root:

```bash
# Autogenerate a migration script based on our model changes
alembic revision --autogenerate -m "Add AI fields to Bookmark model"

# Apply the migration to the database
alembic upgrade head
```

#### Dissecting the Migration 🧐

-   **Schema vs. Data**: A migration changes the *structure* (schema) of your database, not the data itself.
-   **`autogenerate`**: Alembic's `autogenerate` command is a powerful tool that compares your SQLModel classes to the live database. It detected the new columns (`ai_enabled`, `ai_status`, etc.) and automatically wrote the Python code needed to add them.
-   **Safety**: Running `alembic upgrade head` executes this script. It uses `ALTER TABLE` commands to safely add the new columns to your existing `bookmarks` table without deleting any of your current data.

### Step 4: Configure Celery and App Settings

We need to tell our application where to find Redis and configure our AI settings.

**1. Update `app/core/config.py`**

```python
class Settings(BaseSettings):
    # ... (existing settings)

    # Add Redis and AI Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    AI_ENABLED: bool = True
    AI_API_BASE_URL: str = "http://localhost:8080/v1" #Default for vllm
    AI_API_KEY: Optional[str] = "secret_key"
    AI_MODEL: str = "qwen3"
```

**2. Add the new settings to your `.env` and `.env.example` files.**

**3. Create `app/core/celery_app.py`**

```python
from celery import Celery
from celery.signals import setup_logging
from logging.config import dictConfig
from app.core.logging_config import LOGGING_CONFIG
from app.core.config import settings

# This function will be called when the Celery worker starts
@setup_logging.connect
def configure_logging(**kwargs):
    """
    Apply the application's logging configuration to the Celery worker.
    """
    dictConfig(LOGGING_CONFIG)

celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.ai_tasks"] # Points to our tasks file
)
```

#### Dissecting the Configuration 🧐

-   **Centralized Settings**: We've added all AI and Redis configuration to our central `Settings` class in `config.py`. This is a best practice that allows us to easily manage and change these values for different environments (development, production) using the `.env` file.
-   **Celery Instance**: The `celery_app` is the entry point for our background processing system. We configure it with the `broker` (Redis), which is the message bus for sending tasks, and the `backend` (also Redis), which is used to store task results.
-   **Task Discovery**: The `include=["app.tasks.ai_tasks"]` line tells Celery which modules to scan to find functions decorated with `@celery_app.task`.
-   **Logging Integration**: The `@setup_logging.connect` decorator is a **Celery signal**. It's a crucial hook that ensures our custom logging configuration from `logging_config.py` is applied to the Celery worker process when it starts. This guarantees consistent, structured logging for both our main API and our background workers.

### Step 5: Create the AI Content Service

This service will contain the core logic from your prototype for scraping web content and calling the AI model.

Create `app/services/content_processor.py`:

```python
import logging
import re
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from docling.datamodel.document import InputDocument, InputFormat
from docling.backend.html_backend import HTMLDocumentBackend
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class ContentProcessor:
    """A service to extract, clean, and analyze web content using AI."""

    def __init__(self):
        self.ai_client = OpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_API_BASE_URL
        )

    def extract_clean_content(self, url: str) -> BeautifulSoup:
        """Extracts clean HTML content from a URL."""
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            boilerplate_re = re.compile(r'.*(footer|header|navigation|nav|sidebar|menu).*', re.I)
            static_tags = ['script', 'style', 'noscript', 'iframe', 'aside']
            
            tags_to_remove = soup.find_all(name=boilerplate_re) + soup.find_all(static_tags)
            for tag in tags_to_remove:
                tag.decompose()
            
            #return soup.encode('utf-8')
            return soup
        except requests.RequestException as e:
            raise Exception(f"Error fetching {url}: {e}") from e

    @staticmethod    
    def extract_title(soup: BeautifulSoup) -> str:
        """Extract the page title from <title> or <h1>. Return fallback if none found."""
        try:
            # Try <title> tag
            if soup.title and soup.title.string:
                return soup.title.string.strip()
            
            # Try first <h1> tag
            h1 = soup.find('h1')
            if h1 and h1.text:
                return h1.text.strip()
            
        except Exception as e:
            # Optional: log or print the error if needed
            pass

        # Fallback title
        return "title not found"

    def html_to_markdown(self, clean_html: bytes) -> str:
        """Converts clean HTML bytes to markdown."""
        try:
            clean_html_utf8 = clean_html.encode('utf-8')
            html_stream = BytesIO(clean_html_utf8)

            in_doc = InputDocument(
                path_or_stream=BytesIO(clean_html_utf8),
                format=InputFormat.HTML,
                backend=HTMLDocumentBackend,
                filename="content.html",
            )
            backend = HTMLDocumentBackend(in_doc=in_doc, path_or_stream=html_stream)
            doc = backend.convert()
            markdown = doc.export_to_markdown()
            return re.sub(r'\n{3,}', '\n\n', markdown).strip()
        except Exception as e:
            raise Exception(f"Error converting HTML to markdown: {e}") from e

    def _call_ai_model(self, system_prompt: str, user_content: str) -> str:
        """Helper function to make calls to an OpenAI-compatible API."""
        try:
            response = self.ai_client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=4096,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error calling AI model: {e}")
            raise Exception(f"AI API call failed: {e}") from e

    def generate_summary(self, markdown_content: str) -> str:
        """Generates a summary from markdown content."""
       #SYSTEM_PROMPT = """
        #You are an intelligent web content analyst for a bookmarking service. Create a concise summary (under 80 words) that captures the essence of the content. Focus on the main topic, key points, and purpose. Do not use introductory phrases like 'This article...'.
        #"""
        SYSTEM_PROMPT = """
        You are an intelligent web content analyst for a sophisticated bookmarking service. Your primary function is to create a dense 'highlight' summary from the text of a webpage. This highlight serves as a quick, informative preview for the user's saved bookmarks.

        When creating the highlight, focus on extracting:
        1.  **The core subject and main topic.**
        2.  **Key entities mentioned (e.g., people, companies, products, technologies).**
        3.  **The main takeaway, conclusion, or purpose of the content (e.g., is it a news report, a how-to guide, an opinion piece, a product review?).**

        The final output must be a single, well-written paragraph. It must be extremely concise to fit within a 512-token limit for a downstream embedding model. For this reason, keep the summary under 400 words. Do not use introductory phrases like 'This article is about...' or 'The content discusses...'. Jump directly into the highlight.
        """
        user_content = "Please generate a highlight summary for the following content:\n\n" + markdown_content[:10000]
        return self._call_ai_model(SYSTEM_PROMPT, user_content)

    def generate_tags(self, markdown_content: str) -> list[str]:
        """Generates a list of tags from markdown content."""
        SYSTEM_PROMPT = """
        You are an expert content categorization engine for a bookmarking application. Your sole purpose is to analyze the provided text and generate exactly 5 relevant tags to help users organize and find their bookmarks.

        Instructions:
        1.  **Analyze the content** to identify the primary subjects, technologies, themes, and key entities.
        2.  **Generate exactly 6 tags.** No more, no less.
        3.  **Tags must be concise**, ideally 1-3 words.
        4.  **Format all tags in lowercase** and replace spaces with a hyphen (kebab-case).
        5.  **Provide the output as a single line of comma-separated values.** Do not add a numbered list, bullet points, or any introductory text like "Here are the tags:".

        Example output:
        web-development,react-js,front-end,state-management,tutorial,python
        """
        user_content = "Generate 6 tags for the following content:\n\n" + markdown_content[:10000]
        
        tags_str = self._call_ai_model(SYSTEM_PROMPT, user_content)
        # Clean up the AI's output
        return [tag.strip() for tag in tags_str.split(',') if tag.strip()]

# Create a single, reusable instance for the application
content_processor = ContentProcessor()
```

#### Dissecting the AI Content Service 🧐
-   **Separation of Concerns**: This `ContentProcessor` class is a dedicated service whose only job is to handle the complex logic of scraping web content and interacting with the AI. This keeps our Celery task simple and focused on orchestration.
-   **Web Scraping**: The `extract_clean_content` method uses `requests` to fetch the webpage and `BeautifulSoup` to parse the HTML and strip out common boilerplate (like headers, footers, and scripts), leaving only the core text for analysis.
-   **Prompt Engineering**: The `generate_summary` and `generate_tags` methods contain detailed **system prompts**. These prompts instruct the AI model on its role, the desired output, and the rules it must follow. Good prompt engineering is the key to getting reliable and consistently formatted results from language models.
-   **Configuration-Driven**: The entire service is configured via the `settings` object. This allows you to easily switch between a local model (like with Ollama) and a cloud-based one (like OpenAI) just by changing your `.env` file.

### Step 6: Create the Celery Background Task

This task will orchestrate the AI processing, handle state changes, and implement fault tolerance.

Create `app/tasks/ai_tasks.py` (and an empty `app/tasks/__init__.py`):

```python
import logging
from sqlmodel import Session, select
from app.core.celery_app import celery_app
from app.core.database import engine
from app.models import Bookmark, ProcessingStatus, Tag
from app.services.content_processor import content_processor

logger = logging.getLogger(__name__)

@celery_app.task
def process_bookmark_content(bookmark_id: int, user_id: int, request_id: str | None = None):
    """AI task to process a bookmark's content."""
    # Create a rich log context with all available info
    log_context = {
        "event": "AI_PROCESSING",
        "bookmark_id": bookmark_id,
        "user_id": user_id,
        "request_id": request_id,
    }
    logger.info("Starting AI processing", extra={"extra_info": log_context})
    with Session(engine) as session:
        bookmark = session.get(Bookmark, bookmark_id)
        if not bookmark or not bookmark.ai_enabled:
            logger.warning(f"Skipping AI processing for bookmark_id: {bookmark_id}")
            return

        bookmark.ai_status = ProcessingStatus.PROCESSING
        session.add(bookmark)
        session.commit()

        try:
            clean_html = content_processor.extract_clean_content(bookmark.url)
            title = content_processor.extract_title(clean_html)
            markdown = content_processor.html_to_markdown(clean_html)
            summary = content_processor.generate_summary(markdown)
            tag_names = content_processor.generate_tags(markdown)

            bookmark.title = title
            bookmark.description = summary
            bookmark.tags.clear()
            for name in tag_names:
                tag = session.exec(select(Tag).where(Tag.name == name)).first()
                if not tag:
                    tag = Tag(name=name)
                bookmark.tags.append(tag)
            
            bookmark.ai_status = ProcessingStatus.COMPLETED
            bookmark.ai_error = None
            # Add structured success log with full context
            log_context["status"] = "SUCCESS"
            log_context["summary_length"] = len(summary)
            log_context["tags_generated"] = tag_names
            logger.info("Successfully processed bookmark", extra={"extra_info": log_context})
        
        except Exception as e:
            # Fault Tolerance: Handle AI failures gracefully
            bookmark.ai_status = ProcessingStatus.FAILED
            bookmark.ai_error = str(e)[:499]
            bookmark.description = "AI processing failed. Could not generate summary."
            # Add structured failure log with full context
            log_context["status"] = "FAILURE"
            log_context["error"] = str(e)
            logger.error("Failed to process bookmark", exc_info=True, extra={"extra_info": log_context})
        
        session.add(bookmark)
        session.commit()
```

#### Dissecting the Task 🧐

  - **Orchestration**: The Celery task doesn't contain the complex AI logic itself; it calls the `ContentProcessor` service. This is a great design pattern called **Separation of Concerns**.
  - **State Management**: The task is responsible for updating the `ai_status` in the database, providing real-time feedback on its progress.
  - **Fault Tolerance**: The `try...except` block is critical. If any part of the process fails (e.g., the website is down, the AI API is unresponsive), it catches the error, marks the bookmark as `FAILED`, saves the error message, and provides a helpful fallback description. The API request for the user never fails.

### Step 7: Update API to Dispatch Tasks

Modify the `create_bookmark` endpoint to save the bookmark and dispatch the task to Celery.

**Update `app/api/routes/bookmarks.py`:**

```python
from fastapi import APIRouter, HTTPException, status, Query, Request # Add Request
from app.models import (
    Bookmark,
    BookmarkCreate,
    BookmarkRead,
    BookmarkUpdate,
    BookmarkBulkDelete,
    Tag,
    BookmarkTag,
    ProcessingStatus, # Add this line
)
from app.tasks.ai_tasks import process_bookmark_content # Add this line
import logging # Add this line

# Add a logger
logger = logging.getLogger(__name__)

# ...

@router.post("/", response_model=BookmarkRead, status_code=status.HTTP_201_CREATED)
def create_bookmark(
    bookmark_in: BookmarkCreate,
    db: SessionDep,
    current_user: CurrentUser,
    request: Request
):
    """Create a new bookmark with optional AI enhancement"""
    # Create the initial bookmark object
    bookmark = Bookmark(
        **bookmark_in.model_dump(exclude={"tags"}),
        user_id=current_user.id,
        ai_status=ProcessingStatus.PENDING if bookmark_in.ai_enabled else ProcessingStatus.SKIPPED
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    # If AI is NOT enabled, use the explicit, manual tag handling logic
    if not bookmark.ai_enabled and bookmark_in.tags:
        for tag_name in set(bookmark_in.tags):
            tag = db.exec(select(Tag).where(Tag.name == tag_name.lower())).first()
            if not tag:
                tag = Tag(name=tag_name.lower())
                db.add(tag)
                db.commit()
                db.refresh(tag)
            
            # Manually create the link table entry
            bookmark_tag = BookmarkTag(bookmark_id=bookmark.id, tag_id=tag.id)
            db.add(bookmark_tag)
        
        db.commit()
        db.refresh(bookmark)

    # Log the creation event
    log_context = {
        "event": "CREATE_BOOKMARK",
        "bookmark_id": bookmark.id,
        "user_id": current_user.id,
        "request_id": getattr(request.state, "request_id", None),
    }
    logger.info("Bookmark created", extra={"extra_info": log_context})
    
    # Queue AI processing if enabled
    if bookmark.ai_enabled:
        try:
            process_bookmark_content.delay(
                bookmark_id=bookmark.id,
                user_id=current_user.id,
                request_id=getattr(request.state, "request_id", None)
            )
        except Exception as e:
            logger.error(f"Failed to queue AI processing for bookmark {bookmark.id}: {e}")
            bookmark.ai_status = ProcessingStatus.FAILED
            bookmark.ai_error = "Failed to queue processing task."
            db.add(bookmark)
            db.commit()
            db.refresh(bookmark)
    
    # Manually construct the response model
    return BookmarkRead(
        **bookmark.model_dump(exclude={"tags", "tags_from_relationship"}), 
        tags=[tag.name for tag in bookmark.tags]
    )
```

#### Dissecting the API Update 🧐
-   **Instant Response**: The endpoint immediately saves the bookmark and returns a `201 Created` response. The heavy AI work, which could take many seconds, no longer blocks the API, providing a much better user experience.
-   **Conditional Logic**: The function now has two paths. If `ai_enabled` is `False`, it runs the familiar manual tag-linking logic. If `ai_enabled` is `True`, it skips this and sets the `ai_status` to `PENDING`.
-   **`.delay()`**: This is the key Celery method. Instead of calling `process_bookmark_content(...)` directly, we call `.delay(...)`. This serializes the task and its arguments and sends it as a message to the Redis broker. A separate Celery worker process will then pick it up and execute it asynchronously.
-   **Passing Context**: Notice we pass `user_id` and `request_id` to the task. This is a critical pattern. The background worker has no concept of the original web request, so we must explicitly pass along any context needed for logging and traceability.

### Step 8: Running Redis and Celery Locally

We'll run these services directly on our machine for this chapter.

**1. Start Redis as a container using podman**

```bash
podman run -d --name my-redis -p 6379:6379 redis:alpine
```

**2. Start the Celery Worker**
Open a **new terminal window**, navigate to your project root, activate your `venv`, and run:

```bash
celery -A app.core.celery_app worker --loglevel=info
```

Keep this terminal open. It is now your background job processor.

#### Dissecting the Local Services 🧐
-   **Decoupled Services**: Our application now consists of three independent services: the FastAPI web server, the Redis message broker, and the Celery worker. They communicate with each other but run in separate processes. This is a common and scalable architecture.
-   **Podman/Docker**: While we run them locally here, using Podman for Redis is a good example of how containers simplify managing services without polluting your local machine with installations.
-   **The Worker's Role**: The Celery worker terminal is your window into the background processing. It will show you when a task is received, when it starts, its log output, and whether it succeeded or failed.

### Step 9: 🧪 Test Your Smart Bookmarks

1.  **Start your API server** in another terminal: `fastapi dev app.main:app`
2.  **Make sure your local LLM is running** (e.g., Ollama).
3.  **Create a smart bookmark with `curl`:**
    1.  **Register a new user**:

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

    2.  **Login to get token**:

    ```bash
    curl -X POST "http://localhost:8000/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{
        "username": "john_doe",
        "password": "securepass123"
    }'

    # Save the access_token from the response!
    ```

    3. **Create a bookmark**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/bookmarks/" \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"url": "https://www.djangoproject.com/", "title": "Django Project"}'
    ```
4.  **Observe the Logs:** You'll get an immediate success from `curl`. In your Celery worker terminal, you'll see it receive and start processing the task. When it's done, you can fetch the bookmark again to see its new AI-generated description and tags.

### Step 10: Automated Testing

We'll test the task logic directly and "mock" the AI calls to keep our tests fast and reliable.

Create `app/tests/test_ai_tasks.py`:

```python
from unittest.mock import MagicMock
from sqlmodel import Session
from app.models import Bookmark, ProcessingStatus, User
from app.tasks.ai_tasks import process_bookmark_content

def test_process_bookmark_content(session: Session, test_user: User, monkeypatch):
    """Test the AI processing task by mocking the AI service."""
    # Arrange: Create a pending bookmark
    bookmark = Bookmark(
        url="https://example.com",
        title="Test",
        user_id=test_user.id,
        ai_enabled=True,
        ai_status=ProcessingStatus.PENDING
    )
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    
    # Mock the content_processor to avoid real network calls
    mock_processor = MagicMock()
    mock_processor.extract_clean_content.return_value = "Clean HTML Content"
    # Add a mock for the extract_title method
    mock_processor.extract_title.return_value = "Mocked Title"
    mock_processor.html_to_markdown.return_value = "Clean markdown"
    mock_processor.generate_summary.return_value = "Mocked AI summary."
    mock_processor.generate_tags.return_value = ["mocked", "ai", "tag"]
    monkeypatch.setattr("app.tasks.ai_tasks.content_processor", mock_processor)
    
    # Monkeypatch the engine for the test database
    test_engine = session.get_bind()
    monkeypatch.setattr("app.tasks.ai_tasks.engine", test_engine)

    # Act: Run the task function directly
    process_bookmark_content(bookmark_id=bookmark.id, user_id=test_user.id)
    
    # Assert: Check the bookmark was updated with mocked data
    session.refresh(bookmark)
    assert bookmark.ai_status == ProcessingStatus.COMPLETED
    assert bookmark.title == "Mocked Title" # Assert the new title
    assert bookmark.description == "Mocked AI summary."
    assert "mocked" in [tag.name for tag in bookmark.tags]
```

#### Dissecting the Test 🧐
Testing a background task that interacts with external services and a database requires a specific strategy. This test demonstrates two key best practices: testing the logic in isolation and mocking external dependencies.

-   **Direct Task Testing**: Instead of using `TestClient` to call an API endpoint, we import the task function (`process_bookmark_content`) and call it directly. This is a form of **unit/integration testing** that is much faster and more focused. It allows us to verify the task's core logic without the overhead of the full HTTP stack.

-   **Mocking External Services**: The `monkeypatch` fixture is used to replace real components with fake "mock" objects for the duration of the test. We mock two things:
    1.  **The AI Service**: We replace the real `content_processor` with a `MagicMock`. We then tell this mock exactly what to return (e.g., `return_value = "Mocked AI summary."`). This makes our test fast, reliable (it won't fail due to network issues), and free (it doesn't make real, costly AI API calls).
    2.  **The Database Engine**: This is the most critical part. The Celery task normally uses the real database `engine`. We use `monkeypatch` to replace it with the temporary, in-memory test `engine` from our `session` fixture. This ensures the task reads from and writes to the same isolated database that our test's "Arrange" and "Assert" steps are using.

This combination of direct function calls and mocking allows us to write a fast, reliable, and focused test for our complex background task.

#### Run Your New Tests

From your project's root directory, run `pytest`:

```bash
pytest app/tests/test_ai_tasks.py -v
```

You should see all tests pass\!

### Step 11: Commit Your Work

```bash
pre-commit run --all-files
git add .
git commit -m "feat(ai): Add Celery for background AI processing of bookmarks"
git push origin main
```

