# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**🚨 CONSTITUTION COMPLIANCE MANDATORY**: All development must follow the principles in `.specify/memory/constitution.md`.

## Development Commands

### Running the Application

- **Development with reload**: `python -m uvicorn app.main:app --host 0.0.0.0 --port 5681 --reload`
- **Production with pm2**: `pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 5681" --name scrapling-api`

### Testing

- **All tests**: `python -m pytest`
- **Quick test run**: `python -m pytest -q`
- **Verbose output**: `python -m pytest -v`
- **Unit tests only**: `python -m pytest -m unit`
- **Integration tests only**: `python -m pytest -m integration` (requires real network/browser)

### Test Structure

The test suite is organized into two main categories:

```
tests/
├── unit/           # Unit tests (mocked, no network/browser dependencies)
│   ├── api/        # API endpoint unit tests
│   ├── core/       # Configuration, logging unit tests
│   ├── schemas/    # Pydantic schema validation tests
│   └── services/   # Business logic unit tests
│       ├── browser/
│       ├── common/
│       ├── crawler/
│       ├── proxy/
│       └── tiktok/
└── integration/    # Real network/browser tests only
    ├── api/        # API integration tests
    ├── chromium/   # Browser automation integration
    ├── crawl/      # Crawling integration tests
    ├── services/   # Service integration tests
    └── tiktok/     # TikTok integration tests
```

### Test Markers

All test files must have proper pytest markers at the top of the file:
- **Unit tests**: `pytestmark = [pytest.mark.unit]`
- **Integration tests**: `pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("require_scrapling")]`

### Port Information

- Application runs on port 5681 by default
- Health endpoint: `http://localhost:5681/health`
- API docs: `http://localhost:5681/docs`

## Architecture Overview

This is a FastAPI web scraping service using Scrapling for browser automation. The architecture follows a clean layered structure:

### Core Components

- **app/main.py**: Application factory with CORS middleware and lifespan management
- **app/api/routes.py**: REST API endpoints for crawling operations
- **app/core/config.py**: Configuration management using pydantic-settings
- **app/schemas/**: Pydantic models for request/response validation

### Services Layer

- **app/services/crawler/**: Business logic for different scrapers
  - `generic.py`: Generic crawling functionality
  - `dpd.py`: DPD tracking-specific scraping
  - `executors/`: Task execution modules
  - `utils/`: Scraping utilities
- **app/services/tiktok/**: NEW - TikTok session endpoint implementation
  - `service.py`: TikTok session management and login detection
  - `executor.py`: TikTok-specific browsing executor
  - `utils/`: TikTok utilities and login detection logic

### Key Dependencies

- **FastAPI**: Web framework with automatic OpenAPI docs
- **Scrapling**: Browser automation and scraping library
- **BrowserForge**: Browser fingerprinting for anti-detection
- **Pydantic 2.9**: Data validation with Python 3.13 compatibility

### API Endpoints

- `POST /crawl`: Generic crawling endpoint
- `POST /crawl/dpd`: DPD tracking endpoint
- `POST /tiktok/session`: NEW - TikTok interactive session endpoint (requires login)
- `GET /health`: Health check

### Project Structure

```
app/
├── main.py          # FastAPI app factory
├── api/             # HTTP endpoints
│   ├── routes.py    # NEW: TikTok session endpoint
│   └── existing endpoints
├── core/            # Configuration
├── schemas/         # Pydantic models
│   ├── tiktok.py    # NEW: TikTok session schemas
│   └── existing schemas
├── services/        # Business logic
│   ├── tiktok/      # NEW: TikTok session implementation
│   ├── common/      # NEW: Abstract browsing executor
│   ├── crawler/     # Existing crawling services
│   └── browser/     # Browser automation utilities
└── middleware/      # Custom middleware
```

### Environment Setup

- Uses `.env` for configuration
- Python 3.10+ required
- Node.js/npm only needed for pm2 production deployment

### Integration Testing

Some tests require real network/browser operations,  which will perform actual web scraping operations.

### Constitutional Requirements

- **Test-Driven Development**: NON-NEGOTIABLE - Tests must be written before implementation
- **Layered Architecture**: Strict separation of API/Core/Middleware/Schemas/Services layers
- **Schema Consistency**: All new schemas must follow existing patterns in `app/schemas/*.py`
- **Code Quality**: Must pass `flake8` linting for `app/` and `tests/` directories
- **Location Rules**: Never place implementation code in `.specify/` directory

## Backwards Compatibility

- **Policy**: NO NEED for backwards compatibility
- **Breaking Changes**: Allowed without migration requirements
- **Focus**: Clean architecture and implementation over legacy support

### CUSTOM RULES

* init.py should be empty

