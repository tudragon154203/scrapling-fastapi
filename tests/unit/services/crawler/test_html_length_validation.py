import sys
import types
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit]


def _make_request():
    from app.schemas.crawl import CrawlRequest

    return CrawlRequest(
        url="https://example.com",
        wait_for_selector="body",
        wait_for_selector_state="visible",
        timeout_seconds=2,
        network_idle=False,
    )


def _install_fake_scrapling_with_html_lengths(monkeypatch, html_lengths):
    """Install a fake StealthyFetcher that returns 200 with specified html lengths per attempt."""
    calls = {"count": 0}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):
            idx = calls["count"]
            calls["count"] += 1
            length = html_lengths[min(idx, len(html_lengths) - 1)]
            obj = types.SimpleNamespace()
            obj.status = 200
            obj.html_content = "<" + ("x" * max(0, length - 2)) + ">"  # crude string of desired length
            return obj

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)
    return calls


def test_single_attempt_fails_on_short_html(monkeypatch):
    from app.services.common.engine import CrawlerEngine

    class MockSettings:
        max_retries = 1
        default_headless = True
        default_network_idle = False
        default_timeout_ms = 2000
        min_html_content_length = 500

    monkeypatch.setattr("app.core.config.get_settings", lambda: MockSettings())
    _install_fake_scrapling_with_html_lengths(monkeypatch, html_lengths=[100])

    engine = CrawlerEngine.from_settings(MockSettings())
    res = engine.run(_make_request())
    assert res.status == "failure"
    assert res.html is None
    assert "HTML too short" in (res.message or "")


def test_retry_succeeds_after_short_html_then_long(monkeypatch):
    from app.services.common.engine import CrawlerEngine

    class MockSettings:
        max_retries = 3
        retry_backoff_base_ms = 1
        retry_backoff_max_ms = 1
        retry_jitter_ms = 0
        proxy_list_file_path = None
        private_proxy_url = None
        proxy_rotation_mode = "sequential"
        default_headless = True
        default_network_idle = False
        default_timeout_ms = 2000
        proxy_health_failure_threshold = 2
        proxy_unhealthy_cooldown_minute = 1
        min_html_content_length = 500

    monkeypatch.setattr("app.core.config.get_settings", lambda: MockSettings())
    calls = _install_fake_scrapling_with_html_lengths(monkeypatch, html_lengths=[100, 200, 800])

    with patch("time.sleep"):
        engine = CrawlerEngine.from_settings(MockSettings())
        res = engine.run(_make_request())

    assert res.status == "success"
    assert calls["count"] == 3
    assert res.html and len(res.html) >= 500
