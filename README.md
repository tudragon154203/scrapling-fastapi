# Scrapling FastAPI

A scalable FastAPI project with a layered architecture and testing framework.

## Project Overview

This project provides a robust and extensible FastAPI service designed for advanced web scraping. It leverages Scrapling/Camoufox for stealthy browser automation, offering specialized endpoints for various crawling needs, including DPD and AusPost tracking, and TikTok session management and content search. The service is built with a layered architecture, emphasizing modularity, testability, and maintainability, and includes features like proxy rotation, humanized browsing actions, and persistent user data handling to effectively bypass bot detection mechanisms.

## Project Structure

```
scrapling-fastapi/
├── app/                    # Main application package
│   ├── __init__.py         # Package initializer
│   ├── main.py             # FastAPI application entry point
│   ├── api/                # API layer - HTTP endpoints and routing (health, crawl, browse, tiktok)
│   ├── core/               # Core layer - Configuration and application setup
│   ├── middleware/         # Middleware layer - Custom middleware components
│   ├── schemas/            # Schemas layer - Pydantic models for data validation
│   └── services/           # Services layer - Business logic
│       ├── browser/        # Browser automation and interactive flows
│       ├── common/         # Shared utilities, interfaces, and base components
│       ├── crawler/        # Web crawling logic, retry, proxy, and specific verticals
│       └── tiktok/         # TikTok specific services (session, search)
├── tests/                  # Test suite
│   ├── api/                # API layer tests
│   ├── core/               # Core layer tests
│   ├── integration/        # End-to-end integration tests
│   │   └── tiktok/         # TikTok integration tests
│   ├── middleware/         # Middleware tests
│   ├── schemas/            # Schema tests
│   └── services/           # Service tests
│       ├── common/         # General application service tests
│       └── tiktok/         # TikTok service tests
│           ├── search/     # TikTok search service tests
│           ├── session/    # TikTok session service tests
│           └── utils/      # TikTok utility tests
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── .gitignore              # Git ignore rules
├── pytest.ini              # Pytest configuration
└── README.md               # This file
```

## Features

- **FastAPI**: Modern, fast (high-performance) web framework for building APIs with Python 3.10+ based on standard Python type hints.
- **Layered Architecture**: Separation of concerns with distinct layers for API, core, middleware, schemas, and services.
- **Environment Configuration**: Configuration management through environment variables.
- **Testing Framework**: Pytest integration for comprehensive testing.
- **Health Checks**: Built-in health check endpoint for monitoring.
- **Advanced Web Scraping**: Utilizes Scrapling/Camoufox for stealthy browser automation.
- **Specialized Crawlers**: Includes dedicated endpoints for DPD and AusPost tracking.
- **TikTok Integration**: Provides endpoints for TikTok session management, content search, and video downloads with configurable browser execution mode and strategy selection.
- **User Data Persistence**: Supports persistent user profiles for maintaining sessions across requests with master/clone architecture for Chromium and single-profile mode for Camoufox.
- **Humanized Actions**: Implements realistic user behavior (mouse movements, typing delays) to avoid bot detection.
- **Configurable Browser Mode**: Control browser execution mode (headless/headful) for TikTok searches with automatic test environment override.

## Prerequisites

- Python 3.10+
- pip (Python package installer)

## Installation

### Local Development

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd scrapling-fastapi
   ```
2. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   Copy `.env.example` to `.env` and modify as needed:

   ```bash
   cp .env.example .env
   ```

   **Key Environment Variables for TikTok Features:**
   - `TIKTOK_DOWNLOAD_STRATEGY`: Download strategy for TikTok videos (`camoufox` or `chromium`, default: `chromium`)
   - `TIKVID_BASE`: Base URL for TikVid resolver service (default: `https://tikvid.io/vi`)
   - `CHROMIUM_USER_DATA_DIR`: Root directory for Chromium profiles (enables persistent Chromium sessions, default: disabled)

   **User Data Management:**
   - `CAMOUFOX_USER_DATA_DIR`: Directory for Camoufox Firefox profiles (default: `data/camoufox_profiles`)
   - `CHROMIUM_USER_DATA_DIR`: Directory for Chromium profiles with master/clone structure (default: disabled)

   If you plan to use the Brave MCP server, copy `.claude/mcp.env.example` to
   `.claude/mcp.env` and provide your Brave Search API key via the
   `BRAVE_API_KEY` variable (or export it in your shell before launching the MCP
   server).

## Running the Application

Run the FastAPI app locally:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 5681 --reload
```

For detailed instructions on running the application, see [RUN.md](RUN.md).

## Testing

Tests run in parallel by default via [`pytest-xdist`](https://pytest-xdist.readthedocs.io/en/latest/) (configured with `-n auto`).
Run all tests:

```bash
python -m pytest
```

Run the suite serially if needed:

```bash
python -m pytest -n 0
```

Unit tests only:

```bash
python -m pytest -m unit
```

Integration tests only:

```bash
python -m pytest -m integration
```

### Test Markers

All test files use file-level pytest markers for categorization:
- **Unit tests**: Marked with `pytestmark = [pytest.mark.unit]` at the top of the file
- **Integration tests**: Marked with `pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("require_scrapling")]` at the top of the file

This ensures proper test categorization and allows running specific test types using the marker selectors above.

### Integration Test Prerequisites

Some integration tests require browser automation dependencies. For TikTok-related integration tests:

```bash
# Install Camoufox browser engine for TikTok tests
pip install camoufox
```

**Note**: TikTok integration tests (`tests/integration/services/tiktok/download/test_tiktok_download.py`) require Camoufox for browser automation. These tests are marked with `@pytest.mark.slow` and will be skipped if Camoufox is not installed.

To run only the TikTok download integration tests:

```bash
python -m pytest tests/integration/services/tiktok/download/test_tiktok_download.py -v
```

To run integration tests serially (recommended for browser tests to avoid conflicts):

```bash
python -m pytest tests/integration/services/tiktok/download/test_tiktok_download.py -n 0
```

## Extending the Template

To use this template for your own project:

1. Clone or copy the template
2. Rename the project directory
3. Update `requirements.txt` with your project dependencies
4. Modify the application code in the `app/` directory
5. Update this README with your project-specific information

## Project Layers

### API Layer (`app/api/`)

Contains HTTP endpoints and routing definitions.

### Core Layer (`app/core/`)

Contains configuration and application setup code.

### Middleware Layer (`app/middleware/`)

Contains custom middleware components.

### Schemas Layer (`app/schemas/`)

Contains Pydantic models for data validation.

### Services Layer (`app/services/`)

Contains business logic and service implementations, further organized into:
- **Browser Layer (`app/services/browser/`)**: Handles browser automation and interactive flows.
- **Common Layer (`app/services/common/`)**: Provides shared utilities, interfaces, and base components.
- **Crawler Layer (`app/services/crawler/`)**: Manages web crawling logic, including retry mechanisms, proxy handling, and specific vertical implementations.
- **TikTok Layer (`app/services/tiktok/`)**: Contains services specific to TikTok, such as session management and search functionalities.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

Specify your license here.
