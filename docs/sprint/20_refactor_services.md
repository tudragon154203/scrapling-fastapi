Sprint 20 — Refactor Services (Breaking)

Goal
- Split `app/services` into three clear layers: `common`, `crawler`, and `browser`.
- Remove legacy coupling and transitional shims. No backwards compatibility.
- Keep endpoints stable but update all imports and tests to the new structure.

Motivation
- Separation of concerns: interactive browsing (UX, user-data) vs. scripted crawling (HTML extraction).
- A shared “common” layer avoids duplication across both.
- Cleaner dependencies and faster iteration on either side without cross‑coupling.

New Layout
- `app/services/common`: shared orchestration, types, interfaces, and adapters
- `app/services/crawler`: crawl flows, retry/backoff, proxy logic, verticals (DPD, AusPost)
- `app/services/browser`: browse flows, interactive actions, user‑data/camoufox options

Target Tree (high‑level)
- app/services/common
  - engine.py
  - interfaces.py
  - types.py
  - adapters/
    - scrapling_fetcher.py
- app/services/crawler
  - generic.py
  - dpd.py
  - auspost.py
  - executors/
    - retry_executor.py
    - single_executor.py
    - backoff.py
    - auspost_no_proxy.py
  - proxy/
    - health.py
    - plan.py
    - sources.py
    - redact.py
  - (optional) domain_actions/
    - auspost.py (if we choose to move domain‑specific actions here)
- app/services/browser
  - browse.py
  - executors/
    - browse_executor.py
  - actions/
    - base.py
    - wait_for_close.py
    - humanize.py
  - options/
    - resolver.py
    - camoufox.py
    - user_data.py

File Moves (authoritative mapping)
- app/services/crawler/core/engine.py → app/services/common/engine.py
- app/services/crawler/core/interfaces.py → app/services/common/interfaces.py
- app/services/crawler/core/types.py → app/services/common/types.py
- app/services/crawler/adapters/scrapling_fetcher.py → app/services/common/adapters/scrapling_fetcher.py
- app/services/crawler/browse.py → app/services/browser/browse.py
- app/services/crawler/executors/browse_executor.py → app/services/browser/executors/browse_executor.py
- app/services/crawler/actions/base.py → app/services/browser/actions/base.py
- app/services/crawler/actions/wait_for_close.py → app/services/browser/actions/wait_for_close.py
- app/services/crawler/actions/humanize.py → app/services/browser/actions/humanize.py
- app/services/crawler/options/resolver.py → app/services/browser/options/resolver.py
- app/services/crawler/options/camoufox.py → app/services/browser/options/camoufox.py
- app/services/crawler/options/user_data.py → app/services/browser/options/user_data.py
- app/services/crawler/generic.py → stays in app/services/crawler/generic.py
- app/services/crawler/dpd.py → stays in app/services/crawler/dpd.py
- app/services/crawler/auspost.py → stays in app/services/crawler/auspost.py
- app/services/crawler/executors/{retry_executor.py,single_executor.py,backoff.py,auspost_no_proxy.py} → stay in app/services/crawler/executors/
- app/services/crawler/proxy/* → stay in app/services/crawler/proxy/

Public Interfaces after Refactor
- Engine and base contracts live in `app/services/common`:
  - `app.services.common.engine.CrawlerEngine`
  - `app.services.common.interfaces` (IExecutor, IFetchClient, …)
  - `app.services.common.types` (CrawlOptions, FetchArgs, FetchCapabilities, …)
  - `app.services.common.adapters.scrapling_fetcher` (ScraplingFetcherAdapter, FetchArgComposer)
- Crawler side remains focused on extraction:
  - `app.services.crawler.generic.GenericCrawler`
  - `app.services.crawler.dpd.DPDCrawler`
  - `app.services.crawler.auspost.AuspostCrawler`
  - Executors and proxy strategy under `app.services.crawler.executors` and `app.services.crawler.proxy`
- Browser side handles interactive sessions and user‑data:
  - `app.services.browser.browse.BrowseCrawler`
  - `app.services.browser.executors.browse_executor.BrowseExecutor`
  - `app.services.browser.actions` and `app.services.browser.options`

Endpoint Imports (breaking import paths, same HTTP routes)
- Update `app/api/routes.py` imports only; HTTP contract remains the same:
  - from app.services.crawler.generic import GenericCrawler  (unchanged)
  - from app.services.crawler.dpd import DPDCrawler        (unchanged)
  - from app.services.crawler.auspost import AuspostCrawler (unchanged)
  - from app.services.browser.browse import BrowseCrawler   (UPDATED)
- Any direct references to `core.*` must change to `services.common.*`.

Code Touch Points (non‑exhaustive)
- Replace imports throughout codebase:
  - `app.services.crawler.core.engine` → `app.services.common.engine`
  - `app.services.crawler.core.interfaces` → `app.services.common.interfaces`
  - `app.services.crawler.core.types` → `app.services.common.types`
  - `app.services.crawler.adapters.scrapling_fetcher` → `app.services.common.adapters.scrapling_fetcher`
  - `app.services.crawler.browse` → `app.services.browser.browse`
  - `app.services.crawler.executors.browse_executor` → `app.services.browser.executors.browse_executor`
  - `app.services.crawler.actions.*` → `app.services.browser.actions.*`
  - `app.services.crawler.options.*` → `app.services.browser.options.*`

Tests To Update (import paths only)
- API tests:
  - tests/api/test_browse_endpoint.py → import `BrowseCrawler` from `app.services.browser.browse`
- Service tests:
  - tests/services/test_browse_executor.py → import `BrowseExecutor` from `app.services.browser.executors.browse_executor`
  - tests/services/test_scrapling_fetcher.py → import adapter and `FetchCapabilities` from `app.services.common.*`
  - Any uses of `core.types`, `core.interfaces`, or `adapters.scrapling_fetcher` → point to `app.services.common.*`
- No test semantics change expected; only paths move. Keep all existing behaviors and assertions.

Breaking Changes Summary
- No compatibility shims or legacy re‑exports. All imports must be updated.
- Internal Python import paths change; HTTP API remains unchanged.
- Any third‑party code importing internal modules must be updated accordingly.

Refactor Steps (suggested order)
1) Create new packages: `app/services/common`, `app/services/browser` with `__init__.py`.
2) Move files per mapping above; update relative imports locally.
3) Update all imports in code to new paths; focus first on `app/api/routes.py` and service entry points.
4) Update tests to new import paths.
5) Run full test suite and fix any missed imports/logging names.
6) Sweep for dead files/paths under old `crawler/*` locations; remove leftovers.

Modularize Bloated Files (new task)
- Objective: reduce oversized modules into focused units with single responsibility. No compatibility shims; update imports/tests accordingly.
- Indicators of bloat (use as heuristics, not hard rules):
  - File > 250 LOC or function > 80 LOC
  - Module contains 3+ distinct responsibilities (e.g., orchestration + fallbacks + threading + arg building)
  - High branching or repeated nested try/except in multiple code paths
- Candidates and suggested splits:
  - `app/services/common/adapters/scrapling_fetcher.py` → split into:
    - `fetch_client.py`: `ScraplingFetcherAdapter` core fetch interface only
    - `thread_runner.py`: “running loop” detection and threaded execution utilities
    - `geoip_fallback.py`: GeoIP fallback wrapper logic
    - `http_fallback.py`: lightweight HTTP fallback implementation
    - `args.py`: `FetchArgComposer` (argument composition concerns isolated)
  - `app/services/crawler/executors/retry_executor.py` → split into:
    - `retry_loop.py`: attempt orchestration and timing
    - `result_eval.py`: HTTP/HTML acceptance logic (status/min length/etc.)
    - `rotation.py`: proxy selection/rotation helpers
    - `health_ops.py`: proxy health marking utilities
  - Optional: `app/services/common/engine.py` if coupling grows → extract executor factory to `engine_factory.py`.
- Guardrails:
  - Keep public behavior identical; only reorganize internals and imports.
  - Preserve existing logging where helpful; adjust module logger names.
  - Add/adjust unit tests to cover new helpers (pure functions/util modules) without adding unrelated tests.
- Acceptance for this task:
  - Identified candidates documented in PR description with rationale.
  - New modules created and imports updated.
  - Tests pass with equal or improved coverage; no behavior regressions.

Post‑Move Sanity Checklist
- Browse flow still composes engine correctly:
  - `BrowseCrawler` uses `BrowseExecutor` and `CrawlerEngine` from `services.common`.
- Crawler flows still use retry/backoff and proxy strategy unchanged.
- Scrapling adapter and capability detection used from `services.common.adapters`.
- Options resolver and camoufox/user‑data live under `services.browser.options` and are referenced by both browse and crawl executors as needed.

Acceptance Criteria
- All unit and integration tests pass after import updates (no behavior change expected).
- No `from app.services.crawler.core...` imports remain.
- `/crawl`, `/crawl/dpd`, `/crawl/auspost`, and `/browse` routes are unchanged at the HTTP layer and continue to pass tests.

Risks / Notes
- Domain‑specific actions currently under `actions/auspost.py` can either:
  - remain where used under crawler (preferred), or
  - move to `app/services/crawler/domain_actions/auspost.py` for clarity. Decide during implementation.
- Ensure logging namespaces are updated (module paths in loggers will change).
- Watch for circular imports after moves; keep “common” free of domain logic.

Out of Scope
- Further behavior changes, new endpoints, or configuration changes.
- Compatibility aliases or transitional re‑exports.

Migration Tips
- Use a fast search/replace for imports (e.g., ripgrep) and update in small, verifiable chunks.
- Validate by running impacted test files first (browse executor, adapter, routes), then the full suite.
