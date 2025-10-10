# Sprint 08 - HTML Length Validation & Retry Guard

Goal: detect likely bot-detection responses that return minimal HTML and automatically retry with different proxies/strategies until valid content is obtained.

## Context

- The legacy project applied a minimum HTML length heuristic (500 chars). Content shorter than this was considered invalid and used to trigger retries with alternate proxies or configurations.
- Our current service already supports robust retry and proxy rotation. This sprint integrates the same heuristic to improve quality and reliability when targets serve placeholder or blocked pages.

## Configuration

- Env: `MIN_HTML_CONTENT_LENGTH` (default: `500`)
- Setting: `settings.min_html_content_length` exposed via `app/core/config.py`.
- `.env` updated with a default and `.env.example` documents usage.

## Behavior

- On any successful HTTP 200 fetch, validate HTML length:
  - If `len(html) >= MIN_HTML_CONTENT_LENGTH`: treat as success.
  - Else: treat as failure with message `"HTML too short (<{MIN} chars)"` and continue retries.
- Applies to both executors:
  - `executors/single.py`: returns `failure` immediately when too short.
  - `executors/retry.py`: marks attempt as failure, updates proxy health, and advances according to the attempt plan.
- Fallback path:
  - When Playwright sync API cannot be used and `_simple_http_fetch` returns 200, the same length validation is enforced before accepting success.

## Design Overview

- New config field: `min_html_content_length` with default 500 (env `MIN_HTML_CONTENT_LENGTH`).
- Validation injected at success paths in both `single` and `retry` executors.
- Logging updated to make short-content failures visible and to mark proxies unhealthy after repeated short responses.

## Acceptance Criteria

- Add env `MIN_HTML_CONTENT_LENGTH` and wire to settings.
- For status 200 with HTML shorter than threshold:
  - Single attempt: returns `status=failure` with explanatory message.
  - Retry executor: attempt counted as failure, proxy health updated, subsequent attempt selected.
- Fallback `_simple_http_fetch` obeys the same threshold.
- Unit tests cover both single and retry cases; existing tests updated to use a small threshold where appropriate.

## Testing

- Added `tests/services/test_html_length_validation.py`:
  - Single attempt fails on short HTML (`min=500`, HTML=100 chars).
  - Retry succeeds after two short HTML attempts followed by a long one.
- Updated existing tests that stub minimal HTML to set `min_html_content_length = 1` in their mock settings to preserve expectations.

## Notes

- This heuristic is intentionally simple and fast. It complements, not replaces, other bot-detection strategies and health tracking.
- Threshold can be tuned per deployment via environment variable.
