# Sprint 02 — Generic Crawl (Full Options)

This sprint delivers a generic crawl endpoint that supports the full options described for the legacy project, while aligning with the current Scrapling-based implementation.

Focus: Accept both new fields and legacy `x_*` fields, map them correctly to Scrapling's `StealthyFetcher.fetch`, and return consistent responses.

## API

- Endpoint: `POST /crawl`
- Request (new + legacy fields):
  - `url` (string, required): target URL.
  - `wait_selector` (string, optional): CSS selector to wait for.
  - `wait_selector_state` (string, optional): one of `visible|attached|hidden|detached` (default: `visible`).
  - `timeout_ms` (int, optional): overall operation timeout in milliseconds (default from settings).
  - `headless` (bool, optional): override default headless mode.
  - `network_idle` (bool, optional): wait for network idle before capture (default from settings).
  - Legacy compatibility:
    - `x_wait_for_selector` (string): alias for `wait_selector` if the new field is not provided.
    - `x_wait_time` (int, seconds): fixed delay before capturing HTML. Mapped to Scrapling's `wait` in milliseconds.
    - `x_force_headful` (bool): forces `headless=False` when `true`.
    - `x_force_user_data` (bool): accepted for compatibility but not used by Scrapling.

- Response:
  - `status`: `success` or `failure`.
  - `url`: echo of the requested URL.
  - `html`: string when `success`.
  - `message`: error details when `failure`.

## Environment Defaults

Loaded via settings in `app/core/config.py`:
- `default_headless`: default for headless (env `HEADLESS`, default: `true`).
- `default_network_idle`: default for network idle (env `NETWORK_IDLE`, default: `false`).
- `default_timeout_ms`: default timeout in ms (env `TIMEOUT_MS`, default: `20000`).

## Implementation

- Schema: `app/schemas/crawl.py`
  - Adds new fields with sane defaults and legacy `x_*` fields.

- Service: `app/services/crawler/generic.py`
  - Uses `scrapling.fetchers.StealthyFetcher.fetch` with:
    - `headless`, `network_idle`, `wait_selector`, `wait_selector_state`, `timeout`.
    - `wait` (ms) is derived from legacy `x_wait_time` seconds.
  - Legacy precedence:
    - `wait_selector = wait_selector or x_wait_for_selector`.
    - `x_force_headful=True` forces `headless=False`.
  - Returns `success` when underlying response has `status == 200`, otherwise `failure` with a message.

## TDD — Red → Green → Refactor

1) Red: Added failing service tests to verify correct mapping to `StealthyFetcher.fetch`:
   - `tests/services/test_generic_crawl.py`
   - Validates that `x_wait_time` maps to `wait` (ms), not `timeout`.
   - Checks defaults for `timeout`, `network_idle`, and legacy headful forcing.

2) Green: Implemented mapping and logic in `app/services/crawler/generic.py`:
   - Compute `timeout_ms` from request or defaults.
   - Compute `wait_ms` from `x_wait_time` seconds.
   - Pass both `timeout=...` and `wait=...` to `StealthyFetcher.fetch`.

3) Refactor: Minor cleanup and comments. All tests pass.

Test summary: `8 passed` (API + service tests).

## Usage Examples

Basic crawl with defaults:

```bash
curl -sS -X POST http://localhost:8000/crawl \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com"
  }'
```

Wait for selector (new field) with explicit timeout and headless override:

```bash
curl -sS -X POST http://localhost:8000/crawl \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com",
    "wait_selector": "#app",
    "wait_selector_state": "visible",
    "timeout_ms": 15000,
    "headless": true,
    "network_idle": true
  }'
```

Legacy compatibility (force headful, fixed wait seconds, legacy selector):

```bash
curl -sS -X POST http://localhost:8000/crawl \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com",
    "x_wait_for_selector": "#app",
    "x_wait_time": 7,
    "x_force_headful": true
  }'
```

## Notes

- `x_force_user_data` is accepted but not used because Scrapling (Camoufox-based) does not expose a persistent user data directory concept analogous to Playwright profiles. It is kept for request compatibility only.
- Next sprints can integrate retry and proxy strategies, stealth diagnostics, and metrics endpoints outlined in `docs/SUMMARY_OLD_PROJECT.md`.

