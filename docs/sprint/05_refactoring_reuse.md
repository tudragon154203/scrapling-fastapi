# Sprint 05 - Refactoring for Reuse and Less Bloat

Goal: reduce duplication in the generic crawler, increase reusability, and keep behavior fully backward compatible. The focus is to centralize option resolution, capability detection, and fetch kwargs composition so both single-attempt and retry paths share the same logic.

## Problem Statement

- `app/services/crawler/generic.py` duplicated logic across the single-attempt (`crawl_generic`) and retry (`execute_crawl_with_retries`) flows:
  - resolving effective options from `CrawlRequest` and defaults
  - building Camoufox `additional_args` and `extra_headers` from settings
  - detecting supported fetch kwargs on `StealthyFetcher.fetch`
  - composing the final kwargs for `fetch` calls (including proxy/geoip)

This duplication made changes error-prone and added cognitive load.

## Objectives

- Extract small, focused helpers for shared concerns.
- Keep external behavior and API unchanged; preserve test suite expectations.
- Improve maintainability for future features (new fetch kwargs, more Camoufox options).

## Changes

In `app/services/crawler/generic.py`:

- Added helpers:
  - `_resolve_effective_options(payload, settings)`
    - Produces: `wait_selector`, `timeout_ms`, `wait_ms`, `headless`, `network_idle`, `wait_selector_state`.
  - `_build_camoufox_args(payload, settings)`
    - Produces: `additional_args` and `extra_headers` (locale/window/disable_coop/virtual_display, and user data dir when enabled).
  - `_detect_fetch_capabilities(fetch_callable)`
    - Introspects `StealthyFetcher.fetch` once to learn supported kwargs.
  - `_compose_fetch_kwargs(options, caps, selected_proxy, additional_args, extra_headers, settings)`
    - Builds a capability-safe kwargs dict for `StealthyFetcher.fetch`, including conditional `proxy`, `geoip`, `additional_args`, and `extra_headers`.

- Refactored both `execute_crawl_with_retries` and the single-attempt branch of `crawl_generic` to use the new helpers. This removed repeated blocks and aligned how both paths build fetch calls.

## Benefits

- Less duplication: one place to update when adding/changing fetch options.
- Clear separation of concerns: option resolution, capability detection, and kwargs composition are independent and testable.
- Safer evolution: future stealth options or fetch kwargs require minimal changes.

## Compatibility

- No API changes. All behavior remains the same.
- Existing tests continue to pass (see below).

## Testing

- Full test suite run: all tests passed.
- The refactor is internal; public interfaces (`crawl_generic`, `execute_crawl_with_retries`) are unchanged.

## Follow‑ups (optional)

- Consider moving generic helpers into a module (e.g., `app/services/crawler/utils.py`) if other crawlers need them.
- Add micro-tests for the new helpers if/when they become more complex.
- Explore making proxy health tracking injectable to ease testing and future persistence.

