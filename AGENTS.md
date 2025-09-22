# Repository Guidelines

## Project Structure & Module Organization
- `app/` hosts the layered FastAPI service: `api/` for routers, `core/` for settings, `middleware/`, `schemas/`, and `services/` split into `browser/`, `crawler/`, `common/`, and `tiktok/`.
- `tests/` mirrors that structure with unit suites plus `integration/` scenarios; keep fixtures close to their targets.
- `docs/`, `specs/`, and `specify_src/` contain architecture notes and model prompts; update them when behavior changes.
- `memory/` stores persisted agent state; `scripts/run-brave-search.sh` and `.claude/` configs configure optional Brave MCP integration; store secrets in `.claude/mcp.env` or `.env`.

## Build, Test, and Development Commands
- `python -m venv .venv` then `.venv/Scripts/activate` (or `source .venv/bin/activate`) to create and enter an isolated environment.
- `pip install -r requirements.txt` for runtime deps; add `-r requirements-test.txt` before running suites locally.
- `python -m uvicorn app.main:app --host 0.0.0.0 --port 5681 --reload` serves the API with hot reload.
- `python -m pytest` executes the full suite in parallel (`-n auto` is set); use `python -m pytest -n 0` for deterministic debugging and `python -m pytest -m integration` for browser-backed scenarios.
- `pre-commit run --all-files` mirrors CI formatting via aggressive `autopep8`.

## Coding Style & Naming Conventions
- Target Python 3.11 semantics with 4-space indents, type hints, and descriptive docstrings for public services.
- Keep lines <=140 chars (enforced by `black`, `isort`, and `flake8`); import order follows `isort`'s Black profile.
- Name modules and files with snake_case; FastAPI routers live in `<feature>_router.py`, Pydantic models in `<Feature>Schema`.
- Service classes should end with `Service`; async helpers prefixed `async_`; prefer explicit enums over magic strings.

## Testing Guidelines
- Place unit tests beside the feature they cover (e.g., `tests/services/crawler/test_retry.py`).
- Adhere to `pytest.ini` patterns: files `test_*.py`, classes `Test*`, functions `test_*`.
- Mark network or browser-dependent work with `@pytest.mark.integration`; use `@pytest.mark.asyncio` for coroutine tests.
- Capture new fixtures in `tests/conftest.py` and prefer factories over hard-coded literals.

## Commit & Pull Request Guidelines
- Follow the existing history by using concise, imperative subjects; Conventional-style prefixes (`feat:`, `fix:`, `docs:`) are encouraged for clarity.
- Reference issue IDs or spec links in the body, summarize behavioral impacts, and note any config or environment changes.
- Before opening a PR, run lint + tests, update docs (`docs/`, `RUN.md`, `AGENTS.md`), and include API samples or screenshots when behavior changes surface endpoints.
- PR descriptions should list validation steps and highlight integration impacts to assist reviewers.
