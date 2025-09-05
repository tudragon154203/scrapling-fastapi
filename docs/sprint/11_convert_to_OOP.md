# Sprint 11 — Crawler Service OOP Refactor Spec

This document proposes an object‑oriented redesign of the crawler services to improve maintainability, readability, and testability. It focuses on `app/services/crawler` while preserving public APIs and behavior.

## Goals

- Maintain behavior and API compatibility while refactoring internals
- Separate concerns: orchestration, execution, fetch, options, proxies, and page actions
- Improve extensibility (e.g., new carriers, custom retry/backoff, proxy strategies)
- Enable focused unit testing of smaller, well‑named components
- Reduce ad‑hoc globals and implicit coupling

## Non‑Goals

- Changing FastAPI endpoints or request/response schemas
- Switching libraries (we continue to adapt to Scrapling + Camoufox)
- Introducing async endpoints (we keep current sync boundaries)

## Current State (Key Touchpoints)

- Generic selection logic
  - app/services/crawler/generic.py:1
  - `crawl_generic` picks single vs retry based on settings

- Executors (functional style + helpers)
  - app/services/crawler/executors/single.py:14 — `crawl_single_attempt`
  - app/services/crawler/executors/retry.py:32 — `execute_crawl_with_retries`
  - app/services/crawler/executors/retry.py:24 — `_calculate_backoff_delay`

- Fetch utilities (introspection, kwargs composition, event‑loop workaround)
  - app/services/crawler/utils/fetch.py:12 — `_detect_fetch_capabilities`
  - app/services/crawler/utils/fetch.py:47 — `_compose_fetch_kwargs`
  - app/services/crawler/utils/fetch.py:85 — `_call_stealthy_fetch`

- Options utilities (defaults, Camoufox args)
  - app/services/crawler/utils/options.py:25 — `_resolve_effective_options`
  - app/services/crawler/utils/options.py:67 — `_build_camoufox_args`

- Proxy utilities (stateful global health tracker, planning)
  - app/services/crawler/utils/proxy.py:5 — `health_tracker` (global)
  - app/services/crawler/utils/proxy.py:28 — `_load_public_proxies`
  - app/services/crawler/utils/proxy.py:47 — `_select_proxy_for_request`
  - app/services/crawler/utils/proxy.py:80 — `_build_attempt_plan`

- Carrier‑specific orchestration
  - app/services/crawler/dpd.py:70 — `crawl_dpd`
  - app/services/crawler/auspost.py:215 — `crawl_auspost`


## Proposed OOP Design

### High‑Level Architecture

- CrawlerEngine (Facade/Orchestrator)
  - Decides which execution strategy to use (single vs retry) based on `Settings`
  - Composes dependencies: Executor, FetchClient, OptionsResolver, Proxy components
  - Public entry: `run(request: CrawlRequest, page_action: Optional[PageAction]) -> CrawlResponse`

- Executors (Strategy)
  - `SingleAttemptExecutor.execute(request, page_action) -> CrawlResponse`
  - `RetryingExecutor.execute(request, page_action) -> CrawlResponse`
    - Depends on `BackoffPolicy`, `AttemptPlanner`, `ProxyHealthTracker`

- Fetch (Adapter + Capability Detection)
  - `FetchClient` interface implemented by `ScraplingFetcherAdapter`
    - Bridges to `scrapling.fetchers.StealthyFetcher.fetch`
    - Handles capability detection and event‑loop workaround
  - `FetchArgComposer` composes safe kwargs for fetch based on capabilities

- Options (Resolver + Builder)
  - `OptionsResolver.resolve(request, settings) -> CrawlOptions`
    - Consolidates legacy/new fields and defaults
  - `CamoufoxArgsBuilder.build(payload, settings, caps) -> (additional_args, extra_headers)`

- Proxies (Providers + Health + Planning)
  - `ProxyListSource` loads public proxies from file
  - `ProxyHealthTracker` (stateful; thread‑safe) stores failures and cooldowns
  - `AttemptPlanner` builds attempt plan (direct/public/private) respecting mode and health
  - `ProxyRedactor` formats proxy URLs for logs

- Page Actions (Command/Callable)
  - `PageAction` protocol: `apply(page) -> Any`
  - Carrier‑specific implementations (e.g., `AuspostTrackAction`)

- Carrier Crawlers (Composable)
  - `DPDCrawler` uses `CrawlerEngine` without `PageAction`
  - `AuspostCrawler` supplies `PageAction` to automate the form flow


### Interfaces and Responsibilities

- ICrawlerEngine
  - `run(request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse`
  - Composes: `IExecutor`, `IFetchClient`, `IOptionsResolver`, `IAttemptPlanner`, `IProxyHealthTracker`, `IBackoffPolicy`

- IExecutor
  - `execute(request, page_action) -> CrawlResponse`
  - Implementations: `SingleAttemptExecutor`, `RetryingExecutor`

- IFetchClient
  - `fetch(url: str, args: FetchArgs) -> Page`
  - `detect_capabilities() -> FetchCapabilities`
  - Bridges Scrapling’s `StealthyFetcher.fetch`

- IOptionsResolver
  - `resolve(request: CrawlRequest, settings: Settings) -> CrawlOptions`
  - Converts legacy fields; centralizes headless/network_idle/timeout decisions

- IFetchArgComposer
  - `compose(options, caps, proxy, additional_args, extra_headers, page_action) -> dict`

- IBackoffPolicy
  - `delay_for_attempt(attempt_idx: int) -> float`

- IAttemptPlanner
  - `build_plan(settings, public_proxies) -> list[Attempt]`

- IProxyListSource
  - `load() -> list[str]`

- IProxyHealthTracker
  - `mark_failure(proxy)`, `mark_success(proxy)`, `is_unhealthy(proxy) -> bool`, `reset()`

- PageAction (Protocol)
  - `apply(page) -> Any` (or `__call__(page)`)


### Class Mapping (from current functions)

- `generic.crawl_generic` → `CrawlerEngine.run`
  - app/services/crawler/generic.py:1

- `executors.single.crawl_single_attempt` → `SingleAttemptExecutor.execute`
  - app/services/crawler/executors/single.py:14

- `executors.retry.execute_crawl_with_retries` → `RetryingExecutor.execute`
  - app/services/crawler/executors/retry.py:32

- `executors.retry._calculate_backoff_delay` → `BackoffPolicy.delay_for_attempt`
  - app/services/crawler/executors/retry.py:24

- `utils.fetch._detect_fetch_capabilities` → `ScraplingFetcherAdapter.detect_capabilities`
  - app/services/crawler/utils/fetch.py:12

- `utils.fetch._compose_fetch_kwargs` → `FetchArgComposer.compose`
  - app/services/crawler/utils/fetch.py:47

- `utils.fetch._call_stealthy_fetch` → `ScraplingFetcherAdapter.fetch` (internal strategy)
  - app/services/crawler/utils/fetch.py:85

- `utils.options._resolve_effective_options` → `OptionsResolver.resolve`
  - app/services/crawler/utils/options.py:25

- `utils.options._build_camoufox_args` → `CamoufoxArgsBuilder.build`
  - app/services/crawler/utils/options.py:67

- `utils.proxy.health_tracker` (global dict) → `ProxyHealthTracker` (instance; module singleton exposed for compat)
  - app/services/crawler/utils/proxy.py:5

- `utils.proxy._load_public_proxies` → `ProxyListFileSource.load`
  - app/services/crawler/utils/proxy.py:28

- `utils.proxy._build_attempt_plan` → `AttemptPlanner.build_plan`
  - app/services/crawler/utils/proxy.py:80

- `dpd.crawl_dpd` → `DPDCrawler.run`
  - app/services/crawler/dpd.py:70

- `auspost.crawl_auspost` → `AuspostCrawler.run` + `AuspostTrackAction`
  - app/services/crawler/auspost.py:215


### Proposed Module Layout

Keep package boundaries familiar; introduce `core/` and `adapters/` while evolving existing folders.

```
app/services/crawler/
  core/
    engine.py            # CrawlerEngine (Facade)
    interfaces.py        # Protocols/ABCs: IExecutor, IFetchClient, etc.
    types.py             # CrawlOptions, FetchArgs, Attempt dataclasses

  executors/
    single_executor.py   # SingleAttemptExecutor
    retry_executor.py    # RetryingExecutor + uses BackoffPolicy
    backoff.py           # BackoffPolicy (configurable)
    __init__.py

  adapters/
    scrapling_fetcher.py # ScraplingFetcherAdapter (capabilities + thread/loop strategy)
    __init__.py

  options/
    resolver.py          # OptionsResolver
    camoufox.py          # CamoufoxArgsBuilder
    __init__.py

  proxy/
    health.py            # ProxyHealthTracker (module singleton exposed for compat)
    plan.py              # AttemptPlanner
    sources.py           # ProxyListFileSource
    redact.py            # ProxyRedactor
    __init__.py

  actions/
    base.py              # PageAction protocol
    auspost.py           # AuspostTrackAction
    __init__.py

  crawlers/
    generic.py           # GenericCrawler (thin) using CrawlerEngine
    dpd.py               # DPDCrawler
    auspost.py           # AuspostCrawler
    __init__.py

  __init__.py           # package doc, public API exports
```

Notes:
- Keep current top‑level functions as thin wrappers that delegate to classes to avoid breaking imports/tests during migration.
- Preserve `health_tracker` as a module‑level alias to the singleton’s internal store to maintain test hooks (`reset_health_tracker`).


### Behavior Preservation Guidelines

- Windows event loop policy fix must remain in the fetch path (inside adapter) to mirror `retry.py` behavior.
- `min_html_content_length` validation remains in executors before success return.
- `private_proxy_url` and public proxy logic must preserve current attempt ordering and health skipping in both sequential and random modes.
- Logging messages should retain current signal (redacted proxies, success/failure reasons) though can be slightly rephrased.


## Incremental Migration Plan

Phase 1 — Foundations (no behavior change)
- Introduce `interfaces.py` and `types.py` (dataclasses/Protocols) alongside existing code
- Add `ScraplingFetcherAdapter` using existing utils: call into `_detect_fetch_capabilities` and `_call_stealthy_fetch` initially
- Add `OptionsResolver` and `CamoufoxArgsBuilder` calling current `_resolve_effective_options` / `_build_camoufox_args`
- Add `ProxyHealthTracker` (backed by current `health_tracker` dict for now); expose `reset()` to keep tests green

Phase 2 — Executors
- Implement `SingleAttemptExecutor` and `RetryingExecutor` reusing current logic
- Move `_calculate_backoff_delay` into `BackoffPolicy`
- Move attempt plan logic into `AttemptPlanner` (preserve existing behavior for sequential/random)
- Keep old functions (`crawl_single_attempt`, `execute_crawl_with_retries`) as wrappers that instantiate and delegate

Phase 3 — Engine and Generic Crawler
- Implement `CrawlerEngine` to decide single vs retry based on settings
- Replace `generic.crawl_generic` with wrapper delegating to the engine

Phase 4 — Carrier Crawlers and PageActions
- Extract AusPost page automation into `AuspostTrackAction`
- Implement `DPDCrawler` and `AuspostCrawler` using engine; keep `crawl_dpd`/`crawl_auspost` wrappers

Phase 5 — Utils Consolidation and Cleanup
- Inline `_detect_fetch_capabilities`, `_compose_fetch_kwargs`, `_call_stealthy_fetch` into adapter/composer classes
- Move proxy helpers into `proxy/` package files
- Deprecate old utils with compatibility shims

Phase 6 — Test Hardening
- Keep all existing tests passing through wrappers
- Add unit tests for: BackoffPolicy, AttemptPlanner, ProxyHealthTracker, OptionsResolver, FetchArgComposer
- Gradually retarget tests to class boundaries (optional)


## Acceptance Criteria

- All existing tests remain green without changes
- Public FastAPI endpoints continue to return the same shapes and semantics
- `health_tracker` and `reset_health_tracker()` test hooks remain available
- Proxy rotation and health behavior matches current tests (sequential and random)
- Logging includes redacted proxy info and explicit outcomes per attempt


## Design Details

- Dependency Injection
  - Provide a small factory: `CrawlerEngineFactory.from_settings(settings)` to assemble default components
  - Allow overriding components (e.g., a different BackoffPolicy) for tests or advanced users

- Thread‑Safety
  - `ProxyHealthTracker` should guard its map with a threading lock (granularity: per‑proxy or global)
  - `ScraplingFetcherAdapter` confines event‑loop detection and thread handoff internally

- Configuration
  - Continue using `app.core.config.get_settings()` as the primary source
  - `OptionsResolver` owns headless/network_idle/timeout resolution rules (including platform quirks)

- Error Handling
  - Define internal exception types (e.g., `FetchError`, `InvalidResponseError`), but map to current `CrawlResponse.status/message` consistently in executors

- Observability (optional, later)
  - Add structured attempt logs and counters (success/failure per proxy)
  - Expose a health snapshot API (internal) via `ProxyHealthTracker`


## Function → Class Wrapper Stubs (API Compatibility)

Keep these wrappers in place initially (names unchanged; implemented via classes internally):
- `crawl_generic(payload)` → `CrawlerEngine.run(payload)`
- `crawl_single_attempt(payload, page_action=None)` → `SingleAttemptExecutor.execute(...)`
- `execute_crawl_with_retries(payload, page_action=None)` → `RetryingExecutor.execute(...)`
- `crawl_dpd(request)` → `DPDCrawler.run(...)`
- `crawl_auspost(request)` → `AuspostCrawler.run(...)`

Rationale: avoids breaking `app/api/routes.py` and existing tests while enabling class testing in parallel.


## Risk & Mitigations

- Risk: Divergence between old utils and new classes
  - Mitigation: thin wrappers call class methods; delete old utils only after test parity

- Risk: Subtle timing differences (backoff, waits)
  - Mitigation: encapsulate calculations in `BackoffPolicy`; unit test with seeded/jitterless configs

- Risk: Global state changes (proxy health)
  - Mitigation: preserve a module‑level singleton and existing reset helpers until tests are migrated


## Future Enhancements

- Pluggable carriers registry (strategy lookup by carrier code)
- Metrics hooks (OpenTelemetry) at executor/attempt level
- Circuit breaker around private proxy
- Caching layer for static assets / rate limit guardrails


## Appendix A — Example Composition Flow (Retry)

1) `CrawlerEngine.run(request)` decides `RetryingExecutor`
2) `OptionsResolver.resolve(request, settings)` returns `CrawlOptions`
3) `ScraplingFetcherAdapter.detect_capabilities()` guides `CamoufoxArgsBuilder` and `FetchArgComposer`
4) `ProxyListSource.load()` and `AttemptPlanner.build_plan()` create attempt plan
5) For each attempt:
   - Check `ProxyHealthTracker.is_unhealthy(proxy)`
   - `FetchArgComposer.compose(...)` builds kwargs
   - `ScraplingFetcherAdapter.fetch(url, args)` performs call (thread handoff if event loop detected)
   - Validate status/html; mark success/failure in `ProxyHealthTracker`
   - `BackoffPolicy.delay_for_attempt(idx)` computes sleep before next attempt


## Appendix B — Test Impact

- Keep current tests unchanged initially; wrappers maintain behavior
- Add new focused tests for: `BackoffPolicy`, `AttemptPlanner`, `ProxyHealthTracker`, `OptionsResolver`, `FetchArgComposer`
- Prefer deterministic configs in tests (e.g., backoff jitter=0, seeded RNG) as seen in existing tests


## Out of Scope

- Converting endpoints to async
- Changing Pydantic models (`app/schemas`)
- External network I/O behavior beyond current settings


---
Owner: Team Backend
Sprint: 11
Status: Proposed (Specs only; no implementation in this sprint doc)

