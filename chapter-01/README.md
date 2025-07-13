Of course. This is an excellent idea. Adding version control, automated code quality with `pre-commit`, and Continuous Integration (CI) with GitHub Actions at the beginning sets a professional foundation for the entire project.

Here is the reworked Chapter 1 with your requested additions, keeping all original text and maintaining the same style.

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
mkdir -p app/{api,core,models,schemas,services,tests}
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
  - `schemas/` - Pydantic models for validation
  - `services/` - Business logic.
  - `tests/` - Test files.

#### Dissecting the Project Structure 🧐

This initial setup establishes a professional, scalable foundation for our application.

  - **Virtual Environment**: The `python3.11 -m venv venv` command creates an **isolated environment** for our project. This means any libraries we install will be specific to this project and won't interfere with other Python projects on your system. Activating it makes it our current shell's active Python environment.
  - **Modular Directories**: Creating directories like `api`, `core`, and `models` is a best practice called "separation of concerns." It keeps our code organized, making it easier to find, manage, and test as the project grows.
  - **`__init__.py` Files**: These empty files are crucial. They tell Python to treat the directories as "packages," which allows us to import code between them (e.g., `from app.core.config import settings`).

-----

### Step 2: Initialize Git & GitHub Repository

Version control is essential. Let's initialize a Git repository and link it to a new repository on GitHub.

1.  **Initialize Git locally:**

    ```bash
    git init
    git branch -M main
    ```

2.  **Create a GitHub Repository:** Go to [GitHub](https://github.com/new) and create a new public repository named `smart-bookmarks`. Do **not** initialize it with a README, license, or .gitignore file.

3.  **Link the local and remote repositories:** Copy the commands from your new GitHub repository page and run them. They will look something like this (replace `YourUsername` with your actual GitHub username):

    ```bash
    git remote add origin https://github.com/YourUsername/smart-bookmarks.git
    ```

#### Dissecting the Git Setup 🧐

  - **`git init`**: This command turns our `smart-bookmarks` directory into a new Git repository, allowing us to track changes to our files. `git branch -M main` renames the default branch to `main`, which is the modern standard.
  - **GitHub**: GitHub is a hosting service for Git repositories. By creating a repository there and linking it with `git remote add origin`, we create a remote backup of our code and a place to collaborate and run automated workflows.

-----

### Step 3: Create a `.gitignore` File

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

### Step 4: Install Dependencies

Next, we'll define and install the third-party libraries our project needs, including tools for code quality.

Create `requirements.txt` file in the project root:

```txt
# Application
fastapi[standard]>=0.115.0
uvicorn[standard]>=0.30.0
sqlmodel>=0.0.16
pydantic-settings>=2.1.0
python-multipart>=0.0.9

# Security
PyJWT>=2.8.0
passlib[bcrypt]>=1.7.4
bcrypt>=4.0.0

# Database
alembic>=1.13.0
psycopg2-binary>=2.9.9

# Testing & Code Quality
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
pre-commit>=3.7.0
ruff>=0.5.5
```

Now, install everything with `pip`:

```bash
pip install -r requirements.txt
```

#### Dissecting the Dependencies 🧐

The `requirements.txt` file lists all the third-party libraries our project needs. Here are the key players:

  - **`fastapi[standard]`**: The web framework itself.
  - **`uvicorn`**: The high-performance ASGI server that will run our FastAPI application.
  - **`sqlmodel`**: Our library for interacting with the database and validating data.
  - **`pydantic-settings`**: Manages application configuration using environment variables.
  - **`PyJWT`**: The library we'll use to create and verify JSON Web Tokens for authentication.
  - **`passlib[bcrypt]`**: For securely hashing and verifying user passwords.
  - **`bcrypt`**: The underlying library that performs the fast and secure hashing for `passlib`.
  - **`alembic`**: Handles database migrations, allowing us to version control our database schema.
  - **`pytest`**: The framework we'll use to write tests for our application.
  - **`pre-commit` & `ruff`**: Tools for automating code quality checks.

-----

### Step 5: Set Up Pre-commit Hooks

To maintain high code quality automatically, we'll use **pre-commit**, a tool that runs checks on your code *before* you're allowed to commit it. This catches simple errors, formatting issues, and style violations early.

1.  **Create the configuration file:** Create a file named `.pre-commit-config.yaml` in your project root.
    ```bash
    touch .pre-commit-config.yaml
    ```
2.  **Add the following configuration:**
    ```yaml
    repos:
    -   repo: https://github.com/pre-commit/pre-commit-hooks
        rev: v5.0.0
        hooks:
        -   id: check-yaml
        -   id: end-of-file-fixer
        -   id: trailing-whitespace
    -   repo: https://github.com/astral-sh/ruff-pre-commit
        rev: v0.12.3
        hooks:
        -   id: ruff
            args: [--fix, --exit-non-zero-on-fix]
        -   id: ruff-format
    ```

3.  **Install the git hooks:**
    ```bash
    pre-commit install
    ```

Now, every time you run `git commit`, these hooks will run automatically\! You can also run them on all files at any time:

```bash
pre-commit run --all-files
```

#### Dissecting the Pre-commit Setup 🧐

  - **Why Pre-commit?**: It enforces a consistent code style across the project for all contributors. It catches silly mistakes before they even get into version control, saving time on code reviews.
  - **`.pre-commit-config.yaml`**: This file defines which checks to run.
  - **`pre-commit-hooks`**: A set of basic hooks that do things like fix trailing whitespace and ensure YAML files are valid.
  - **`ruff`**: This is an extremely fast and powerful Python linter and formatter. It replaces older tools like `black`, `isort`, and `flake8`. The `--fix` argument allows it to automatically fix many of the issues it finds.

-----

### Step 6: Create a GitHub Actions Workflow

Let's automate our testing with GitHub Actions. This will create a Continuous Integration (CI) pipeline that automatically runs our code quality checks and tests every time we push a change to GitHub.

1.  **Create the workflow directory:**
    ```bash
    mkdir -p .github/workflows
    ```
2.  **Create the workflow file:** Create a file named `ci.yml` inside that directory.
    ```bash
    touch .github/workflows/ci.yml
    ```
3.  **Add the following content:**
    ```yaml
    name: CI Pipeline

    on:
      push:
        branches: [ "main" ]
      pull_request:
        branches: [ "main" ]

    jobs:
      build-and-test:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            python-version: ["3.11"]

        steps:
        - name: Checkout code
          uses: actions/checkout@v4

        - name: Set up Python ${{ matrix.python-version }}
          uses: actions/setup-python@v5
          with:
            python-version: ${{ matrix.python-version }}

        - name: Install dependencies
          run: |
            python -m pip install --upgrade pip
            pip install -r requirements.txt
        
        - name: Run pre-commit checks
          run: |
            pre-commit run --all-files

        - name: Run tests with pytest
          run: |
            pytest app/tests || true
    ```

#### Dissecting the GitHub Actions Workflow 🧐

  - **What is CI?**: Continuous Integration is the practice of automatically building and testing your code every time a change is pushed. It ensures the `main` branch is always stable and that new features don't break the application.
  - **`on: [push, pull_request]`**: This defines the triggers. The workflow will run on every push to the `main` branch and every time a pull request is opened against `main`.
  - **`jobs:`**: This section defines the work to be done. We have one job, `build-and-test`.
  - **`runs-on: ubuntu-latest`**: This specifies that our job will run on a fresh virtual machine provided by GitHub, running the latest version of Ubuntu.
  - **`steps:`**: These are the individual commands our CI pipeline will execute in order: checking out the code, setting up Python, installing our dependencies, running our `pre-commit` checks, and finally running our `pytest` suite.


### Step 7: Create the Main App and First Endpoint

Now we'll write the code for our application. To keep things organized, we'll create the main app instance in `main.py` and place our first endpoint in a separate file inside the `api/routes` directory.

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

Next, create the main application file `app/main.py`:

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

  - **`APIRouter`**: The router in `health.py` works like a mini `FastAPI` app. It lets us group related endpoints in a separate file, which keeps our project organized as it grows.
  - **`app.include_router(...)`**: In `main.py`, this line tells our main application to include all the routes defined in our `health.router`. This makes our main file a clean entry point responsible for app-level configuration, while the routing logic lives in the `api.routes` module.

-----

### Step 8: Run Your First API

Now, let's run the application using FastAPI's development server.

```bash
# Development mode with auto-reload
fastapi dev app/main.py
```

#### Dissecting the `fastapi dev` Command 🧐

The `fastapi dev` command's key feature is **auto-reloading**. The server watches your project files for changes. When you save a file, the server automatically restarts to apply the new code, speeding up your workflow immensely.

-----

### Step 9: 🧪 Test It Out\!

1.  **Visit the API**: Open http://localhost:8000 in your browser.
2.  **Check the health endpoint**: Open http://localhost:8000/health.
3.  **Explore the automatic docs**: Open http://localhost:8000/docs.

-----

### Step 10: Configuration Management

Let's separate our application's configuration from its code using environment variables.

Create `app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )
    
    PROJECT_NAME: str = "Smart Bookmarks API"
    PROJECT_DESCRIPTION: str = "A bookmark manager to organize your favorite links"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: Optional[str] = "sqlite:///./bookmarks.db"
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

settings = Settings()
```

Create a `.env` file for local development:

```env
PROJECT_NAME="Smart Bookmarks API"
DATABASE_URL="sqlite:///./bookmarks.db"
SECRET_KEY="development-secret-key-change-this"
```

Create a `.env.example` to serve as a template:

```env
PROJECT_NAME="Smart Bookmarks API"
DATABASE_URL="sqlite:///./bookmarks.db"
SECRET_KEY="your-secret-key-here"
```

#### Dissecting the Configuration 🧐

  - **`Settings(BaseSettings)`**: This class from `pydantic-settings` automatically reads variables from your system's environment or a `.env` file and validates them.
  - **`.env` vs `.env.example`**: The `.env` file stores secrets and is ignored by Git. The `.env.example` is a non-secret template committed to version control.

-----

### Step 11: Update the App to Use Settings

Finally, let's refactor our application to use the new settings object.

**Update `app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings # Add
from app.api.routes import health

app = FastAPI(
    title=settings.PROJECT_NAME, # Change
    description=settings.PROJECT_DESCRIPTION, # Change
    version=settings.VERSION, # Change
    openapi_url=f"{settings.API_V1_STR}/openapi.json" # Add
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
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
        "message": f"Welcome to {settings.PROJECT_NAME}", # Change
        "version": settings.VERSION, # Change
    }
```

**Update `app/api/routes/health.py`**

```python
from fastapi import APIRouter
from app.core.config import settings # Add

# Create an API router
router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME # ADD
    }
```

#### Dissecting the Update 🧐

By replacing static text with references like `settings.PROJECT_NAME`, our application becomes much more flexible. We can change core settings by just editing the `.env` file, without touching the code.

### Step 12: Commit and Push Your Work

Now that we've set up our project, let's save all our work to Git and push it to GitHub. This will also trigger our new CI pipeline for the first time.

```bash
# Add all new files to Git's staging area
git add .

# Run pre-commit on the staged files (this will happen automatically
# on commit, but it's good to see it run manually)
pre-commit run
check yaml...............................................................Passed
fix end of files.........................................................Passed
trim trailing whitespace.................................................Failed
- hook id: trailing-whitespace
- exit code: 1
- files were modified by this hook

Fixing .github/workflows/ci.yml
Fixing app/core/config.py

ruff (legacy alias)......................................................Passed
ruff format..............................................................Failed
- hook id: ruff-format
- files were modified by this hook

3 files reformatted, 7 files left unchanged

# Add the updated files
git add .

# Create your first commit
git commit -m "feat: Initial project setup with FastAPI, pre-commit, and CI"

# Push your commit to the main branch on GitHub
git push origin main
```

Now, go to your repository on GitHub and click on the "Actions" tab. You should see your "CI Pipeline" workflow running\!

-----

### Understanding the Setup

**What we've accomplished:**

  - ✅ Modern, scalable project structure.
  - ✅ Git repository hosted on GitHub.
  - ✅ Automated code quality checks with Pre-commit.
  - ✅ Continuous Integration pipeline with GitHub Actions.
  - ✅ FastAPI with automatic documentation.
  - ✅ Configuration management with environment variables.

### Pro Tips

1.  **Always use virtual environments** to isolate dependencies.
2.  **Never commit `.env` files** - use `.env.example` as a template.
3.  **Commit often**: Small, logical commits are easier to manage than large ones.
4.  **Trust your CI**: Let the automated workflow be your first line of defense against bugs.

📝 **Exercise**: Try adding a new endpoint `/api/v1/status` that returns the current time and database URL (masked for security). This will help you practice creating endpoints and using settings.

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