# Sprint 11 — Crawler Service OOP Refactor Spec (Breaking)

This document proposes an object‑oriented redesign of the crawler services to improve maintainability, readability, and testability. It focuses on `app/services/crawler` and intentionally introduces a breaking change: remove legacy wrappers and compatibility shims.

## Goals

- Deliver a clean, object-oriented crawler architecture with explicit components
- Separate concerns: orchestration, execution, fetch, options, proxies, and page actions
- Improve extensibility (e.g., new carriers, custom retry/backoff, proxy strategies)
- Enable focused unit testing of smaller, well‑named components
- Reduce ad‑hoc globals and implicit coupling
- Accept a breaking change: remove legacy wrappers and compatibility shims

## Non‑Goals

- Changing FastAPI endpoints or request/response schemas
- Switching libraries (we continue to adapt to Scrapling + Camoufox)
- Introducing async endpoints (we keep current sync boundaries)

## Current State (Key Touchpoints)

- Generic selection logic
  - `app/services/crawler/generic.py`
- Executors
  - `app/services/crawler/executors/single_executor.py`
  - `app/services/crawler/executors/retry_executor.py`
- Fetch adapter + arg composition
  - `app/services/crawler/adapters/scrapling_fetcher.py`
- Options (defaults, Camoufox args)
  - `app/services/crawler/options/resolver.py`
  - `app/services/crawler/options/camoufox.py`
- Proxy components
  - `app/services/crawler/proxy/health.py`
  - `app/services/crawler/proxy/plan.py`
  - `app/services/crawler/proxy/sources.py`
  - `app/services/crawler/proxy/redact.py`
- Carrier‑specific orchestration
  - `app/services/crawler/dpd.py`
  - `app/services/crawler/auspost.py`

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
    - Handles capability detection and event loop conflicts
  - `FetchArgComposer` composes safe kwargs for fetch based on capabilities
- Options (Resolver + Builder)
  - `OptionsResolver.resolve(request, settings) -> CrawlOptions` (legacy/new fields and defaults)
  - `CamoufoxArgsBuilder.build(payload, settings, caps) -> (additional_args, extra_headers)`
- Proxies (Providers + Health + Planning)
  - `ProxyListSource` loads public proxies from file
  - `ProxyHealthTracker` (thread‑safe) stores failures and cooldowns (singleton via `get_health_tracker()`)
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
  - `fetch(url: str, args: dict) -> Page`
  - `detect_capabilities() -> FetchCapabilities`
- IOptionsResolver
  - `resolve(request: CrawlRequest, settings: Settings) -> dict`
- IFetchArgComposer
  - `compose(options, caps, proxy, additional_args, extra_headers, settings, page_action) -> dict`
- IBackoffPolicy
  - `delay_for_attempt(attempt_idx: int) -> float`
- IAttemptPlanner
  - `build_plan(settings, public_proxies) -> list[Attempt]`
- IProxyListSource
  - `load() -> list[str]`
- IProxyHealthTracker
  - `mark_failure(proxy)`, `mark_success(proxy)`, `is_unhealthy(proxy) -> bool`, `reset()`
- PageAction (Protocol)
  - `apply(page) -> Any`

### Proposed Module Layout

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
    health.py            # ProxyHealthTracker (singleton via get_health_tracker())
    plan.py              # AttemptPlanner
    sources.py           # ProxyListFileSource
    redact.py            # ProxyRedactor
    __init__.py

  actions/
    base.py              # PageAction protocol
    auspost.py           # AuspostTrackAction
    __init__.py

  generic.py           # GenericCrawler (thin) using CrawlerEngine
  dpd.py               # DPDCrawler
  auspost.py           # AuspostCrawler

  __init__.py           # package doc, public API exports
```

Notes:

- This refactor is intentionally breaking: remove legacy top‑level function wrappers and do not preserve old imports.
- Tests are rewritten to target the new classes and interfaces directly.
- Access proxy health exclusively via `get_health_tracker()`; do not mutate a module‑level dict.

### Behavior Preservation Guidelines

- Windows event loop policy fix should remain in the fetch path (adapter) or executor to mirror prior behavior.
- `min_html_content_length` validation remains in executors before success return.
- `private_proxy_url` and public proxy logic must preserve attempt ordering and health skipping in both sequential and random modes.
- Logging messages should retain current signal (redacted proxies, success/failure reasons) though can be slightly rephrased.

## Migration Plan (Breaking)

- Replace legacy utility modules and functions with class implementations.
- Remove function wrappers (`crawl_generic`, `execute_crawl_with_retries`, etc.).
- Update FastAPI routes to use new crawlers (already done) and remove any references to old functions.
- Rewrite tests to target new classes: `CrawlerEngine`, `SingleAttemptExecutor`, `RetryingExecutor`, `BackoffPolicy`, `AttemptPlanner`, `ProxyListFileSource`, `ProxyHealthTracker`, `OptionsResolver`, `FetchArgComposer`.
- Delete/deprecate old utils and compatibility shims without aliasing.

## Acceptance Criteria

- New test suite passes, targeting the OOP classes directly.
- Public FastAPI endpoints continue to return the same shapes and semantics.
- Proxy rotation and health behavior is preserved semantically (sequential and random), but APIs are class‑based only.
- Logging includes redacted proxy info and explicit outcomes per attempt.

## Design Details

- Dependency Injection
  - Provide a small factory: `CrawlerEngine.from_settings(settings)` to assemble default components
  - Allow overriding components (e.g., a different BackoffPolicy) for tests or advanced users
- Thread‑Safety
  - `ProxyHealthTracker` should guard its map with a threading lock (granularity: per‑proxy or global)
  - `ScraplingFetcherAdapter` confines event loop detection and thread handoff internally
- Configuration
  - Continue using `app.core.config.get_settings()` as the primary source
  - `OptionsResolver` owns headless/network_idle/timeout resolution rules (including platform quirks)
- Error Handling
  - Define internal exception types (e.g., `FetchError`, `InvalidResponseError`), but map to current `CrawlResponse.status/message` consistently in executors
- Observability (optional, later)
  - Add structured attempt logs and counters (success/failure per proxy)
  - Expose a health snapshot API (internal) via `ProxyHealthTracker`

## API Compatibility

This refactor intentionally removes legacy function wrappers and module‑level globals. Consumers must migrate to the new classes and interfaces (e.g., instantiate `GenericCrawler`/`DPDCrawler`/`AuspostCrawler`, or use `CrawlerEngine` directly). Tests and any internal call sites are updated accordingly.

## Risk & Mitigations

- Risk: Breaking changes require coordinated test updates
  - Mitigation: rewrite the suite to target new classes and stabilize via seeded configs
- Risk: Subtle timing differences (backoff, waits)
  - Mitigation: encapsulate calculations in `BackoffPolicy`; unit test with seeded/jitterless configs
- Risk: Global state changes (proxy health)
  - Mitigation: centralize via `ProxyHealthTracker` singleton and avoid mutable module dicts

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

- Replace tests that import legacy functions with tests that construct and call classes.
- Add focused tests for: `BackoffPolicy`, `AttemptPlanner`, `ProxyHealthTracker`, `OptionsResolver`, `FetchArgComposer`.
- Prefer deterministic configs in tests (e.g., jitter=0, seeded RNG) to ensure stability.

