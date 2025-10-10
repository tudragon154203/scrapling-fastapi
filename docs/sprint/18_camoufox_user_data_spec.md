# Spec: Persistent User-Data for Camoufox (Scrapling) — /crawl is read-only

## Goals
- Support persistent login sessions across platforms using Camoufox profiles.
- Enable safe concurrency for many parallel read (clone) sessions.
- Preserve compatibility and safe fallback if environment variables or the installed Scrapling/Camoufox version do not support user-data parameters.
- Write/interactive sessions are delegated to a dedicated endpoint (see Sprint 19 — Browse Endpoint).

---

## API

### Applicable Endpoints
- `POST /crawl` (and derivatives like `/crawl/auspost`, `/crawl/dpd`) — READ-ONLY clones.
- Write/interactive sessions have moved to the `/browse` endpoint (Sprint 19), not `/crawl`.

### Request Fields
```json
{
  "force_user_data": true
}
```
- `force_user_data`:
  - `false` (default): do not attach user-data (legacy behavior).
  - `true`: enable persistent profile handling (if supported).
  - `/crawl` endpoint always uses read mode for user data (no write mode).

---

## Environment Configuration

- `CAMOUFOX_USER_DATA_DIR`: root directory for profiles. Default: `data/camoufox_profiles`.
  - Contains:
    - `master/` — persistent profile (used by the `/browse` writer endpoint).
    - `clones/<uuid>/` — ephemeral clones (used by `/crawl` read sessions).

The system binds this env var to `settings.camoufox_user_data_dir`. If enabled and supported by Scrapling/Camoufox, the service auto-creates directories and passes the correct param (`user_data_dir | profile_dir | profile_path | user_data`) to `StealthyFetcher.fetch`. If not supported, it logs a warning and continues without persistence.

---

## Behavior

### Read Mode (only for `/crawl`)
- Effective path: `<CAMOUFOX_USER_DATA_DIR>/clones/<uuid>` cloned from `master` when present.
- Concurrency: each clone is independent, safe for parallel runs.
- Lifecycle: delete clone directory after run (discard). No merging back.

Write mode has been removed from `/crawl`. For write/interactive sessions (persistent login updates, headful flows that wait for manual close), see Sprint 19 — Browse Endpoint (`docs/sprint/19_browse_endpoint_spec.md`).

---

## Fetch Kwargs Composition

1. Enablement
   - If `force_user_data != true` → do not pass user-data args.
   - If `true` → resolve `effective_dir` as a read clone; ensure directory exists.

2. Capability Detection
   - Probe `StealthyFetcher.fetch` for accepted args.
   - Priority: `user_data_dir`, `profile_dir`, `profile_path`, `user_data`.
   - Attach chosen param if supported.

3. Other kwargs
   - Proxy, timeout, wait selectors, headless, etc. remain unchanged.
   - GeoIP already auto-enabled when supported.

---

## Concurrency Management

- Read: unlimited parallel clones on `/crawl`, no lock required.
- No merging: discard clones to avoid cookie/DB corruption.
- Write-mode concurrency and locking is defined in the `/browse` spec (Sprint 19).

---

## Error Handling & Fallback

- Env missing: do not pass user-data; log info; continue normally.
- Unsupported param: log warning; continue without user-data.
- Clone copy failure: fail current request with error message; master unaffected.
- `/crawl` only supports read mode for user data; write operations use `/browse` instead.

---

## Implementation Plan

- `app/services/crawler/options/user_data.py` provides context utilities used by both `/crawl` (read clones) and `/browse` (write/master). `/crawl` must call it only in read mode.
- Integration in Camoufox builder/executors should pass only read-clone directories for `/crawl`.

---

## Testing

### Unit
- `force_user_data=true, mode=read` → kwargs contains `.../clones/<uuid>`; cleanup removes it.
- Env unset → no user-data param.
- Unsupported param → no user-data param, no exception, warning logged.

### Integration
- Multiple readers in parallel have independent clones; no corruption. Other features (retry, proxy, geoip, min HTML length) remain intact.

---

## Logging
- Use global logging system.
- Debug logs should show:
  - Effective path (`clones/<uuid>`).

---

## Acceptance Criteria
- `/crawl` supports persistent profiles only in read mode (clone directories).
- Fallback safe when env missing or param unsupported.
- No regressions in stealth, proxy, retry, or geoip features.
- Write-mode behavior is out of scope here; see `/browse` spec in Sprint 19.

