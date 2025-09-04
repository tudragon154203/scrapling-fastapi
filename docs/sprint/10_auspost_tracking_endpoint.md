# Sprint 10 - AusPost Tracking Endpoint (/crawl/auspost)

Goal: deliver a specialized AusPost tracking endpoint that accepts a tracking code and returns the resulting details page HTML. The behavior mimics the demo in `demo/scrapling_aupost_test.py`, implemented on top of our existing Scrapling (Camoufox) pipeline, with the same legacy compatibility flags used by DPD.

## Context

- The demo (`demo/scrapling_aupost_test.py`) shows the reliable flow for AusPost:
  - Open the public search page `https://auspost.com.au/mypost/track/search`.
  - Fill the tracking number, submit using the Search/Track button (or Enter key).
  - Handle the "Verifying the device..." interstitial if it appears.
  - Wait for navigation to details URL `**/mypost/track/details/**` and the header selector `h3#trackingPanelHeading` to appear.
  - Save the resulting HTML (in the demo, written to disk; in our API we return it in JSON).
- Our codebase already supports page actions via `crawl_single_attempt` / `execute_crawl_with_retries(page_action=...)` and option resolution via `_resolve_effective_options`.
- We have a DPD endpoint that uses `tracking_code` as the primary field; AusPost must follow the same request/response shape.

## API

- Endpoint: `POST /crawl/auspost`
- Request (JSON):
  - `tracking_code` (string, required): AusPost tracking code. Trimmed, must be non-empty.
  - `x_force_user_data` (bool, optional, default `false`): enable Camoufox persistent user data if configured.
  - `x_force_headful` (bool, optional, default `false`): forces headful mode on Windows; ignored on Linux/Docker.
- Response (JSON):
  - `status`: `success | failure`.
  - `tracking_code`: echo of input.
  - `html`: HTML string when `success`.
  - `message`: error details when `failure`.

Notes

- Request validation: `tracking_code` must be a non-empty string after trimming (same validator as DPD).
- Headfulness and user-data semantics mirror DPD and the generic endpoint.

## Behavior

Page flow (mimics the demo):

1) Start URL: `https://auspost.com.au/mypost/track/search`.
2) Page action procedure (Playwright page object):
   - Wait for input: `input[data-testid="SearchBarInput"]` (first).
   - Click and `fill(tracking_code)`.
   - Prefer clicking `button[data-testid="SearchButton"]` (first); if not visible, press Enter.
   - Handle interstitial: try to detect `text=Verifying the device` and wait until it becomes hidden; then wait for `domcontentloaded` and (best-effort) `networkidle`.
   - Wait for URL to match pattern `**/mypost/track/details/**` (15s timeout). If still on search page, retry clicking.
   - Wait for details header selector to appear: `h3#trackingPanelHeading` (15s timeout as a safety on top of engine wait).

Fetch options:

- `wait_selector`: `h3#trackingPanelHeading`.
- `wait_selector_state`: `visible`.
- `network_idle`: `true` (to stabilize dynamic details page), unless settings dictate otherwise.
- `timeout_ms`: 30000 by default (can use `default_timeout_ms` from settings if preferred).
- `wait`: a small fixed delay (e.g., 1200 ms) to help with late content, consistent with the demo.
- `additional_args` should include `disable_coop: true` (helps some anti-bot checks/Turnstile iframes). Use settings flag if one exists (`camoufox_disable_coop`).
- Prefer to enable Cloudflare solving when supported by `StealthyFetcher.fetch` (already capability-gated in utils).
- GeoIP: attempt with `geoip=True` first; if the MaxMind DB is missing or invalid (e.g., `InvalidDatabaseError` or mentions of `GeoLite2-City.mmdb`), retry without geoip. Use the same capability detection pattern we use elsewhere.

Success/Failure semantics:

- Success when the upstream fetch returns HTTP 200 and the HTML length is above `min_html_content_length` (same thresholding as generic executor). Return `status=success` and the `html`.
- Failure if non-200, exceptions, or HTML is too short; return `status=failure` with a meaningful `message`.

## Design Overview

- New schema models: `app/schemas/auspost.py`
  - `AuspostCrawlRequest`: `tracking_code`, `x_force_user_data`, `x_force_headful` with the same validation as DPD for `tracking_code`.
  - `AuspostCrawlResponse`: `status`, `tracking_code`, `html?`, `message?`.
- New service module: `app/services/crawler/auspost.py`
  - Expose `crawl_auspost(request: AuspostCrawlRequest) -> AuspostCrawlResponse`.
  - Build a generic `CrawlRequest` targeting the search URL and pass a `page_action` that performs the demo’s form automation and waits for the details content.
  - Use the same retry/single strategy as generic/DPD: `execute_crawl_with_retries` when `max_retries > 1`, else `crawl_single_attempt`, both with `page_action`.
  - Wire `additional_args` and capability-detected options via our existing utils (`_detect_fetch_capabilities`, `_compose_fetch_kwargs`, `_build_camoufox_args`).
- API route: `app/api/routes.py`
  - Add `POST /crawl/auspost` endpoint that validates request and delegates to `crawl_auspost`.

## Configuration

Leverage existing settings from `app/core/config.py`:
- `max_retries`, `retry_backoff_*`, `retry_jitter_ms`
- `proxy_list_file_path`, `private_proxy_url`, `proxy_rotation_mode`
- `default_headless`, `default_timeout_ms`, `default_network_idle`
- `camoufox_user_data_dir` (for `x_force_user_data`)
- `camoufox_disable_coop` (set true to pass `disable_coop` in `additional_args`)
- `camoufox_geoip` (attempt geoip; fallback to no-geoip on error)
- `min_html_content_length` and `http_fallback_on_failure` (fallback likely won’t help with interactive flows but remains capability-gated by the executors)

## Validation & Errors

- 400 on request validation errors (missing/blank `tracking_code`).
- 200 with `status=failure` and `message` when upstream fetch fails or HTML is below the threshold; echo `tracking_code`.
- Log headless decision reasoning and whether `x_force_headful` was honored (Windows) or ignored (Linux/Docker), mirroring DPD.

## Testing

Schema tests:
- `AuspostCrawlRequest` requires non-empty `tracking_code`.
- Defaults: `x_force_user_data=false`, `x_force_headful=false`.

Service unit tests (mock `StealthyFetcher.fetch`):
- Verifies that a `page_action` is supplied and invoked with the expected selector interactions:
  - Fill input `input[data-testid="SearchBarInput"]` with the provided `tracking_code`.
  - Click `button[data-testid="SearchButton"]` or press Enter fallback.
  - Attempts to handle the "Verifying the device" interstitial and waits for details URL and selector.
- On 200 + sufficiently long HTML, returns `status=success` with `html`.
- On non-200 or exception, returns `status=failure` with `message`.
- Honors `x_force_headful` semantics (Windows only) and `x_force_user_data` when configured.
- If geoip attempt raises a DB error, retries once with geoip disabled.

API tests:
- `POST /crawl/auspost` happy path returns `status=success`, echoes `tracking_code`, and contains HTML.
- Validation: missing/blank `tracking_code` yields 400.

Manual check (optional, mirrors the demo):
- Use tracking code `36LB4503170001000930309` to confirm the flow reaches the details page and returns HTML containing the header `h3#trackingPanelHeading`.

## Acceptance Criteria

- `POST /crawl/auspost` exists and accepts the request schema above.
- For a mocked successful fetch, returns `status=success`, includes `tracking_code`, and `html`.
- For mocked failure/non-200, returns `status=failure` and a `message`.
- Implements the page-action flow equivalent to `demo/scrapling_aupost_test.py` (selectors, URL wait, interstitial handling).
- Honors `x_force_user_data` and `x_force_headful` semantics consistent with DPD.
- Reuses retry/proxy behavior and option resolution from the generic executors.

## Examples

Basic request:

```bash
curl -sS -X POST http://localhost:8000/crawl/auspost \
  -H 'Content-Type: application/json' \
  -d '{
    "tracking_code": "36LB4503170001000930309"
  }'
```

With legacy flags:

```bash
curl -sS -X POST http://localhost:8000/crawl/auspost \
  -H 'Content-Type: application/json' \
  -d '{
    "tracking_code": "36LB4503170001000930309",
    "x_force_user_data": true,
    "x_force_headful": true
  }'
```

## References

- Demo script: `demo/scrapling_aupost_test.py`
- Generic executors and utils: `app/services/crawler/executors/*`, `app/services/crawler/utils/*`
- DPD endpoint for schema/response shape: `docs/sprint/07_dpd_tracking_endpoint.md`, `app/schemas/dpd.py`, `app/services/crawler/dpd.py`
