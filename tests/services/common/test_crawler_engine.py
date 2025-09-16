from app.core.config import Settings
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.common import engine as engine_module
from app.services.common.engine import CrawlerEngine
from app.services.crawler.executors.retry_executor import RetryingExecutor
from app.services.crawler.executors.single_executor import SingleAttemptExecutor


class DummyExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, request, page_action=None):
        self.calls.append((request, page_action))
        return CrawlResponse(status="success", url=request.url, html="ok")


def make_request(url: str = "https://example.com") -> CrawlRequest:
    return CrawlRequest(url=url)


def test_crawler_engine_from_settings_single_executor():
    settings = Settings(max_retries=1)

    engine = CrawlerEngine.from_settings(settings)

    assert isinstance(engine.executor, SingleAttemptExecutor)
    assert isinstance(engine.fetch_client, engine_module.ScraplingFetcherAdapter)
    assert isinstance(engine.options_resolver, engine_module.OptionsResolver)
    assert isinstance(engine.camoufox_builder, engine_module.CamoufoxArgsBuilder)


def test_crawler_engine_from_settings_retry_executor(monkeypatch):
    sentinel_backoff = object()
    sentinel_tracker = object()
    captured_settings = {}

    def fake_from_settings(cls, settings):
        captured_settings["value"] = settings
        return sentinel_backoff

    monkeypatch.setattr(
        engine_module.BackoffPolicy,
        "from_settings",
        classmethod(fake_from_settings),
    )
    monkeypatch.setattr(engine_module, "get_health_tracker", lambda: sentinel_tracker)

    settings = Settings(max_retries=3)

    engine = CrawlerEngine.from_settings(settings)

    assert isinstance(engine.executor, RetryingExecutor)
    assert engine.executor.backoff_policy is sentinel_backoff
    assert engine.executor.health_tracker is sentinel_tracker
    assert captured_settings["value"] is settings


def test_crawler_engine_run_uses_existing_executor():
    request = make_request()
    executor = DummyExecutor()
    engine = CrawlerEngine(executor=executor)
    page_action = object()

    response = engine.run(request, page_action=page_action)

    assert response.status == "success"
    assert executor.calls == [(request, page_action)]


def test_crawler_engine_run_creates_executor_on_demand(monkeypatch):
    sentinel_settings = Settings(max_retries=1)
    created_executor = DummyExecutor()
    created = {"count": 0}

    def fake_get_settings():
        return sentinel_settings

    def fake_create(self, settings):
        created["count"] += 1
        assert settings is sentinel_settings
        return created_executor

    monkeypatch.setattr(engine_module.app_config, "get_settings", fake_get_settings)
    monkeypatch.setattr(CrawlerEngine, "_create_executor", fake_create)

    engine = CrawlerEngine(executor=None)
    request = make_request()

    response = engine.run(request)

    assert response.status == "success"
    assert engine.executor is created_executor
    assert created_executor.calls == [(request, None)]
    assert created["count"] == 1


def test_crawler_engine_create_single_executor_reuses_components():
    fetch_client = object()
    options_resolver = object()
    camoufox_builder = object()
    engine = CrawlerEngine(
        fetch_client=fetch_client,
        options_resolver=options_resolver,
        camoufox_builder=camoufox_builder,
    )

    executor = engine._create_executor(Settings(max_retries=1))

    assert isinstance(executor, SingleAttemptExecutor)
    assert executor.fetch_client is fetch_client
    assert executor.options_resolver is options_resolver
    assert executor.camoufox_builder is camoufox_builder


def test_crawler_engine_create_retry_executor_reuses_components(monkeypatch):
    fetch_client = object()
    options_resolver = object()
    camoufox_builder = object()
    attempt_planner = object()
    health_tracker = object()
    sentinel_backoff = object()

    def fake_from_settings(cls, settings):
        return sentinel_backoff

    monkeypatch.setattr(
        engine_module.BackoffPolicy,
        "from_settings",
        classmethod(fake_from_settings),
    )

    engine = CrawlerEngine(
        fetch_client=fetch_client,
        options_resolver=options_resolver,
        camoufox_builder=camoufox_builder,
        attempt_planner=attempt_planner,
        health_tracker=health_tracker,
    )

    executor = engine._create_executor(Settings(max_retries=2))

    assert isinstance(executor, RetryingExecutor)
    assert executor.fetch_client is fetch_client
    assert executor.options_resolver is options_resolver
    assert executor.camoufox_builder is camoufox_builder
    assert executor.attempt_planner is attempt_planner
    assert executor.health_tracker is health_tracker
    assert executor.backoff_policy is sentinel_backoff


def test_crawler_engine_retry_executor_uses_health_tracker_fallback(monkeypatch):
    sentinel_tracker = object()

    monkeypatch.setattr(engine_module, "get_health_tracker", lambda: sentinel_tracker)

    engine = CrawlerEngine(fetch_client=object(), options_resolver=object(), camoufox_builder=object())

    executor = engine._create_executor(Settings(max_retries=5))

    assert isinstance(executor, RetryingExecutor)
    assert executor.health_tracker is sentinel_tracker
