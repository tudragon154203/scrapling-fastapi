import sys
import types
from unittest.mock import patch

import pytest


def _install_fake_scrapling(monkeypatch, side_effects):
    """Install fake scrapling.fetchers with a StealthyFetcher.fetch sequence.

    side_effects: list of items; each item is either an Exception to raise
    or an int HTTP status code to return in the stubbed response.
    """
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
            obj = types.SimpleNamespace()
            obj.status = int(action)
            obj.html_content = f"<html>attempt-{idx+1}</html>"
            return obj

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)
    return calls


def _mock_settings(max_retries=3):
    class MockSettings:
        pass

    settings = MockSettings()
    settings.max_retries = max_retries
    settings.retry_backoff_base_ms = 1
    settings.retry_backoff_max_ms = 1
    settings.retry_jitter_ms = 0
    settings.proxy_list_file_path = None
    settings.private_proxy_url = None
    settings.proxy_rotation_mode = "sequential"
    settings.default_headless = True
    settings.default_network_idle = False
    settings.default_timeout_ms = 2000
    settings.min_html_content_length = 1

    return settings


def _make_request():
    from app.schemas.crawl import CrawlRequest

    return CrawlRequest(
        url="https://example.com",
        wait_selector="body",
        wait_selector_state="visible",
        timeout_ms=2000,
        headless=True,
        network_idle=False,
    )


def test_retry_success_on_second_attempt(monkeypatch):
    from app.services.crawler.core.engine import CrawlerEngine

    # Patch settings and scrapling
    monkeypatch.setattr("app.core.config.get_settings", lambda: _mock_settings(max_retries=3))
    calls = _install_fake_scrapling(monkeypatch, side_effects=[Exception("boom"), 200])

    # Avoid sleeping in tests
    with patch("time.sleep") as mocked_sleep:
        res = CrawlerEngine.from_settings(_mock_settings(max_retries=3)).run(_make_request())

    assert res.status == "success"
    assert "attempt-2" in (res.html or "")
    assert calls["count"] == 2
    # One backoff between attempt 1 and 2
    assert mocked_sleep.call_count == 1


def test_retry_failure_after_exhausting_attempts(monkeypatch):
    from app.services.crawler.core.engine import CrawlerEngine

    monkeypatch.setattr("app.core.config.get_settings", lambda: _mock_settings(max_retries=3))
    calls = _install_fake_scrapling(monkeypatch, side_effects=[500, 500, 500])

    with patch("time.sleep") as mocked_sleep:
        res = CrawlerEngine.from_settings(_mock_settings(max_retries=3)).run(_make_request())

    assert res.status == "failure"
    assert res.html is None
    assert res.message and "Non-200 status: 500" in res.message
    assert calls["count"] == 3
    # Backoff between attempts: max_retries - 1 times
    assert mocked_sleep.call_count == 2


def test_retry_non200_then_success(monkeypatch):
    from app.services.crawler.core.engine import CrawlerEngine

    monkeypatch.setattr("app.core.config.get_settings", lambda: _mock_settings(max_retries=3))
    calls = _install_fake_scrapling(monkeypatch, side_effects=[500, 200])

    with patch("time.sleep") as mocked_sleep:
        res = CrawlerEngine.from_settings(_mock_settings(max_retries=3)).run(_make_request())

    assert res.status == "success"
    assert calls["count"] == 2
    assert mocked_sleep.call_count == 1
