# AGENTS.md

AI Agent Development Guidelines for Scrapling FastAPI Project

## Core Development Principles (CONSTITUTION MANDATES)

### 1. Layered Architecture (MANDATORY)
- **Structure**: API/Core/Middleware/Schemas/Services layers
- **Services Organization**: By domain specificity (browser, common, crawler, tiktok)
- **Separation**: No mixing of layers - strict separation required
- **Location**: All spec-related code in project root, NOT in `.specify/` directory

### 2. Technology Stack
- **Framework**: FastAPI with automatic OpenAPI documentation
- **Target**: Python 3.10.8 on Windows
- **Validation**: Pydantic 2.9 with Python 3.13 compatibility
- **Type Hints**: Required throughout application
- **Browser Automation**: Scrapling/Camoufox by default

### 3. Test-Driven Development (NON-NEGOTIABLE)
- **Process**: Tests written → Implementation → Tests pass → Refactor
- **Cycle**: Red-Green-Refactor strictly enforced
- **Tools**: pytest with pytest-xdist for parallel execution
- **Integration Tests**: Minimal, focused on critical paths, marked with `pytest.mark.integration`
- **Structure**: Must follow established test directory structure

### 4. Configuration Management
- **Method**: Environment variables via .env files
- **Tool**: Pydantic-settings for type-safe configuration
- **Rule**: No hardcoded configuration values
- **Environments**: Clear development vs production separation

### 5. Schema Consistency (API Contracts)
- **Reference**: All new schemas must refer to existing app/schemas/*.py patterns
- **Conventions**: Follow established field naming, validation, response structures
- **Documentation**: Any divergence must be justified and documented

## Security & Anti-Detection Requirements

- **Fingerprinting**: BrowserForge integration mandatory
- **Sessions**: User session persistence and management with master/clone architecture for Chromium profiles
- **Proxy**: Support for distributed crawling
- **Detection**: Rate limiting and bot detection avoidance
- **Compliance**: GDPR considerations for data processing

## Quality Gates

- **Code Quality**: Must pass `flake8` linting for `app/` and `tests/` directories
- **Test Coverage**: Required for all PRs
- **Reviews**: Required for schema changes and security features
- **Performance**: Benchmarks required for scraping operations
- **Cleanup**: Remove all intermediate files/folders post-implementation

## Development Commands & Patterns

### Environment Setup
- **DO NOT** create or use .venv virtual environments
- Use the system's direct Python interpreter
- `pip install -r requirements.txt` for runtime deps; add `-r requirements-test.txt` for testing

### Running the Application
- **Development**: `python -m uvicorn app.main:app --host 0.0.0.0 --port 5681 --reload`
- **Production**: `pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 5681" --name scrapling-api`
- **Port**: 5681 by default
- **Endpoints**: Health at `/health`, API docs at `/docs`

### Testing
- `python -m pytest` executes the full suite in parallel (`-n auto` is set)
- `python -m pytest -n 0` for deterministic debugging
- `python -m pytest -m unit` for unit tests only (mocked, fast)
- `python -m pytest -m integration` for browser-backed scenarios (requires real network/browser)
- `pre-commit run --all-files` mirrors CI formatting

## Project Structure & Module Organization

### Application Structure (app/)
- **api/**: HTTP routers and endpoints
- **core/**: Configuration and settings management
- **middleware/**: Custom middleware components
- **schemas/**: Pydantic models for request/response validation
- **services/**: Business logic organized by domain:
  - **browser/**: Browser automation utilities
  - **crawler/**: Web scraping services (generic, dpd)
  - **common/**: Abstract browsing executors
  - **tiktok/**: TikTok-specific session management
- **main.py**: FastAPI application factory

### Testing Structure (tests/)
- **unit/**: Unit tests (mocked, no network/browser dependencies)
  - **api/**: API endpoint unit tests
  - **core/**: Configuration, logging unit tests
  - **schemas/**: Pydantic schema validation tests
  - **services/**: Business logic unit tests
    - **browser/**: Browser automation unit tests
    - **common/**: Common service unit tests
    - **crawler/**: Web scraping service unit tests
    - **proxy/**: Proxy rotation unit tests
    - **tiktok/**: TikTok service unit tests
  - **chromium/**: Chromium-specific unit tests
  - **crawl/**: Crawling unit tests
  - **tiktok/**: TikTok unit tests
- **integration/**: End-to-end scenarios requiring real browser/network
  - **api/**: API integration tests
  - **chromium/**: Browser automation integration tests
  - **crawl/**: Crawling integration tests
  - **services/**: Service integration tests
  - **tiktok/**: TikTok integration tests
- **conftest.py**: Shared test fixtures and factories

### Test Markers & Execution
- **Unit tests**: `pytestmark = [pytest.mark.unit]` - Use mocks, no network/browser dependencies
- **Integration tests**: `pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("require_scrapling")]` - Real network/browser operations
- **Execution**: `python -m pytest -m unit` for unit tests, `python -m pytest -m integration` for integration tests

### Additional Directories
- **docs/**: Architecture documentation
- **specs/**: Feature specifications
- **specify_src/**: Main source code for spec-related functionality
- **memory/**: Persisted agent state
- **scripts/**: Utility scripts (e.g., Brave MCP integration)
- **.claude/**: Claude Code configuration and secrets

## Coding Style & Naming Conventions

- Target Python 3.10.8+ semantics with 4-space indents, type hints, and descriptive docstrings for public services
- Keep lines <=140 chars (enforced by `black`, `isort`, and `flake8`); import order follows `isort`'s Black profile
- Name modules and files with snake_case; FastAPI routers live in `<feature>_router.py`, Pydantic models in `<Feature>Schema`
- Service classes should end with `Service`; async helpers prefixed `async_`; prefer explicit enums over magic strings

## Testing Guidelines

- **Unit Tests**: Place in `tests/unit/` organized by feature (e.g., `tests/unit/services/crawler/test_retry.py`)
- **Integration Tests**: Place in `tests/integration/` for real network/browser scenarios
- **Markers**: Always include proper pytest markers at file level:
  - Unit tests: `pytestmark = [pytest.mark.unit]`
  - Integration tests: `pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("require_scrapling")]`
- **Patterns**: Follow `pytest.ini` patterns: files `test_*.py`, classes `Test*`, functions `test_*`
- **Async**: Use `@pytest.mark.asyncio` for coroutine tests
- **Fixtures**: Capture new fixtures in `tests/conftest.py` and prefer factories over hard-coded literals
- **Dependencies**: Unit tests should never depend on external services or real browsers

## Commit & Pull Request Guidelines

- Follow the existing history by using concise, imperative subjects; Conventional-style prefixes (`feat:`, `fix:`, `docs:`) are encouraged for clarity
- Reference issue IDs or spec links in the body, summarize behavioral impacts, and note any config or environment changes
- Before opening a PR, run lint + tests, update docs (`docs/`, `RUN.md`, `AGENTS.md`), and include API samples or screenshots when behavior changes surface endpoints
- PR descriptions should list validation steps and highlight integration impacts to assist reviewers

## Critical Rules for Agents

1. **NEVER** place implementation code in `.specify/` directory
2. **ALWAYS** write tests before implementation
3. **MUST** follow layered architecture strictly
4. **REQUIRED** to use type hints throughout
5. **MANDATORY** schema consistency with existing patterns
6. **ESSENTIAL** to clean up intermediate files after implementation
7. **FORBIDDEN** to create or use .venv virtual environments - use system Python directly

## Governance

- **Constitution**: Supreme governance document (Version 1.4.2)
- **Amendments**: Require documentation and migration planning
- **Versioning**: Semantic versioning with impact assessment
- **Reference**: Use GEMINI.md for runtime development guidance

## Backwards Compatibility

- **Policy**: NO NEED for backwards compatibility
- **Breaking Changes**: Allowed without migration requirements
- **Focus**: Clean architecture and implementation over legacy support

**Last Updated**: 2025-10-10 | **Constitution Version**: 1.4.2
