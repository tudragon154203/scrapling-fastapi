# Sprint 1 — Skeleton with Scrapling

Goal: establish a runnable FastAPI service skeleton that replaces Playwright with Scrapling for generic crawling, aligned with the legacy API summary while keeping the scope minimal.

Deliverables

- FastAPI app scaffold with `/health` and `POST /crawl`.
- Integration with `scrapling.fetchers.StealthyFetcher` for generic fetch.
- Pydantic-based settings loaded from `.env`.
- Dockerfile and Compose wired to use `${PORT}` consistently.
- Minimal request/response schemas with legacy field compatibility.

Key Endpoints

- `GET /health`: simple readiness check.
- `POST /crawl`: generic crawling using Scrapling.
  - Accepts new fields and legacy `x_*` fields:
    - `url` (required)
    - `wait_selector` | `x_wait_for_selector`
    - `timeout_ms` | `x_wait_time` (seconds)
    - `headless` | `x_force_headful`
    - `network_idle`

Code Map

- `app/main.py`: app factory, CORS, router registration.
- `app/api/routes.py`: health + crawl endpoints.
- `app/core/config.py`: centralized settings.
- `app/schemas/crawl.py`: request/response models.
- `app/services/crawler/generic.py`: Scrapling integration.

Run Locally

1. `pip install -r requirements.txt`
2. `python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

Run with Docker

- `docker-compose up --build`

Next Sprints (planned)

- Add specialized crawlers (e.g., AusPost, DPD) modeled after `demo/` techniques.
- Proxy pool and rotation support.
- Stealth health/metrics/diagnostics endpoints.
- Structured logging and tracing.
- Unit tests with dependency injection and service mocks.
