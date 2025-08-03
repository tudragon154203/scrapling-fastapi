# FastAPI Project Template

A scalable FastAPI project template with a layered architecture, Docker support, and testing framework.

## Project Structure

```
project-template/
├── app/                    # Main application package
│   ├── __init__.py         # Package initializer
│   ├── main.py             # FastAPI application entry point
│   ├── api/                # API layer - HTTP endpoints and routing
│   ├── core/               # Core layer - Configuration and application setup
│   ├── middleware/         # Middleware layer - Custom middleware components
│   ├── schemas/            # Schemas layer - Pydantic models for data validation
│   └── services/           # Services layer - Business logic
├── tests/                  # Test suite
│   ├── api/                # API layer tests
│   ├── core/               # Core layer tests
│   ├── middleware/         # Middleware tests
│   ├── schemas/            # Schema tests
│   └── services/           # Service tests
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Docker image definition
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── .gitignore              # Git ignore rules
├── pytest.ini              # Pytest configuration
└── README.md               # This file
```

## Features

- **FastAPI**: Modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
- **Layered Architecture**: Separation of concerns with distinct layers for API, core, middleware, schemas, and services.
- **Docker Support**: Containerized application for easy deployment and scalability.
- **Environment Configuration**: Configuration management through environment variables.
- **Testing Framework**: Pytest integration for comprehensive testing.
- **Health Checks**: Built-in health check endpoint for monitoring.

## Prerequisites

- Python 3.7+
- Docker (optional, for containerized deployment)
- pip (Python package installer)

## Installation

### Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd project-template
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

### Using Docker

1. Build and run with Docker Compose:
   ```bash
   docker-compose up --build
   ```

2. The application will be available at `http://localhost:8001`

## Running the Application

For detailed instructions on running the application, see [RUN.md](RUN.md).

## Testing

Run the test suite using pytest:

```bash
python -m pytest
```

Or with verbose output:

```bash
python -m pytest -v
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
Contains business logic and service implementations.

## Docker Configuration

The template includes a multi-stage Dockerfile and docker-compose.yml for containerized deployment:

- Uses Python 3.13 Bookworm as base image
- Installs dependencies in a separate layer for better caching
- Exposes port 8001
- Includes health check configuration
- Uses environment variables for configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

Specify your license here.
