# Sprint 05 - Camoufox User Data (Minimal)

Goal: support Camoufox persistent user data for the `/crawl` endpoint using only the existing legacy flag `x_force_user_data`. When this flag is true, use a single user data directory configured via environment variable. No extra fields and no master toggle.

Additionally, pass a minimal set of stealth-friendly arguments to reduce bot detection without changing the API surface (config-only toggles).

## Problem Statement

- `x_force_user_data` exists but currently does nothing.
- Some targets benefit from session persistence (cookies, localStorage) across requests.

## Objectives

- Respect `x_force_user_data=true` to enable persistent user data.
- Read a single directory path from `.env` and pass it to Camoufox via Scrapling when supported.
- Avoid new schema fields and avoid a global enable toggle.

## API

- Endpoint: `POST /crawl` (unchanged)
- Request fields (subset relevant here):
  - `x_force_user_data` (bool, optional): when true, enable persistent user data using the path from env.

## Configuration

- Add one setting in `app/core/config.py` with env binding:
  - `camoufox_user_data_dir` (`CAMOUFOX_USER_DATA_DIR`): absolute or workspace-relative path to the Camoufox user data directory.

Behavior:

- If `x_force_user_data` is true and `CAMOUFOX_USER_DATA_DIR` is set, pass the directory to `StealthyFetcher.fetch` using the supported parameter name.
- If the parameter is not supported by the installed Scrapling/Camoufox version, log one warning and continue without persistence.
- If `CAMOUFOX_USER_DATA_DIR` is missing, log at INFO and continue without persistence (no error).

## Design Overview

- Where:
  - Settings addition: `app/core/config.py`.
  - Wiring: `app/services/crawler/generic.py` (both single-attempt and retry paths).
- How:
  - Resolve `use_ud = payload.x_force_user_data is True`.
  - If `use_ud` and `settings.camoufox_user_data_dir` is non-empty:
    - Ensure directory exists (`os.makedirs(dir, exist_ok=True)`).
    - Detect a supported parameter on `StealthyFetcher.fetch`: first match in `("user_data_dir", "profile_dir", "profile_path", "user_data")`.
    - Pass `kwargs[param] = settings.camoufox_user_data_dir` on every `fetch` call (all attempts reuse the same dir).

### Additional Stealth Args

Keep behavior opt-in via environment. No schema changes and the toggles are safe defaults.

- geoip: enable when using any proxy (private or public). Spoofs timezone/locale/WebRTC for the proxy IP. Controlled by `CAMOUFOX_GEOIP` (default: true).
- window: fix a realistic window size to match common devices. Controlled by `CAMOUFOX_WINDOW` (formats: `1366x768` or `1366,768`).
- solve_cloudflare: true

Notes

- `google_search` referer remains enabled by default (Scrapling default) and helps blend traffic.
- `allow_webgl` remains true; disabling WebGL can trigger WAFs. Use `webgl_config` only if you have a specific need.
- `block_images`/`disable_resources` can speed up requests but may break page loads and hint automation; keep them off unless you know the target tolerates them.

## Testing

- Unit tests:
  - When `x_force_user_data=true` and env set, assert `fetch` receives a user-data argument.
  - When `x_force_user_data=true` but env unset, no user-data argument is passed.
  - When the parameter is unsupported, no user-data argument is passed and no exception is raised.

## Acceptance Criteria

- `x_force_user_data` alone controls enablement per request.
- Only one env variable is required: `CAMOUFOX_USER_DATA_DIR`.
- Safe fallback if unsupported or unset; no changes to existing retry/proxy behavior.
- Optional stealth toggles (geoip/locale/window/disable_coop/virtual_display) are honored when set, with safe defaults when unset.
