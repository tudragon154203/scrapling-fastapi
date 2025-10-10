# Sprint 12 — Simplify `/crawl` Endpoint (Breaking Change)

This sprint delivers a simplified, forward‑only request model for the generic crawl endpoint. It removes most legacy compatibility fields and adopts clearer, explicit names for selector waits and timeouts. The force flags are retained but renamed. No backward compatibility is provided.

## Summary

- Remove legacy `x_*` request fields from `POST /crawl` except the force flags which are renamed.
- Rename fields for clarity and consistency:
  - `wait_selector` → `wait_for_selector`
  - `wait_selector_state` → `wait_for_selector_state`
  - `timeout_ms` → `timeout_seconds`
  - `x_force_headful` → `force_headful`
  - `x_force_user_data` → `force_user_data`
- Response shape remains unchanged.

Rationale: The service now depends on a stable Scrapling engine and no longer needs legacy compatibility. The updated names describe intent and units unambiguously.

## API

- Endpoint: `POST /crawl`
- Request body (JSON):
  - `url` (string, required): Absolute HTTP(S) URL to crawl.
  - `wait_for_selector` (string, optional): CSS selector to wait for before capturing content.
  - `wait_for_selector_state` (string, optional): One of `visible | attached | hidden | detached`. Defaults to `attached` when `wait_for_selector` is provided and no state is specified.
  - `timeout_seconds` (integer, optional): Overall operation timeout in seconds. Defaults to service settings (20 by default; see Environment Defaults).
  - `network_idle` (boolean, optional): When `true`, instructs the crawler to wait for a network‑idle condition before capture. Defaults to service settings (false by default).
  - `force_headful` (boolean, optional): When `true`, requests non‑headless mode if supported by the runtime environment. Actual effect may depend on platform/container capabilities.
  - `force_user_data` (boolean, optional): Reserved for future persistent profile support; currently accepted but may be a no‑op depending on the engine.

Notes:

- Headless/headful behavior is primarily controlled by server configuration; `force_headful=true` attempts to override to non‑headless where supported.
- The service may apply additional stealth parameters internally; these are not part of the public API.

### Renamed fields

- `x_force_headful` → `force_headful`
- `x_force_user_data` → `force_user_data`

### Removed fields (no longer accepted)

- `x_wait_for_selector` (use `wait_for_selector`)
- `x_wait_time` (removed; fixed waits are not directly supported)

## Response

`200 OK` with a typed body that indicates success or failure (the endpoint is operational even when the crawl fails due to site defenses):

```
{
  "status": "success" | "failure",
  "url": "https://…",
  "html": "<html>…</html>" | null,
  "message": "string | null"
}
```

- On `success`: `html` contains the captured content; `message` is null.
- On `failure`: `html` is null; `message` contains a diagnostic summary (e.g., short HTML, non‑200 status, or an exception summary).

Server errors (e.g., validation bugs, unexpected exceptions) may return `5xx` with standard FastAPI error envelopes. Invalid inputs return `422 Unprocessable Entity` from validation.

## Behavior

- The crawler instructs the underlying engine with the provided options:
  - `wait_for_selector` and `wait_for_selector_state` are passed through to the browser automation to wait for a specific element state prior to capture.
  - `network_idle=true` asks the engine to wait for a quiescent network state before capture.
  - `timeout_seconds` governs the overall crawl timeout. Internally, the service uses milliseconds and converts from seconds.
- A crawl is considered `success` only when the underlying fetch reports HTTP 200 AND the HTML length meets or exceeds the configured threshold (see Environment Defaults). Otherwise, the result is `failure` with an explanatory `message`.

Interactions:

- `wait_for_selector` and `network_idle` can be used together; the engine attempts to honor both when supported by the underlying fetcher.
- If a selector wait is specified without `wait_for_selector_state`, the default state `attached` is used.

## Environment Defaults

Loaded via `app/core/config.py` (environment variables in parentheses):

- `default_network_idle` (env `NETWORK_IDLE`): default `false`.
- `default_timeout_ms` (env `TIMEOUT_MS`): default `20000` ms → 20 seconds.
- `min_html_content_length` (env `MIN_HTML_CONTENT_LENGTH`): default `500` characters.

## Request Examples

Minimal crawl:

```bash
curl -sS -X POST http://localhost:8000/crawl \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com"
  }'
```

Wait for a selector and network idle with explicit timeout:

```bash
curl -sS -X POST http://localhost:8000/crawl \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com",
    "wait_for_selector": "#app",
    "wait_for_selector_state": "visible",
    "timeout_seconds": 30,
    "network_idle": true
  }'
```

## Response Examples

Success:

```json
{
  "status": "success",
  "url": "https://example.com",
  "html": "<html>…omitted…</html>",
  "message": null
}
```

Failure (short HTML / suspected bot defense):

```json
{
  "status": "failure",
  "url": "https://example.com",
  "html": null,
  "message": "HTML too short (<500 chars); suspected bot detection"
}
```

## Migration Guide (Breaking)

- Replace fields in requests to `POST /crawl`:
  - `wait_selector` → `wait_for_selector`
  - `wait_selector_state` → `wait_for_selector_state`
  - `timeout_ms` → `timeout_seconds` (value divided by 1000)
  - `x_force_headful` → `force_headful`
  - `x_force_user_data` → `force_user_data`
- Remove legacy fields from clients:
  - `x_wait_for_selector`, `x_wait_time`

No server‑side backward compatibility is retained. Clients using the old shape will receive `422` validation errors.

* Change tests to adapt to this new schema

## AusPost and DPD Endpoints

The force flag renames apply equally to the specialized tracking endpoints and constitute a breaking change to their request bodies:

- Endpoint: `POST /crawl/auspost`

  - `x_force_headful` → `force_headful`
  - `x_force_user_data` → `force_user_data`
- Endpoint: `POST /crawl/dpd`

  - `x_force_headful` → `force_headful`
  - `x_force_user_data` → `force_user_data`

No other request fields change on these endpoints in this sprint.

## Out of Scope

- Authentication, rate limiting, and result caching are not introduced here.

## Implementation Notes (for maintainers)

- Update `app/schemas/crawl.py` to reflect the new request fields and remove all legacy `x_*` fields.
- Update option resolution in `app/services/crawler/options/resolver.py` to:

  - Read `wait_for_selector` / `wait_for_selector_state`.
  - Accept `timeout_seconds` (convert to ms internally).
  - Stop referencing `x_wait_*` fields; reference `force_headful` and `force_user_data` instead of `x_force_*`.
- Ensure the adapter still passes `wait_selector`, `wait_selector_state`, `timeout` (ms), and `network_idle` to the underlying fetcher.
- Update specialized schemas to rename force flags:

  - `app/schemas/auspost.py`: `x_force_headful` → `force_headful`, `x_force_user_data` → `force_user_data`.
  - `app/schemas/dpd.py`: `x_force_headful` → `force_headful`, `x_force_user_data` → `force_user_data`.

Acceptance criteria: OpenAPI reflects the new schema, service rejects legacy fields with `422`, and integration tests continue to pass with updated request bodies.
