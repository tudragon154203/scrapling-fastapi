import sys
import types

import pytest


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
    """Uses original single-attempt path and returns success with stub."""
    from app.services.crawler.generic import crawl_generic
    from app.schemas.crawl import CrawlRequest

    # Force max_retries=1
    class MockSettings:
        max_retries = 1
        default_headless = True
        default_network_idle = False
        default_timeout_ms = 5000

    monkeypatch.setattr("app.core.config.get_settings", lambda: MockSettings())

    calls = _install_fake_scrapling(monkeypatch, side_effects=[200])

    req = CrawlRequest(
        url="https://example.com",
        wait_selector="body",
        wait_selector_state="visible",
        timeout_ms=5000,
        headless=True,
        network_idle=True,
    )

    res = crawl_generic(req)
    assert res.status == "success"
    assert calls["count"] == 1


def test_generic_crawl_with_max_retries_greater_than_one(monkeypatch):
    """Uses retry path but succeeds on first attempt with stub."""
    from app.services.crawler.generic import crawl_generic
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

    monkeypatch.setattr("app.core.config.get_settings", lambda: MockSettings())
    calls = _install_fake_scrapling(monkeypatch, side_effects=[200])

    req = CrawlRequest(
        url="https://example.com",
        wait_selector="body",
        wait_selector_state="visible",
        timeout_ms=5000,
        headless=True,
        network_idle=True,
    )

    res = crawl_generic(req)
    assert res.status == "success"
    assert calls["count"] == 1
