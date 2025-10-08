import os
import sys
import types

import pytest

pytestmark = [pytest.mark.unit]


def _install_fake_scrapling(monkeypatch, side_effects):
    """Install a fake scrapling.fetchers.StealthyFetcher with programmable behavior."""
    calls = {"count": 0}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):
            idx = calls["count"]
            calls["count"] += 1
            action = side_effects[min(idx, len(side_effects) - 1)]
            if isinstance(action, Exception):
                raise action
            # treat action as HTTP status
            resp = types.SimpleNamespace()
            resp.status = int(action)
            resp.html_content = f"<html>attempt-{idx+1}</html>"
            return resp

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)
    return calls


def test_generic_crawl_with_max_retries_one(monkeypatch):
    """Single-attempt path returns success with stub using GenericCrawler."""
    from app.services.crawler.generic import GenericCrawler
    from app.schemas.crawl import CrawlRequest

    # Force max_retries=1
    class MockSettings:
        max_retries = 1
        default_headless = True
        default_network_idle = False
        default_timeout_ms = 5000
        min_html_content_length = 1

    monkeypatch.setattr("app.core.config.get_settings", lambda: MockSettings())

    calls = _install_fake_scrapling(monkeypatch, side_effects=[200])

    req = CrawlRequest(
        url="https://example.com",
        wait_for_selector="body",
        wait_for_selector_state="visible",
        timeout_seconds=5,
        network_idle=True,
    )

    crawler = GenericCrawler()
    res = crawler.run(req)
    assert res.status == "success"
    assert calls["count"] == 1


def test_generic_crawl_with_max_retries_greater_than_one(monkeypatch):
    """Retry path succeeds on first attempt with stub via GenericCrawler."""
    from app.services.crawler.generic import GenericCrawler
    from app.schemas.crawl import CrawlRequest

    class MockSettings:
        max_retries = 3
        retry_backoff_base_ms = 1
        retry_backoff_max_ms = 1
        retry_jitter_ms = 0
        proxy_list_file_path = None
        private_proxy_url = None
        default_headless = True
        default_network_idle = False
        default_timeout_ms = 5000
        min_html_content_length = 1

    monkeypatch.setattr("app.core.config.get_settings", lambda: MockSettings())
    calls = _install_fake_scrapling(monkeypatch, side_effects=[200])

    req = CrawlRequest(
        url="https://example.com",
        wait_for_selector="body",
        wait_for_selector_state="visible",
        timeout_seconds=5,
        network_idle=True,
    )

    crawler = GenericCrawler()
    res = crawler.run(req)
    assert res.status == "success"
    assert calls["count"] == 1


def test_user_data_with_supported_param(monkeypatch):
    """Test force_user_data=true with supported user_data_dir parameter (via patched builder)."""
    from app.services.crawler.generic import GenericCrawler
    from app.schemas.crawl import CrawlRequest

    class MockSettings:
        max_retries = 1
        default_headless = True
        default_network_idle = False
        default_timeout_ms = 5000
        camoufox_user_data_dir = "/tmp/test_user_data"
        min_html_content_length = 1

    monkeypatch.setattr("app.core.config.get_settings", lambda: MockSettings())

    # Mock fetch with user_data_dir support
    calls = {"count": 0, "kwargs": []}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):
            calls["count"] += 1
            calls["kwargs"].append(kwargs)
            resp = types.SimpleNamespace()
            resp.status = 200
            resp.html_content = "<html>test</html>"
            return resp

    # Mock signature to include user_data_dir
    import inspect
    fake_sig = inspect.Signature([
        inspect.Parameter('url', inspect.Parameter.POSITIONAL_OR_KEYWORD),
        inspect.Parameter('user_data_dir', inspect.Parameter.KEYWORD_ONLY),
        inspect.Parameter('additional_args', inspect.Parameter.KEYWORD_ONLY),
    ], return_annotation=None)

    FakeStealthyFetcher.fetch.__signature__ = fake_sig

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)

    # Patch CamoufoxArgsBuilder to return user_data_dir in additional_args
    from app.services.common.browser.camoufox import CamoufoxArgsBuilder

    def _fake_build(payload, settings, caps):
        clone_dir = os.path.join(settings.camoufox_user_data_dir, "clones", "test_clone")
        return {
            "user_data_dir": clone_dir
        }, None

    monkeypatch.setattr(CamoufoxArgsBuilder, "build", staticmethod(_fake_build))

    req = CrawlRequest(
        url="https://example.com",
        force_user_data=True,
    )

    crawler = GenericCrawler()
    res = crawler.run(req)
    assert res.status == "success"
    assert calls["count"] == 1
    # Check that user_data_dir was passed in additional_args
    kwargs = calls["kwargs"][0]
    assert "additional_args" in kwargs
    expected_dir = os.path.join("/tmp/test_user_data", "clones", "test_clone")
    assert kwargs["additional_args"]["user_data_dir"] == expected_dir


def test_user_data_without_env_var(monkeypatch):
    """Test force_user_data=true but no CAMOUFOX_USER_DATA_DIR set."""
    from app.services.crawler.generic import GenericCrawler
    from app.schemas.crawl import CrawlRequest

    class MockSettings:
        max_retries = 1
        default_headless = True
        default_network_idle = False
        default_timeout_ms = 5000
        camoufox_user_data_dir = None
        min_html_content_length = 1

    monkeypatch.setattr("app.core.config.get_settings", lambda: MockSettings())
    calls = _install_fake_scrapling(monkeypatch, side_effects=[200])

    req = CrawlRequest(
        url="https://example.com",
        force_user_data=True,
    )

    crawler = GenericCrawler()
    res = crawler.run(req)
    assert res.status == "success"
    assert calls["count"] == 1


def test_user_data_unsupported_param(monkeypatch):
    """Test force_user_data=true with unsupported user data parameters."""
    from app.services.crawler.generic import GenericCrawler
    from app.schemas.crawl import CrawlRequest

    class MockSettings:
        max_retries = 1
        default_headless = True
        default_network_idle = False
        default_timeout_ms = 5000
        camoufox_user_data_dir = "/tmp/test_user_data"
        min_html_content_length = 1

    monkeypatch.setattr("app.core.config.get_settings", lambda: MockSettings())

    # Mock fetch without user data support
    calls = {"count": 0, "kwargs": []}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):
            calls["count"] += 1
            calls["kwargs"].append(kwargs)
            resp = types.SimpleNamespace()
            resp.status = 200
            resp.html_content = "<html>test</html>"
            return resp

    # Mock signature without user data params
    import inspect
    fake_sig = inspect.Signature([
        inspect.Parameter('url', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ], return_annotation=None)

    FakeStealthyFetcher.fetch.__signature__ = fake_sig

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)

    req = CrawlRequest(
        url="https://example.com",
        force_user_data=True,
    )

    crawler = GenericCrawler()
    res = crawler.run(req)
    assert res.status == "success"
    assert calls["count"] == 1
    # Check that no user data parameters were passed
    kwargs = calls["kwargs"][0]
    if "additional_args" in kwargs:
        assert "user_data_dir" not in kwargs["additional_args"]
