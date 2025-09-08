# Spec: Persistent User-Data with "read/write mode" for Camoufox (Scrapling)

## Goals
- Support **persistent login sessions** across multiple web platforms (e.g., TikTok, e-commerce sites, social media, SaaS dashboards) using Camoufox profiles.
- Enable **safe concurrency**: many parallel “read” (clone) sessions, and exactly **one “write” session** updating the master profile.
- Preserve compatibility and safe fallback if environment variables or the installed Scrapling/Camoufox version do not support user-data parameters.

---

## API

### Applicable Endpoints
- `POST /crawl` (and derivatives like `/crawl/auspost`, `/crawl/dpd` that use the same fetch pipeline).

### Request Fields
```json
{
  "force_user_data": true,
  "user_data_mode": "read" | "write"
}
```
- `force_user_data`:
  - `false` (default): do **not** attach user-data (legacy behavior).
  - `true`: enable persistent profile handling (if supported).
- `user_data_mode` (default: `"read"`):
  - `"write"`: use **master profile** for updating login/cookies; requires exclusive lock.
  - `"read"`: create an **ephemeral clone** from master, safe for parallel runs, discarded after completion.

---

## Environment Configuration

- `CAMOUFOX_USER_DATA_DIR`: root directory for profiles. Default: `data/camoufox_profiles`.
  - Contains:
    - `master/` – persistent profile (used in write mode).
    - `clones/<uuid>/` – ephemeral clones (used in read mode).

System already binds this env var to `settings.camoufox_user_data_dir`. If enabled and supported by Scrapling/Camoufox, the service auto-creates directories and passes the correct param (`user_data_dir | profile_dir | profile_path | user_data`) to `StealthyFetcher.fetch`. If not supported → logs a warning and continues without persistence.

---

## Behavior

### Write Mode
- **Effective path**: `<CAMOUFOX_USER_DATA_DIR>/master`.
- **Lock**: acquire exclusive file-lock (e.g., `master.lock`) to ensure only 1 write session at a time.
- **Lifecycle**: the browser is kept open for user interaction. The crawl does **not** automatically close the browser; instead it waits until the user manually closes the browser window. Only then will the crawl return its result. This ensures interactive logins or manual actions can be completed.

### Read Mode
- **Effective path**: create `<CAMOUFOX_USER_DATA_DIR>/clones/<uuid>` by cloning from master.
- **Concurrency**: each clone is independent, safe for parallel runs.
- **Lifecycle**: delete clone directory after run (discard). No merging back.

---

## Fetch Kwargs Composition

1. **Enablement**
   - If `force_user_data != true` → do not pass user-data args.
   - If `true` → resolve `effective_dir` via `user_data_mode`, ensure directory exists.

2. **Capability Detection**
   - Probe `StealthyFetcher.fetch` for accepted args.
   - Priority: `user_data_dir`, `profile_dir`, `profile_path`, `user_data`.
   - Attach chosen param if supported.

3. **Other kwargs**
   - Proxy, timeout, wait selectors, headless, etc. remain unchanged.
   - GeoIP already auto-enabled when supported.

---

## Concurrency Management

- **Write**: exclusive lock → max one active writer.
- **Read**: unlimited parallel clones, no lock required.
- **No merging**: discard clones to avoid cookie/DB corruption.

---

## Error Handling & Fallback

- **Env missing**: do not pass user-data; log info; continue normally.
- **Unsupported param**: log warning; continue without user-data.
- **Clone copy failure**: fail current request with error message; master unaffected.
- **Writer conflict**: if lock cannot be acquired, return 409/429 or queue internally.

---

## Implementation Plan

- **New file**: `app/services/crawler/options/user_data.py`
  - `user_data_context(base_dir: str, mode: str) -> ContextManager[(path:str, cleanup:callable)]`
  - `mode="write"`: returns `…/master` with exclusive lock.
  - `mode="read"`: clones master to `…/clones/<uuid>`; cleanup deletes it.

- **Integration**: in Camoufox arg builder/executor:
  - Call `user_data_context` to resolve effective dir.
  - Detect supported param name.
  - Inject into fetch kwargs if supported.

---

## Testing

### Unit
- `force_user_data=true, mode=write` → kwargs contains `…/master`; lock ensures single writer.
- `force_user_data=true, mode=read` → kwargs contains `…/clones/<uuid>`; cleanup removes it.
- Env unset → no user-data param.
- Unsupported param → no user-data param, no exception, warning logged.

### Integration
- 1 writer + N readers in parallel → no corruption, writer updates master, subsequent readers clone new state.
- Other features (retry, proxy, geoip, min HTML length) remain intact.

### TDD Workflow
1. **Write failing tests (RED)** for all cases above.
2. **Implement minimal code (GREEN)** with `user_data_context` and builder integration.
3. **Refactor** for clarity, keep tests passing.

---

## Logging
- Use global logging system.
- Debug logs should show:
  - `user_data_mode` decision.
  - Effective path (`master` or `clones/<uuid>`).
  - Lock acquisition/release events.

---

## Acceptance Criteria
- When `force_user_data=true`:
  - `user_data_mode="write"`: uses master with lock, only one writer allowed.
  - `user_data_mode="read"`: uses clones, parallel safe, cleanup after run.
- Fallback safe when env missing or param unsupported.
- No regressions in stealth, proxy, retry, or geoip features.

