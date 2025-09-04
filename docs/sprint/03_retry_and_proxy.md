# Sprint 03 - Retry and Proxy Strategy

Goal: add resilient retry capability and a progressive proxy strategy to the generic crawler so transient failures and soft blocks don’t immediately fail requests.

## Problem Statement

- No retry wrapper around `StealthyFetcher.fetch` in `app/services/crawler/generic.py`.
- No retry-related settings in `app/core/config.py`.
- No proxy rotation or proxy fallbacks.
- Single-attempt behavior makes the service fragile vs. timeouts, 429/5xx, and intermittent network issues.

## Objectives

- Implement a retry wrapper around the current fetch call with configurable attempts and backoff.
- Add a progressive proxy strategy: direct -> public proxies -> private proxy -> direct (final fallback).
- Centralize settings for retries and proxies in `app/core/config.py` with env overrides.
- Keep API and response schema stable; optionally include debug metadata behind a flag later.

## Deliverables

- Config additions (env + settings) with defaults and documentation.
- Retry execution helper integrated into `crawl_generic`.
- Proxy source + rotation mechanism (file-based public proxy list, single private proxy URL).
- Unit tests for retry/backoff flow and strategy order; integration test to validate behavior toggles.
- Sprint notes in this doc and updates to prior docs where helpful.

## Configuration

Add the following settings to `app/core/config.py` (env names in parentheses) with safe defaults:

- max_retries (`MAX_RETRIES`): int, default `3`.
- retry_backoff_base_ms (`RETRY_BACKOFF_BASE_MS`): int, default `500`.
- retry_backoff_max_ms (`RETRY_BACKOFF_MAX_MS`): int, default `5_000`.
- retry_jitter_ms (`RETRY_JITTER_MS`): int, default `250`.
- proxy_list_file_path (`PROXY_LIST_FILE_PATH`): str | None, default `None`.
- private_proxy_url (`PRIVATE_PROXY_URL`): str | None, default `None`.
- proxy_rotation_mode (`PROXY_ROTATION_MODE`): `sequential|random`, default `sequential`.

Notes:
- Backoff uses exponential growth capped at `retry_backoff_max_ms`, plus jitter.
- If no proxies are configured, the strategy reduces to direct-only with retries.

## Design Overview

- Where: augment `app/services/crawler/generic.py`.
- How: introduce an internal helper `execute_crawl_with_retries(payload)` used by `crawl_generic`.
- Strategy order per attempt:
  1) Direct connection.
  2) Public proxy rotation (if configured) across remaining attempts.
  3) Private proxy (if configured) for the penultimate attempt.
  4) Final direct attempt as a clean fallback.
- Failure conditions that trigger retry:
  - Exceptions from `StealthyFetcher.fetch` (timeouts, connection errors, etc.).
  - Non-200 statuses (e.g., 429, 5xx). Treat as retryable unless out of attempts.

Implementation detail re: proxies:
- If `StealthyFetcher.fetch` exposes a proxy parameter, pass the selected proxy URL. If not, implement a minimal ProxyAdapter layer so we can extend later without changing call sites. Initial scope focuses on the retry wrapper; proxy arg wiring is added in a small, isolated section to be enabled when the library supports it.

## Implementation Plan

- Update `Settings` in `app/core/config.py` with new fields and env bindings.
- Add file loader for public proxies in `app/services/crawler/generic.py` (simple `readlines`, strip, ignore comments/empties).
- Implement `execute_crawl_with_retries(payload)`:
  - Build attempt plan (list of connection modes: direct and proxy candidates) based on configuration and max attempts.
  - For `attempt_idx` in `range(max_retries)`:
    - Select connection mode (direct / proxy URL).
    - Compute backoff for next attempt: `delay_ms = min(max_ms, base_ms * 2**attempt_idx) + jitter`.
    - Call `StealthyFetcher.fetch` with the same arguments as today; if proxy support is available, include the selected proxy.
    - Success: return success response immediately.
    - Failure: store last error/status; sleep for computed backoff before next attempt.
  - After exhausting attempts, return a failure response with the last error message.
- Update `crawl_generic` to delegate to `execute_crawl_with_retries` while preserving all existing field mappings and defaults.
- Logging (minimal): log attempt number, connection mode, status/exception class at INFO/DEBUG based on `log_level`.

## Pseudocode (key parts)

```python
# app/services/crawler/generic.py

def _load_public_proxies(path: Optional[str]) -> list[str]:
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    except Exception:
        return []


def execute_crawl_with_retries(payload: CrawlRequest) -> CrawlResponse:
    settings = get_settings()
    public = _load_public_proxies(settings.proxy_list_file_path)
    private = settings.private_proxy_url

    # Build attempt plan (direct first, public pool, private, final direct)
    plan: list[dict] = []
    plan.append({"mode": "direct", "proxy": None})
    for p in (public if public else []):
        plan.append({"mode": "public", "proxy": p})
    if private:
        plan.append({"mode": "private", "proxy": private})
    plan.append({"mode": "direct", "proxy": None})

    # Trim/extend plan to match max_retries
    if len(plan) < settings.max_retries:
        # cycle public proxies if needed
        while len(plan) < settings.max_retries and public:
            plan.append({"mode": "public", "proxy": public[len(plan) % len(public)]})
    plan = plan[: settings.max_retries]

    last_error = None
    last_status = None

    for i, attempt in enumerate(plan):
        try:
            # assemble args as in current crawl_generic
            page = StealthyFetcher.fetch(
                str(payload.url),
                headless=headless,
                network_idle=network_idle,
                wait_selector=wait_selector,
                wait_selector_state=payload.wait_selector_state,
                timeout=timeout_ms,
                wait=wait_ms or 0,
                # TODO: when supported, pass proxy=attempt["proxy"]
            )
            if getattr(page, "status", None) == 200:
                html = getattr(page, "html_content", None)
                return CrawlResponse(status="success", url=payload.url, html=html)
            last_status = getattr(page, "status", None)
            last_error = f"Non-200 status: {last_status}"
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"

        # backoff before next attempt if any remain
        if i < len(plan) - 1:
            # exponential backoff with jitter
            base = settings.retry_backoff_base_ms
            cap = settings.retry_backoff_max_ms
            jitter = settings.retry_jitter_ms
            delay_ms = min(cap, base * (2 ** i)) + random.randint(0, jitter)
            time.sleep(delay_ms / 1000.0)

    return CrawlResponse(status="failure", url=payload.url, html=None, message=last_error or "exhausted retries")
```

Note: the helper reuses the exact argument mapping already implemented in `crawl_generic` to avoid regressions. In the actual patch, we will refactor to compute `headless`, `network_idle`, `wait_selector`, `wait_ms`, and `timeout_ms` once and share across attempts.

## Testing Plan

- Unit tests (new):
  - `tests/services/test_retry_strategy.py` with a stubbed `StealthyFetcher.fetch` to simulate:
    - First attempt failure (exception), second success => overall success.
    - All attempts non-200 => overall failure after N attempts.
    - Verify exponential backoff calculation (mock `time.sleep`).
    - Proxy plan ordering given env (no proxies, only public, public+private).
- Integration test (extend):
  - Update `tests/integration/test_generic_crawl_integration.py` to set env vars for small `MAX_RETRIES=2` and assert behavior with a known fast URL plus an invalid URL.
- Non-goals for this sprint:
  - End-to-end validation of third-party proxy uptime (out of scope; covered by unit stubs).

## Acceptance Criteria

- Configurable retries via env with sane defaults; default behavior remains single request if `MAX_RETRIES=1`.
- With a transient failure, a later attempt succeeds and returns `status=success`.
- After exhausting attempts, response is `status=failure` and includes the last error/status message.
- No breaking changes to the API schema; existing tests continue to pass with `MAX_RETRIES=1`.
- New unit tests cover retry flow and strategy ordering.

## Observability

- Log attempt number, connection mode (direct/public/private), and outcome at INFO.
- Optionally add a `debug` flag later to include attempt metadata in the response for troubleshooting.

## Risks and Mitigations

- Proxy parameter may not be exposed by Scrapling: encapsulate the wiring so we can enable it later without touching call sites.
- Over-aggressive retries can increase load: keep defaults conservative and cap backoff.
- Public proxies are unreliable: treat as best-effort, fall back to private or direct.

## Rollout

- Phase 1 (this sprint): retries with direct connection; proxy plan scaffolding and config landed; unit tests in place.
- Phase 2: enable proxy parameter once verified; extend tests to cover live proxies in a controlled environment.

## Next Steps

- Implement the config fields and helper in code per this plan.
- Verify library proxy support and wire the parameter when available.
- Add metrics for attempt counts and outcomes in a future sprint.

