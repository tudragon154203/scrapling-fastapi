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
│   ├── middleware/         # Middleware tests
│   ├── schemas/            # Schema tests
│   └── services/           # Service tests
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
- **TikTok Integration**: Provides endpoints for TikTok session management and content search.
- **User Data Persistence**: Supports persistent user profiles for maintaining sessions across requests.
- **Humanized Actions**: Implements realistic user behavior (mouse movements, typing delays) to avoid bot detection.

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
python -m pytest -m "not integration"
```

Integration tests only:

```bash
python -m pytest -m integration
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
