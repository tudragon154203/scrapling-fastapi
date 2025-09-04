# Sprint 07 - DPD Tracking Endpoint (/crawl/dpd)

Goal: deliver a specialized DPD tracking endpoint that accepts a tracking code and returns the resulting tracking page HTML, while preserving legacy compatibility flags and reusing the current Scrapling-based crawl pipeline.

## Context

- The legacy Playwright-based service exposed `POST /crawl/dpd` with form-filling logic and headless/headful controls (see `docs/SUMMARY_OLD_PROJECT.md`).
- Our current stack uses Scrapling (Camoufox) and already supports:
  - Retry + proxy strategy
  - Minimal user data persistence (`x_force_user_data`)
  - Headless override semantics (via `x_force_headful` in the generic endpoint)
- DPD requires either:
  - A query-able tracking endpoint (preferred), or
  - Interactive form steps (legacy approach)

This sprint implements a pragmatic Phase 1 using a direct tracking URL when available and reuses our robust fetch path. A later phase can extend to interactive steps if/when we add action APIs beyond straight fetch.

## API

- Endpoint: `POST /crawl/dpd`
- Request (JSON):
  - `tracking_code` (string, required): DPD tracking code.
  - `x_force_user_data` (bool, optional, default `false`): enable Camoufox persistent user data if configured.
  - `x_force_headful` (bool, optional, default `false`): forces headful mode on Windows; ignored on Linux/Docker.
- Response (JSON):
  - `status`: `success | failure`.
  - `tracking_code`: echo of input.
  - `html`: HTML string when `success`.
  - `message`: error details when `failure`.

Notes

- Request validation: `tracking_code` must be a non-empty string after trimming.
- Headfulness semantics mirror the legacy behavior described in `docs/SUMMARY_OLD_PROJECT.md`.

## Configuration

Leverage existing settings in `app/core/config.py` (already used by `/crawl`):
- `max_retries`, `retry_backoff_*`, `retry_jitter_ms`
- `proxy_list_file_path`, `private_proxy_url`, `proxy_rotation_mode`
- `default_headless` (via env `HEADLESS`)
- `default_timeout_ms` (via env `TIMEOUT_MS`)
- `camoufox_user_data_dir` (via env `CAMOUFOX_USER_DATA_DIR`)

Add one DPD constant for clarity in the implementation:
- `DPD_URL` (module-level): canonical tracking URL base we target in Phase 1
  - Use `https://tracking.dpd.de/parcelstatus` as the default base (legacy references also include `https://my.dpd.de/myParcel.aspx`).
  - Implementation will form a query URL using the tracking code when supported, e.g. `?query=<code>`.
  - Keep the query key configurable in code to allow quick adjustments if DPD changes their parameter name.

## Behavior

- Build a DPD tracking URL from the tracking code using the configured base and query key.
- Reuse the same fetch pipeline as `/crawl`:
  - Compute headless from defaults with legacy override: `x_force_headful=true` => `headless=false` (Windows-only honor).
  - Apply `x_force_user_data` when env is configured (no error if unsupported).
  - Use retry + proxy strategy identical to the generic executor.
- Success criteria: upstream fetch returns `status == 200` and HTML length is reasonable (> 0). Return `success` with the HTML.
- Failure: return `failure` with a meaningful message (status code or exception class+message).

## Design Overview

- New schema models: `app/schemas/dpd.py`
  - `DPDCrawlRequest`: `tracking_code`, `x_force_user_data`, `x_force_headful`.
  - `DPDCrawlResponse`: `status`, `tracking_code`, `html?`, `message?`.
- New service module: `app/services/crawler/dpd.py`
  - Expose `crawl_dpd(request: DPDCrawlRequest) -> DPDCrawlResponse`.
  - Internal helpers to construct URL from code and wire fetch through our existing single-attempt or retry executor style (shared util functions from generic executors and utils).
  - Define `DPD_URL` and a simple query builder (e.g., `build_dpd_url(code: str) -> str`).
- API route: `app/api/routes.py`
  - Add `POST /crawl/dpd` endpoint that validates request and delegates to the DPD service.

Implementation detail

- DPD endpoint should not fork a new network path; it should reuse `StealthyFetcher.fetch` and the same composition of kwargs already present in `executors/single.py` and `executors/retry.py`.
- If Scrapling’s version lacks a parameter we intend to pass (proxy/user_data/etc.), log a single warning and proceed without it (same pattern as generic).

## Phased Delivery

- Phase 1 (this sprint):
  - Implement query-based tracking fetch using `DPD_URL` with a configurable query key (default `query`).
  - No page actions. The result is the HTML of the tracking page for that code.
- Phase 2 (future):
  - Add interactive steps (form fill, button click, conditional continue) once we introduce an action API on top of Scrapling/Camoufox (or integrate an alternative headless action layer) — modeled after legacy selectors.

## Validation & Errors

- 400 when `tracking_code` is missing/blank.
- 200 response with `status=failure` when upstream fetch returns non-200 or raises (same style as generic endpoint), including a helpful `message`.
- Log headless decision reasoning and whether `x_force_headful` was honored or ignored by platform.

## Testing

- Schema tests:
  - `DPDCrawlRequest` requires non-empty `tracking_code`.
  - Defaults: `x_force_user_data=false`, `x_force_headful=false`.
- Service unit tests (mock `StealthyFetcher.fetch`):
  - Builds a tracking URL including the code and hits it once in single-attempt mode.
  - On success (status 200 + html), returns `success` with html.
  - On non-200 or exception, returns `failure` with message.
  - When `x_force_headful=true` on Windows, ensure `headless=false` passed; on Linux/Docker, request is ignored (assert via decision helper or logged reason when accessible).
  - When `x_force_user_data=true` and env is set, verify the appropriate user-data arg is attempted if supported.
- API tests:
  - `POST /crawl/dpd` happy path returns `status=success`, echoes `tracking_code`.
  - Validation: missing/blank `tracking_code` yields 400.
  - Propagates service failure as 500 only if we follow the legacy hard-fail pattern; otherwise returns 200 with `status=failure` (choose one and document — see Acceptance Criteria).

## Acceptance Criteria

- `POST /crawl/dpd` exists and accepts the request schema above.
- For a mocked successful fetch, returns `status=success`, includes `tracking_code`, and `html`.
- For mocked failure/non-200, returns `status=failure` and a `message`.
- Honors `x_force_user_data` per existing generic behavior.
- Honors `x_force_headful` semantics:
  - Windows: forces headful (best-effort subject to library support), logs decision.
  - Linux/Docker: logs and ignores, no crash.
- Endpoint reuses the same retry/proxy behavior configured for the generic crawler.
- Documentation includes examples and constraints.

## Examples

Basic request:

```bash
curl -sS -X POST http://localhost:8000/crawl/dpd \
  -H 'Content-Type: application/json' \
  -d '{
    "tracking_code": "12345678901234"
  }'
```

With legacy flags:

```bash
curl -sS -X POST http://localhost:8000/crawl/dpd \
  -H 'Content-Type: application/json' \
  -d '{
    "tracking_code": "12345678901234",
    "x_force_user_data": true,
    "x_force_headful": true
  }'
```

## References

- Legacy endpoint behavior and selectors: `docs/SRC_CODE_OLD_PROJECT.md` (see `app/api/dpd.py`, `app/schemas/dpd.py`, `app/services/crawler/dpd.py`).
- Summary and API shapes: `docs/SUMMARY_OLD_PROJECT.md`.
