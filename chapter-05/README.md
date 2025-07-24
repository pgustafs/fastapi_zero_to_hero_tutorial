# Chapter 5: Logging and Monitoring

## What is Logging?

Logging is the practice of recording events that happen in your application. Think of it as a diary for your API—tracking what happened, when, and why. Good logging is essential for debugging, monitoring, and security.

## Why Logging Matters

1.  **Debugging**: Find out *why* something went wrong.
2.  **Monitoring**: Know when things break *before* users complain.
3.  **Analytics**: Understand how your API is being used.
4.  **Security**: Detect suspicious activities and audit trails.

## How Python Logging Works

Python's `logging` module provides a powerful system with four main components:

  - **Loggers**: The entry point to the logging system (e.g., `logging.getLogger(__name__)`).
  - **Handlers**: Send log records to destinations like the console or a file.
  - **Formatters**: Specify the layout and structure of your log messages.
  - **Levels**: The severity of a message (DEBUG, INFO, WARNING, ERROR, CRITICAL).

## Let's Build: A Comprehensive Logging System

### Step 1: Configure Structured Logging

We'll start by creating a centralized logging configuration. We'll use **structured logging**, which means writing logs in a machine-readable format like JSON. This is a best practice for modern applications as it makes logs much easier to search, filter, and analyze.

#### Step 1:
First, add `rich` to your `requirements.txt` for pretty development logging and install it:

```txt
# In requirements.txt
rich>=13.0.0
```

```bash
pip install -r requirements.txt
```

#### Step 2: Add Settings to `config.py`

First, add the new configuration variables to your `Settings` class.

**Update `app/core/config.py`:**

```python
class Settings(BaseSettings):
    # ... (existing settings) ...
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # ✅ Add new logging settings
    LOG_LEVEL: str = "INFO"
    LOG_ROTATION_SIZE_MB: int = 5
    LOG_ROTATION_BACKUP_COUNT: int = 3
```


#### Step 3: Update Your `.env` Files

Now, add these new variables to your `.env` and `.env.example` files so you can easily change them.

**In `.env` and `.env.example`, add these lines:**

```env
# ... (existing variables) ...

# Logging
LOG_LEVEL="INFO"
LOG_ROTATION_SIZE_MB=5
LOG_ROTATION_BACKUP_COUNT=3
```

#### Step 4: Create `app/core/logging_config.py`

Now, create `app/core/logging_config.py`:

```python
import logging.config
import sys
import json
from datetime import datetime
from pathlib import Path
from app.core.config import settings

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format."""
    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
        }
        if hasattr(record, "extra_info"):
            log_object.update(record.extra_info)
        
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_object)

# This dictionary defines the entire logging configuration.
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "app.core.logging_config.JSONFormatter",
        },
    },
    "handlers": {
        "rich_console": {
            "class": "rich.logging.RichHandler",
            "level": settings.LOG_LEVEL.upper(),
            "rich_tracebacks": True,
            "tracebacks_show_locals": True,
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/app.log",
            "maxBytes": settings.LOG_ROTATION_SIZE_MB * 1024 * 1024,
            "backupCount": settings.LOG_ROTATION_BACKUP_COUNT,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "logs/errors.log",
            "maxBytes": settings.LOG_ROTATION_SIZE_MB * 1024 * 1024,
            "backupCount": settings.LOG_ROTATION_BACKUP_COUNT,
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["rich_console"], "level": "INFO", "propagate": False},
        "sqlalchemy": {"handlers": ["rich_console"], "level": "WARNING", "propagate": False},
        "app": {
            "handlers": ["rich_console", "app_file", "error_file"], 
            "level": "DEBUG", 
            "propagate": False
        },
    },
    "root": {
        "handlers": ["rich_console", "app_file", "error_file"],
        "level": settings.LOG_LEVEL.upper(),
    },
}

```

#### Dissecting the Logging Configuration 🧐

  - **Structured Logging**: Our custom `JSONFormatter` turns log messages into JSON objects. This is incredibly powerful because these logs can be easily ingested and searched by monitoring tools.
  - **`dictConfig`**: This is the standard, modern way to configure Python logging. By defining our entire setup in a single dictionary, we gain complete control and prevent conflicts from default configurations (like Uvicorn's).
  - **Handlers**: We define three distinct destinations for our logs:
    1.  **`rich_console`**: Uses the powerful `rich` library to provide beautiful, colored, and easy-to-read output in the terminal during development.
    2.  **`app.log`**: A `RotatingFileHandler` that writes structured JSON logs to `logs/app.log`. It automatically rotates the file when it reaches 5MB, keeping the 3 most recent backups.
    3.  **`errors.log`**: A dedicated handler that only captures critical `ERROR` level logs, making it easy to find what's broken.
  - **Loggers**: The `loggers` section gives us fine-grained control. We tame the noisy `sqlalchemy` logger by setting its level to `WARNING` and direct our own `app` logger to send messages to all three handlers. `propagate: False` is a key setting that stops `app` logs from being passed up to the root logger, preventing duplicated messages.

#### Securing Database Logs

By default, SQLAlchemy can be configured to "echo" every SQL statement it runs to the logs. While useful for debugging, this can log sensitive data like the hashed passwords in our `INSERT` statements. It's a best practice to disable this in most environments.

Update `app/core/database.py`:

```python
# app/core/database.py

# ...
engine = create_engine(
    settings.DATABASE_URL,
    echo=False, # ✅ Change this from True to False
    connect_args={"check_same_thread": False}
)
# ...
```

#### Dissecting the Database Log Change 🧐

Setting `echo=False` tells SQLAlchemy to stop logging every raw SQL statement and its parameters. Our application logs (e.g., "User logged in") are still active, but we no longer log the low-level database chatter, making our logs cleaner and more secure.

-----

### Step 2: Create Request Logging Middleware

A **middleware** is a function that processes every request before it hits an endpoint and every response before it's sent. It's the perfect place to automatically log every incoming request and its outcome.

Create `app/middleware/logging.py`:

```python
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Log request details
        start_time = time.time()
        
        # Prepare a dictionary with extra info to pass to the logger
        log_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
        }
        logger.info("Request started", extra={"extra_info": log_extra})
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Log response details
            duration_ms = (time.time() - start_time) * 1000
            log_extra["status_code"] = response.status_code
            log_extra["duration_ms"] = f"{duration_ms:.2f}"
            logger.info("Request completed", extra={"extra_info": log_extra})
            
            # Add request ID to response header for client-side correlation
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            # Log any unhandled exceptions
            log_extra["status_code"] = 500
            logger.exception(
                "Unhandled exception during request",
                exc_info=e,
                extra={"extra_info": log_extra}
            )
            # Re-raise the exception to be handled by FastAPI's error handling
            raise
```

#### Dissecting the Logging Middleware 🧐

  - **`BaseHTTPMiddleware`**: This is a standard FastAPI/Starlette class for creating middleware. The `dispatch` method is called for every request.
  - **Request ID**: We generate a unique ID (`request_id`) for every single request. This is a critical best practice. If you have an issue, you can search your logs for this ID to see every event related to that specific request.
  - **Timing**: We record the time before and after the request is processed to calculate its duration, a key performance metric.
  - **Structured `extra`**: We pass a dictionary to the `extra` parameter of our logger. Our custom `JSONFormatter` knows to automatically add the contents of this dictionary to the final JSON log object.

-----

### Step 3: Integrate Logging into the Application

Now, let's tell our FastAPI app to use our new logging setup and middleware.

Update `app/main.py`:

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db, get_session
# Import logging setup and middleware
import logging.config
from app.core.logging_config import LOGGING_CONFIG
from app.middleware.logging import LoggingMiddleware
from app.api.routes import api_router

# Apply the logging configuration at the module level
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    """
    logger.info("--- App startup ---") # Add 

    # Initialize the database if not in a test environment
    if get_session not in app.dependency_overrides:
        init_db()

    yield

    logger.info("--- App shutdown ---") # Add

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

#  Add the logging middleware. This should be one of the first.
app.add_middleware(LoggingMiddleware)

# ... (CORS middleware, include_router, and root endpoint) ...
```

### Dissecting the Integration 🧐

This step connects your logging system to the core of your FastAPI application.

-   **Configuration at Module Level**: By placing `logging.config.dictConfig(LOGGING_CONFIG)` at the top of `main.py`, you ensure that your custom logging configuration is the **first thing to run** when the application is loaded. This is crucial because it takes control of the logging system before Uvicorn or other libraries can apply their own default (and often conflicting) settings.

-   **Activating the Middleware**: The line `app.add_middleware(LoggingMiddleware)` registers our custom middleware with the FastAPI application. Now, every single HTTP request will be intercepted and processed by our `LoggingMiddleware`, which is how we get automatic, detailed logs for every API call.

-   **Centralized Logging in Action**: Notice that other parts of your application, like the `lifespan` manager, can now get and use a logger (`logger = logging.getLogger("app")`). Since the configuration is already set, it will automatically use the correct handlers and formatters we defined, ensuring consistent logging across your entire project.

-----

### Step 4: Add Specific Application-Level Logging

The middleware gives us great general-purpose logs, but sometimes we want to log specific, meaningful events from our business logic, like a failed login attempt.

Update the `login` endpoint in `app/api/routes/auth.py` to add more specific logs:

```python
# app/api/routes/auth.py
import logging #  Add logging import
# Get a logger for this specific module
logger = logging.getLogger(__name__)

# ...

@router.post("/login", response_model=Token)
def login(form_data: LoginRequest, request: Request, db: SessionDep):
    # ... rate limiting logic ...

    user = db.exec(
        select(User).where(
            or_(
                User.username == form_data.username,
                User.email == form_data.username,
            )
        )
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        login_limiter.add_attempt(request.client.host)
        
        # ✅ Log the specific failure event
        logger.warning(
            "Failed login attempt for username: %s",
            form_data.username,
            extra={"extra_info": {"event": "LOGIN_FAILURE", "username": form_data.username}}
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # ... successful login logic ...
    
    # ✅ Log the specific success event
    logger.info(
        "User logged in successfully: %s",
        user.username,
        extra={"extra_info": {"event": "LOGIN_SUCCESS", "user_id": user.id}}
    )
    
    return Token(access_token=access_token, token_type="bearer")
```

#### Dissecting Application Logging 🧐

  - **`logging.getLogger(__name__)`**: This is the standard way to get a logger instance specific to the current file. It helps you trace where a log message originated.
  - **Contextual Messages**: We now log specific, meaningful events like `LOGIN_FAILURE` and `LOGIN_SUCCESS`. This is much more valuable than just seeing a generic `POST /login` request log. We include contextual data like the `user_id` in the `extra` dictionary, which will be added to our structured JSON log.

-----

### 🧪 Testing Your Logging System

1.  **Delete old logs** to start fresh: `rm logs/*.log`

2.  **Start your server**: `fastapi dev app/main.py`

3.  **Make some API calls:**

      * **Register a user:**

        ```bash
        curl -X POST "http://localhost:8000/api/v1/auth/register" \
          -H "Content-Type: application/json" \
          -d '{
            "username": "log_tester",
            "email": "log@example.com",
            "password": "a_good_password"
          }'
        ```

      * **Log in successfully (and capture the token):**

        ```bash
        export TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \
          -H "Content-Type: application/json" \
          -d '{"username": "log_tester", "password": "a_good_password"}' \
          | jq -r .access_token)
        ```

      * **Try to log in with a wrong password:**

        ```bash
        curl -X POST "http://localhost:8000/api/v1/auth/login" \
          -H "Content-Type: application/json" \
          -d '{"username": "log_tester", "password": "a_wrong_password"}'
        ```

      * **Create a bookmark (using the captured token):**

        ```bash
        curl -X POST "http://localhost:8000/api/v1/bookmarks/" \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" \
          -d '{
            "url": "https://example.com/logging-test",
            "title": "Logging Test Bookmark"
          }'
        ```
4.  **Check your console output**: You should see the simple, human-readable logs.
5.  **Check your log files**:
      * **`cat logs/app.log | jq`**: View the structured JSON logs for all requests. Look for the `request_id` and the `extra_info` we added.
      * **`cat logs/errors.log | jq`**: View the dedicated error log. This should be empty unless an unexpected `500 Internal Server Error` occurred.


### Step 5: Making the Request ID Accessible

Our middleware is creating a unique ID for each request, but right now it's "trapped" there. Let's make this ID available to our entire application (for better logs) and return it to the client (for better support), which is a crucial best practice for traceability.

#### 1\. Share the Request ID with Endpoints

We'll use `request.state`, a carrier object that lives for the duration of a single request, to share the ID from the middleware to the endpoints.

**Update `app/middleware/logging.py`:**

```python
# app/middleware/logging.py

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        # ✅ Add this line to make the ID available to endpoints
        request.state.request_id = request_id
        
        # ... rest of the middleware ...
```

Now, you can access this ID in any endpoint. Let's update our `login` endpoint to include it in its specific log messages.

**Update `app/api/routes/auth.py`:**

```python
# app/api/routes/auth.py

@router.post("/login", ...)
def login(form_data: LoginRequest, request: Request, db: SessionDep):
    # ...
    if not user or not verify_password(...):
        # ...
        logger.warning(
            "Failed login attempt for username: %s",
            form_data.username,
            extra={"extra_info": {
                "event": "LOGIN_FAILURE",
                "username": form_data.username,
                # ✅ Access the request_id from the request state
                "request_id": getattr(request.state, "request_id", None),
            }}
        )
        raise HTTPException(...)
    # ...
```

#### 2\. Return the Request ID to the Client

It's a best practice to return the `request_id` in a response header, typically `X-Request-ID`. Your `LoggingMiddleware` already does this\!

The code is here in `app/middleware/logging.py`:

```python
# This code is already in your middleware
response = await call_next(request)
response.headers["X-Request-ID"] = request_id # <-- This line does it
return response
```

You can verify this by running a `curl` command with the `-v` (verbose) flag, which shows response headers:

```bash
curl -v -X GET "http://localhost:8000/api/v1/health"
```

You will see `< X-Request-ID: ...` in the response headers.

#### Dissecting the Changes 🧐

  - **`request.state`**: Think of this as a temporary storage space that is unique to each request. It's the standard FastAPI way to pass data between middleware and endpoints.
  - **`X-Request-ID` Header**: This header acts as a reference number for the client. If an API call fails, the client can report this ID to your support team, allowing you to instantly find all related logs.


### Step 6: Ignore Log Files in Git

Log files are generated by your running application and are specific to your local environment. They can grow very large and contain information you don't want to save in version control. They should always be ignored.

Update your `.gitignore` file to include the `logs/` directory.

```gitignore
# ... (existing content) ...

# SQLite Databse
*.db

# Application logs
logs/
```

#### Dissecting the Change 🧐

Adding `logs/` to your `.gitignore` tells Git to completely ignore the `logs` directory and all files inside it (like `app.log` and `errors.log`). This keeps your Git repository clean and prevents environment-specific data from being committed.

### Step 6: Commit Your Work

You've added a robust, production-ready logging system to your application. Let's save it.

```bash
git add .
git commit -m "feat( observability): Add structured logging and request middleware"
git push origin main
```