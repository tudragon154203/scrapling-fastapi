# TODO: Headless TikTok Search Fallback PRD

## Summary

- Redirect headless executions of `/tiktok/search` from the multistep Playwright automation to the URL-parameter strategy to restore reliability.
- Preserve headful behaviour (force_headful or default BrowserMode decision) by keeping the multistep browser automation path unchanged.
- Ensure API responses clearly reflect the actual execution mode and continue to satisfy existing contracts.

## Background

- The `multistep` strategy relies on humanized Playwright flows that require a visible browser; in headless mode it stalls, returning 500 errors.
- Historically all production calls were headful; recent changes introduced `force_headful` toggling, exposing the headless failure path.
- The `direct` URL-parameter strategy already exists, returns normalized data, and is headless-safe.

## Goals

1. Automatically choose the `direct` strategy whenever BrowserMode resolves to `headless`.
2. Maintain parity in response structure (`TikTokSearchResponse`) and execution_mode reporting.
3. Keep multistep automation intact for headful sessions (forced or default).
4. Backstop the change with unit coverage and contract updates documenting the routing behaviour.

## Non-Goals

- Rewriting the multistep automation to function in headless mode.
- Making invasive changes to TikTok service internals beyond strategy selection.
- Adding new request parameters or altering existing validation.

## Requirements

- **R1**: BrowserModeService continues to decide execution mode using `force_headful` and test context signals.
- **R2**: TikTokSearchService accepts a resolved strategy (`direct` or `multistep`) and executes accordingly.
- **R3**: `/tiktok/search` endpoint must override `multistep` to `direct` when BrowserMode resolves to headless.
- **R4**: Response `execution_mode` matches the BrowserMode decision regardless of strategy.
- **R5**: Unit tests cover both headless (redirected) and headful (unchanged) flows, asserting strategy selection and search invocation arguments.
- **R6**: Documentation (API + specs) records the automatic fallback to the URL-parameter strategy for headless mode.

## Proposed Approach

1. **Endpoint Routing Logic**
   - Import `BrowserMode` enum in `app/api/tiktok.py`.
   - Derive `effective_strategy`: default to payload.strategy; switch to `direct` when BrowserMode is HEADLESS and user requested `multistep`.
   - Instantiate `TikTokSearchService` with `effective_strategy`.
2. **Service Layer**
   - Leverage existing behaviour: the URL-parameter service already handles headless; no modification required beyond receiving the chosen strategy.
3. **Testing**
   - Extend `tests/api/test_tiktok_api_unit.py` to assert that headless calls request `direct` and headful calls keep `multistep`.
   - Ensure mocks capture both strategy selection and search call arguments.
4. **Docs**
   - Update `docs/api.md` and relevant spec (`specs/001-change-tiktok-search`) to mention automatic fallback.

## Validation Plan

- Run fast API unit suite (`python -m pytest tests/api/test_tiktok_api_unit.py`).
- Optionally execute integration tests that hit `/tiktok/search` in controlled environments to confirm no regression in headful mode.
- Manual smoke test (if time) by hitting the endpoint with `force_headful=false` after redeploy.

## Risks & Mitigations

- **Risk**: URL-parameter strategy may not return parity results for some queries. *Mitigation*: Document behaviour and monitor; users can still force headful.
- **Risk**: Tests relying on patched strategy names may need updates. *Mitigation*: Update mocks to assert new behaviour.

## Timeline (abbreviated)

- Day 0: Implement routing + unit tests.
- Day 1: Update docs/specs, run targeted test suite, prepare PR.
- Day 2: Review feedback, deploy.
