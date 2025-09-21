# Project: Scrapling FastAPI

## Project Overview

This project is a scalable FastAPI application designed for advanced web scraping. It leverages Scrapling/Camoufox for stealthy browser automation and provides specialized endpoints for various crawling needs, including DPD and AusPost tracking, and TikTok session management and content search. The service is built with a layered architecture, emphasizing modularity, testability, and maintainability, and includes features like proxy rotation, humanized browsing actions, and persistent user data handling to effectively bypass bot detection mechanisms.

**Key Technologies:**
*   **Backend:** Python 3.10+, FastAPI
*   **Web Scraping:** Scrapling/Camoufox
*   **Data Validation:** Pydantic
*   **Testing:** Pytest

## Building and Running

### Prerequisites

*   Python 3.10+
*   pip (Python package installer)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd scrapling-fastapi
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure environment variables:**
    Copy `.env.example` to `.env` and modify as needed:
    ```bash
    cp .env.example .env
    ```

### Running the Application Locally

To run the FastAPI application locally:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 5681 --reload
```

### Testing

*   **Run all tests:**
    ```bash
    python -m pytest
    ```
*   **Run unit tests only:**
    ```bash
    python -m pytest -m "not integration"
    ```
*   **Run integration tests only:**
    ```bash
    python -m pytest -m integration
    ```

## Development Conventions

*   **Layered Architecture:** The project follows a clear layered architecture with distinct responsibilities for API, core, middleware, schemas, and services.
*   **Data Validation:** Pydantic models are used extensively for data validation and serialization.
*   **Testing:** Pytest is the chosen framework for comprehensive testing, with clear separation between unit and integration tests.
*   **Configuration:** Environment variables are used for application configuration.
