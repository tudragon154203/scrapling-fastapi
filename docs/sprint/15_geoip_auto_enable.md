# Sprint 15 - Auto-enable GeoIP When Supported

Goal: automatically enable GeoIP spoofing (`geoip=True`) whenever the underlying fetcher supports the `geoip` parameter. This applies to both proxy and proxyless requests. No environment configuration is required; the system should “just work” by attempting GeoIP when possible.

## Context

- Prior behavior (Sprint 06): GeoIP was enabled only when a proxy was in use and gated by an environment flag `CAMOUFOX_GEOIP` (default true).
- Some endpoints (e.g., AusPost in Sprint 10) recommend attempting GeoIP and gracefully falling back when the MaxMind DB is missing or invalid.
- We want consistent behavior across all fetches: if the fetcher can accept `geoip`, we pass it by default, independent of proxy usage or environment flags.

## API (unchanged)

- Endpoints: `POST /crawl`, `POST /crawl/auspost`, `POST /crawl/dpd`.
- Request/response shapes do not change.
- No new request field or environment variable is introduced. No client action required.

## Behavior

- When composing fetch arguments, if capability detection indicates that `geoip` is supported, include `geoip=True` in the fetch kwargs.
- This applies whether a proxy is set or not.
- If the fetcher or its GeoIP backend raises a known “DB missing/invalid” error (e.g., mentions `InvalidDatabaseError` or `GeoLite2-City.mmdb`), retry once without `geoip` and proceed with the result.
- Capability detection is based on signature introspection or the presence of `**kwargs` (same pattern already used for other flags via `_ok("...")`).

## Implementation Notes

- Update the fetch arg composer to remove dependence on proxy presence and environment flags for GeoIP:
  - app/services/crawler/adapters/scrapling_fetcher.py:104-105, 132-133
    - Before: `geoip` only when `settings.camoufox_geoip` is true AND a proxy is selected.
    - After: if `_ok("geoip")` is true, set `fetch_kwargs["geoip"] = True` unconditionally (no proxy or env gate).
  - Keep capability detection helper `_ok(name)` unchanged and reuse it for `geoip`.
- Environment defaults remain in `app/core/config.py`, but `camoufox_geoip` is no longer consulted by the adapter for enabling GeoIP.
- Ensure retry/fallback without GeoIP is applied where applicable (centralized around fetch or specific endpoints as previously documented in Sprint 10).

### Pseudocode (before → after)

Before:

```
geoip_enabled = bool(settings.camoufox_geoip and selected_proxy)
if _ok("geoip") and geoip_enabled:
    fetch_kwargs["geoip"] = True
```

After:

```
if _ok("geoip"):
    fetch_kwargs["geoip"] = True
```

## Testing

- Unit (adapter):
  - With a fake fetcher whose signature accepts `**kwargs` or explicitly `geoip`, verify that composed kwargs include `geoip=True`:
    - when `selected_proxy` is set
    - when `selected_proxy` is None
  - Verify behavior is independent of `settings.camoufox_geoip`.
- Integration: smoke test core endpoints to ensure no regressions. If the environment lacks a MaxMind DB, confirm the fallback path is taken (one retry without `geoip`).

## Acceptance Criteria

- For any fetcher that supports `geoip`, requests pass `geoip=True` by default, regardless of proxy usage.
- No environment configuration is required to enable GeoIP.
- If GeoIP initialization fails due to missing/invalid DB, the request automatically retries once without `geoip`.
- No API changes; existing clients continue to work unchanged.

## Out of Scope

- Adding new user-facing configuration for GeoIP.
- Changing other stealth parameters (locale, window size, etc.).

## References

- Adapter: app/services/crawler/adapters/scrapling_fetcher.py
- Prior sprints: docs/sprint/06_camoufox_user_data_and_additional_stealth.md, docs/sprint/10_auspost_tracking_endpoint.md

