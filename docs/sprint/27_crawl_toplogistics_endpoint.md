# Sprint 27 - TopLogistics Tracking Endpoint (/crawl/toplogistics)

Goal: deliver a dedicated TopLogistics tracking endpoint that normalizes either a tracking code or search URL into the canonical tracking page, then reuses our Scrapling (Camoufox) crawl pipeline with the same compatibility flags exposed by the generic `/crawl` route. Required coverage: unit tests (schemas/services/api) and a happy-path integration test.

## Context

- The working demo (`demo/crawl_toplogistics.py`) already demonstrates the target flow:
  - Accepts a TopLogistics search URL (e.g. `https://toplogistics.com.au/?s=33EVH0319358`).
  - Extracts the tracking number from the `s` query parameter.
  - Converts it into the tracking page URL `https://imshk.toplogistics.com.au/customerService/imparcelTracking?s=<code>`.
  - Issues a crawl request with `network_idle=True`, a 25s timeout, and legacy overrides for headful/user-data.
- `/crawl/dpd` and `/crawl/auspost` define the expected schema/response shape for courier-specific endpoints. TopLogistics should adopt the same status+html contract so clients can swap carriers without branching logic.
- Requirements emphasize reusing the layered architecture:
  - Schema validation stays under `app/schemas/`.
  - Business logic lives in `app/services/crawler/toplogistics.py`.
  - Routing stays in `app/api/`.

## API

- Endpoint: `POST /crawl/toplogistics`
- Request (JSON):
  - `tracking_code` (string, required): Accepts either a bare tracking code (`33EVH0319358`) or a search URL containing `?s=<code>`. Trim and validate non-empty after normalization.
  - `force_user_data` (bool, optional, default `false`): preserves legacy user-data override semantics used by `/crawl`.
  - `force_headful` (bool, optional, default `false`): forces headful mode when supported (Windows); ignored elsewhere.
- Response (JSON) — reuse `/crawl/dpd` & `/crawl/auspost` contract:
  - `status`: `success | failure`.
  - `tracking_code`: normalized code (echo).
  - `html`: populated when `status=success`.
  - `message`: populated when `status=failure`.

Notes

- Preserve backwards-compatible flag handling: request keys stay `force_user_data` / `force_headful`, matching the demo and generic endpoint.
- Return canonical tracking URL in logs/diagnostics but not in the public response unless we standardize across endpoints.

## Behavior

1. Normalize input:
   - If `tracking_code` looks like a URL, extract the `s` parameter (case-insensitive).
   - If no `s` parameter exists, treat the entire string as the tracking code.
   - Validate the resulting code (alphanumeric/uppercase per observed format, but keep validation relaxed to avoid false negatives).
2. Build the tracking page URL: `https://imshk.toplogistics.com.au/customerService/imparcelTracking?s=<code>`.
3. Compose a `CrawlRequest` mirroring the demo defaults:
   - `url`: canonical tracking URL.
   - `network_idle=True`.
   - `timeout_seconds=25` (align with demo; allow overriding via config defaults if desired).
   - `force_headful` / `force_user_data` resolved through existing helpers.
   - Supply a modern desktop `User-Agent` header (reuse generic default if one exists; fallback to the demo UA string).
4. Execute via the generic crawler pipeline:
   - Prefer `execute_crawl_with_retries` when retries > 1, else `crawl_single_attempt`.
   - Reuse proxy, geoip, and retry behavior identical to `/crawl/dpd`.
5. Success path: HTML length above `min_html_content_length` ⇒ return `status=success` + HTML.
6. Failure path: non-200 responses, exceptions, or short HTML ⇒ return `status=failure` + `message`.
7. Log the normalized code, canonical URL, retry attempts, and headful decision for observability.

## Design Overview

- Schemas (`app/schemas/toplogistics.py`):
  - `TopLogisticsCrawlRequest`: fields `tracking_code`, `force_user_data`, `force_headful`; Pydantic validator handles code/url normalization.
  - `TopLogisticsCrawlResponse`: matches DPD/AusPost shape.
- Services (`app/services/crawler/toplogistics.py`):
  - `build_tracking_url(code: str) -> str` helper.
  - `extract_tracking_code(raw: str) -> str` helper shared with schema validator (testable in isolation).
  - `crawl_toplogistics(request: TopLogisticsCrawlRequest) -> TopLogisticsCrawlResponse` that prepares the `CrawlRequest`, invokes the generic executor, and wraps the response.
- API (`app/api/...`):
  - New router entry `POST /crawl/toplogistics` delegating to the service.
  - Ensure routers follow existing grouping (likely `app/api/crawl_router.py` or similar file).
- No changes to middleware/core layers required; reuse configuration from existing crawler endpoints.

## Configuration

Reuse existing settings exposed via `app/core/config.py`:
- `max_retries`, `retry_backoff_*`, `retry_jitter_ms`
- `proxy_list_file_path`, `private_proxy_url`, `proxy_rotation_mode`
- `default_headless`, `default_timeout_ms` (permit overriding the hard-coded 25s if the defaults differ)
- `camoufox_user_data_dir`, `camoufox_geoip`, `camoufox_disable_coop`
- `min_html_content_length`, `http_fallback_on_failure`

If a distinct timeout or network-idle policy is required later, expose a `TOPLOGISTICS_TIMEOUT_MS` or similar env var through `Config`.

## Validation & Errors

- 400 when `tracking_code` cannot be normalized (empty string after trimming/extraction).
- 200 with `status=failure` when upstream crawl fails, times out, or returns short HTML. Include normalized `tracking_code` and a descriptive `message`.
- Log (at info/debug) the raw input and normalized code for troubleshooting; avoid storing full URLs in production metrics if they contain sensitive query params.

## Testing

Schema tests (`tests/schemas/test_toplogistics.py`):
- Accepts bare code and returns uppercase/trimmed value.
- Accepts search URL and extracts the `s` parameter.
- Rejects blank strings or URLs without `s`.
- Defaults `force_user_data=False`, `force_headful=False`.

Service tests (`tests/services/crawler/test_toplogistics.py`):
- Mock `StealthyFetcher.fetch` to assert the canonical URL and headers.
- Validate retry invocation when failures occur.
- Simulate 200 + long HTML ⇒ `status=success`.
- Simulate non-200/exception ⇒ `status=failure` with message.
- Assert headful/user-data flags flow through the option resolver.

API tests (`tests/api/test_crawl_toplogistics.py`):
- Happy path echoes normalized `tracking_code` and returns HTML on mocked success.
- Input normalization works for full URL payload.
- Missing/blank code yields 400.
- Service failure propagates `status=failure`.

Integration test (happy path):
- Exercise the flow using the demo tracking code `33EVH0319358` (or a fixture-backed HTML), ensuring the response HTML contains recognizable order metadata and is tracked as an integration scenario in the test suite.

## Acceptance Criteria

- FR-1: Unit tests cover schema normalization, service execution (success/failure paths), and API response handling.
- FR-2: A happy-path integration test exercises the endpoint with a real TopLogistics tracking code or fixture-backed HTML (marked `@pytest.mark.integration`).
- `POST /crawl/toplogistics` is implemented with the request/response schema above.
- Normalizes both bare codes and search URLs into the canonical tracking URL.
- Reuses retry/proxy/headless logic consistent with `/crawl/dpd` and `/crawl/auspost`.
- Returns HTML on success and descriptive failure messages otherwise.
- All new unit and integration tests pass in CI.
- Documentation updated (this PRD) with references and rationale.

## Examples

Basic request with bare code:

```bash
curl -sS -X POST http://localhost:5681/crawl/toplogistics \
  -H "Content-Type: application/json" \
  -d '{
    "tracking_code": "33EVH0319358"
  }'
```

Request using a search URL and forcing headful/user-data:

```bash
curl -sS -X POST http://localhost:5681/crawl/toplogistics \
  -H "Content-Type: application/json" \
  -d '{
    "tracking_code": "https://toplogistics.com.au/?s=33EVH0319358",
    "force_user_data": true,
    "force_headful": true
  }'
```

## References

- Demo: `demo/crawl_toplogistics.py`
- Existing endpoints: `docs/sprint/07_dpd_tracking_endpoint.md`, `docs/sprint/10_auspost_tracking_endpoint.md`
- Generic crawler utilities: `app/services/crawler/generic.py`, `app/services/crawler/executors/*`, `app/services/crawler/utils/*`
