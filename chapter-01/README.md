# Chapter 1: Project Setup and First Steps

## What We're Building

A bookmark manager API that lets you save, organize, and search your favorite links. Users can add URLs with titles, descriptions, and tags - creating their personal knowledge base.

## What is FastAPI?

FastAPI is a modern Python web framework that's:

  - **Fast**: Built on Starlette and Pydantic for high performance.
  - **Type-safe**: Uses Python type hints for validation and documentation.
  - **Developer-friendly**: Automatic API documentation and editor support.

## Why FastAPI Matters

1.  **Automatic validation**: No more manual data checking.
2.  **Self-documenting**: Interactive API docs generated automatically.
3.  **Modern Python**: Uses async/await and type hints.
4.  **Production-ready**: Built-in security, testing, and performance features.

## How FastAPI Works

FastAPI uses Python type annotations to:

1.  Validate request data.
2.  Serialize responses.
3.  Generate OpenAPI documentation.
4.  Provide editor autocomplete.

-----

## Let's Build: Setting Up Your Project

### Step 1: Create Your Project Structure

First, we'll create the directory structure for our project and set up an isolated Python environment.

```bash
# Create project directory
mkdir smart-bookmarks
cd smart-bookmarks

# Create Python virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Create project structure
mkdir -p app/{api,core,models,services,tests}
mkdir app/api/routes
touch app/__init__.py
touch app/api/routes/__init__.py
touch app/{api,core,models,services,tests}/__init__.py
```

**Project structure explained:**

  - `app/` - Main application package.
  - `api/` - API endpoints and routing.
  - `core/` - Core functionality (config, security, database).
  - `models/` - Database models (using SQLModel).
  - `services/` - Business logic.
  - `tests/` - Test files.

#### Dissecting the Project Structure 🧐

This initial setup establishes a professional, scalable foundation for our application.

  - **Virtual Environment**: The `python3.11 -m venv venv` command creates an **isolated environment** for our project. This means any libraries we install will be specific to this project and won't interfere with other Python projects on your system. Activating it makes it our current shell's active Python environment.
  - **Modular Directories**: Creating directories like `api`, `core`, and `models` is a best practice called "separation of concerns." It keeps our code organized, making it easier to find, manage, and test as the project grows.
  - **`__init__.py` Files**: These empty files are crucial. They tell Python to treat the directories as "packages," which allows us to import code between them (e.g., `from app.core.config import settings`).

-----

### Step 2: Create a `.gitignore` File

It's critical to tell our version control system (like Git) to ignore certain files, such as secrets and environment-specific clutter.

Create a `.gitignore` file in your project's root directory:

```bash
# In the smart-bookmarks root directory
touch .gitignore
```

Add the following content to your new `.gitignore` file:

```gitignore
# Virtual Environment
venv/

# Python cache
__pycache__/
*.pyc

# Environment variables
.env

# IDE / Editor specific
.idea/
.vscode/

# SQLite Databse
*.db
```

#### Dissecting the `.gitignore` File 🧐

This file acts as a blocklist for Git. Any file or folder pattern listed here will be ignored by Git and won't be committed to your repository. This is essential for keeping your virtual environment (`venv/`), Python cache files (`__pycache__/`), and, most importantly, your secrets file (`.env`) out of version control.

-----

### Step 3: Install Dependencies

Next, we'll define and install the third-party libraries our project needs.

Create a `requirements.txt` file in the project root:

```txt
fastapi[standard]>=0.115.0
uvicorn[standard]>=0.30.0
sqlmodel>=0.0.16
pydantic>=2.5.0
pydantic-settings>=2.1.0
PyJWT>=2.8.0
passlib[bcrypt]>=1.7.4
bcrypt>=4.0.0
python-multipart>=0.0.9
httpx>=0.27.0
alembic>=1.13.0
psycopg2-binary>=2.9.9
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
PyJWT>=2.8.0
```

Now, install everything with `pip`:

```bash
pip install -r requirements.txt
```

#### Dissecting the Dependencies 🧐

The `requirements.txt` file lists all the third-party libraries our project needs. The `pip install -r` command reads this file and installs them all at once. Here are the key players:

  - **`fastapi[standard]`**: The web framework itself. The `[standard]` part is a convenient way to install FastAPI along with `uvicorn` and other recommended dependencies.
  - **`uvicorn`**: The high-performance ASGI server that will run our FastAPI application.
  - **`sqlmodel`**: Our library for interacting with the database and validating data.
  - **`pydantic-settings`**: Manages application configuration using environment variables.
  - **`PyJWT`**:
  - **`passlib[bcrypt]`**: For securely hashing and verifying user passwords.
  - **`bcrypt`**:
  - **`alembic`**: Handles database migrations, allowing us to version control our database schema.
  - **`pytest`**: The framework we'll use to write tests for our application.

-----

### Step 4: Create the Main App and First Endpoint

Now we'll write the code for our application. To keep things organized from the start, we'll create the main app instance in `main.py` and place our first endpoint in a separate file inside the `api/routes` directory.

First, create a health check endpoint in `app/api/routes/health.py`:

```python
from fastapi import APIRouter

# Create an API router
router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
```

Next, create the main application file `app/main.py` and include the new router:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health # Import the new router

# Create FastAPI instance
app = FastAPI(
    title="Smart Bookmarks API",
    description="A bookmark manager to organize your favorite links",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the health check router
app.include_router(health.router)


@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "message": "Welcome to Smart Bookmarks API",
        "version": "1.0.0"
    }
```

#### Dissecting the App and Router 🧐

This structure demonstrates a scalable pattern for building APIs.

  - **`APIRouter`**: The router in `health.py` works like a mini `FastAPI` app. It lets us group related endpoints in a separate file, which keeps our project organized as it grows.
  - **`app.include_router(...)`**: In `main.py`, this line tells our main application to include all the routes defined in our `health.router`. This makes our main file a clean entry point responsible for app-level configuration, while the routing logic lives in the `api.routes` module.

-----

### Step 5: Run Your First API

Now, let's run the application using FastAPI's development server.

```bash
# Development mode with auto-reload
fastapi dev app/main.py

# You should see:
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process using StateMachine
```

#### Dissecting the `fastapi dev` Command 🧐

The `fastapi dev` command is a powerful tool for development.

  - **`dev` mode**: This command runs the app in "development mode," and its key feature is **auto-reloading**. The server watches your project files for changes. When you save a file, the server automatically restarts to apply the new code, speeding up your workflow immensely.
  - **Uvicorn**: Under the hood, FastAPI is using the Uvicorn server to run the application, as indicated by the log output.

-----

### 🧪 Test It Out\!

1.  **Visit the API**: Open http://localhost:8000 in your browser.
2.  **Check the health endpoint**: Open http://localhost:8000/health.
3.  **Explore the automatic docs**: Open http://localhost:8000/docs to see the interactive Swagger UI.
4.  **Alternative docs**: Open http://localhost:8000/redoc for a different documentation view.

-----

### Step 6: Configuration Management

Let's separate our application's configuration from its code using environment variables.

Create `app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings using Pydantic BaseSettings.
    This allows us to use environment variables for configuration.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )
    
    # API Settings
    PROJECT_NAME: str = "Smart Bookmarks API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: Optional[str] = "sqlite:///./bookmarks.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]


# Create global settings instance
settings = Settings()
```

Create a `.env` file in the project root for local development:

```env
PROJECT_NAME="Smart Bookmarks API"
DATABASE_URL="sqlite:///./bookmarks.db"
SECRET_KEY="development-secret-key-change-this"
```

Create a `.env.example` file to serve as a template for other developers:

```env
PROJECT_NAME="Smart Bookmarks API"
DATABASE_URL="sqlite:///./bookmarks.db"
SECRET_KEY="your-secret-key-here"
```

#### Dissecting the Configuration 🧐

  - **`Settings(BaseSettings)`**: This class from `pydantic-settings` is the core of our configuration management. It automatically reads variables from your system's environment or a `.env` file and validates them against the defined Python types.
  - **`.env` vs `.env.example`**: The `.env` file stores actual secrets and should **never** be committed to version control. The `.env.example` file is a non-secret template that shows other developers what variables are needed to run the application.

-----

### Step 7: Update the App to Use Settings

Finally, let's refactor our application to use the new settings object instead of hardcoded values.

Update `app/main.py` and `app/api/routes/health.py`:

**`app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import health

# Create FastAPI instance with settings
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS with settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router
app.include_router(health.router)


@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
    }
```

**`app/api/routes/health.py`**

```python
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME
    }
```

#### Dissecting the Update 🧐

  - **`from app.core.config import settings`**: We import the global `settings` instance where it's needed.
  - **`title=settings.PROJECT_NAME`**: We replace static text with dynamic references to our settings object. This makes our application flexible. We can now change the project's name, CORS origins, or other parameters just by editing the `.env` file, without touching the application code.

-----

### 🧪 Test Configuration

1.  Restart your server (`Ctrl+C` and run `fastapi dev app/main.py` again).
2.  Visit http://localhost:8000 and http://localhost:8000/health.
3.  You should see the project name from your `.env` file reflected in the responses.

-----

### Understanding the Setup

**What we've accomplished:**

  - ✅ Modern, scalable project structure.
  - ✅ FastAPI app with a modular router.
  - ✅ Configuration management with environment variables.
  - ✅ CORS setup for frontend integration.
  - ✅ Health check endpoint for monitoring.

**Key concepts learned:**

1.  **FastAPI app creation**: How to initialize and configure a main application.
2.  **API Routers**: How to organize endpoints into modular files.
3.  **Settings management**: Using Pydantic for robust, type-safe configuration.
4.  **Environment variables**: Keeping secrets and settings out of your code.
5.  **Automatic API documentation**: Exploring and using the docs generated by FastAPI.

### Pro Tips

1.  **Always use virtual environments** to isolate project dependencies.
2.  **Never commit `.env` files** to version control — use `.gitignore`.
3.  **The `fastapi dev` CLI** is your best friend for development with its auto-reload feature.
4.  **Type hints** are not just suggestions; FastAPI uses them to give you data validation, serialization, and autocompletion for free.

### What's Next?

In Chapter 2, we'll design our database models using SQLModel and create our bookmark data structure. We'll see how SQLModel combines the best of SQLAlchemy and Pydantic\!

### Quick Commands Reference

```bash
# Run development server
fastapi dev app/main.py

# Run production server
fastapi run app/main.py

# Run with custom host/port
fastapi dev app/main.py --host 0.0.0.0 --port 8080

# Install new package
pip install package-name
pip freeze > requirements.txt
```

-----

📝 **Exercise**: Try adding a new endpoint `/api/v1/status` that returns the current time and database URL (masked for security). This will help you practice creating endpoints and using settings.