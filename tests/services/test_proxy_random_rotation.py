import sys
import types
import tempfile
from unittest.mock import patch

import pytest

from app.services.crawler.executors.retry import execute_crawl_with_retries
from app.services.crawler.utils.proxy import health_tracker, reset_health_tracker
from app.schemas.crawl import CrawlRequest


def _install_fake_scrapling_track_proxies(monkeypatch, statuses):
    """Install fake scrapling that records the `proxy` kwarg and yields statuses.

    `statuses` is a list of int HTTP codes to cycle through (last value repeats).
    """
    calls = {"count": 0, "proxies_used": []}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, proxy=None, **kwargs):
            calls["proxies_used"].append(proxy)
            idx = calls["count"]
            calls["count"] += 1
            status = statuses[min(idx, len(statuses) - 1)]
            obj = types.SimpleNamespace()
            obj.status = int(status)
            obj.html_content = f"<html>attempt-{idx+1}</html>"
            return obj

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)
    return calls


def _mock_settings_random(proxy_file, private_proxy_url=None, max_retries=5, threshold=999):
    class MockSettings:
        pass

    s = MockSettings()
    s.max_retries = max_retries
    s.retry_backoff_base_ms = 1
    s.retry_backoff_max_ms = 1
    s.retry_jitter_ms = 0
    s.proxy_list_file_path = proxy_file
    s.private_proxy_url = private_proxy_url
    s.proxy_rotation_mode = "random"
    s.default_headless = True
    s.default_network_idle = False
    s.default_timeout_ms = 2000
    s.proxy_health_failure_threshold = threshold
    s.proxy_unhealthy_cooldown_ms = 60_000
    return s


def _make_request():
    return CrawlRequest(
        url="https://example.com",
        wait_selector="body",
        wait_selector_state="visible",
        timeout_ms=2000,
        headless=True,
        network_idle=False,
    )


def test_random_rotation_seeded_no_immediate_repetition(monkeypatch):
    """With seeded RNG, selection is deterministic and avoids immediate repetition."""
    reset_health_tracker()

    # Two public proxies; no private
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("127.0.0.1:8080\n127.0.0.2:8080\n")
        proxy_file = f.name

    try:
        settings = _mock_settings_random(proxy_file, private_proxy_url=None, max_retries=5, threshold=999)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        calls = _install_fake_scrapling_track_proxies(monkeypatch, statuses=[500, 500, 500, 500, 500])

        # Seed RNG for determinism; patch sleep to speed up
        import random

        random.seed(42)
        with patch("time.sleep"):
            res = execute_crawl_with_retries(_make_request())

        assert res.status == "failure"  # all attempts fail
        # Should have used a proxy on every attempt (no direct)
        assert len(calls["proxies_used"]) == settings.max_retries
        # Ensure only the two public proxies are used and no immediate repetition
        p1 = "socks5://127.0.0.1:8080"
        p2 = "socks5://127.0.0.2:8080"
        used = calls["proxies_used"]
        assert set(used).issubset({p1, p2})
        assert all(used[i] != used[i+1] for i in range(len(used)-1))
    finally:
        import os
        os.unlink(proxy_file)


def test_random_rotation_skips_unhealthy_proxies(monkeypatch):
    """Pre-mark a proxy unhealthy; random selection should never pick it."""
    reset_health_tracker()

    # Two public proxies; mark the first as unhealthy
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("127.0.0.1:8080\n127.0.0.2:8080\n")
        proxy_file = f.name

    try:
        settings = _mock_settings_random(proxy_file, private_proxy_url=None, max_retries=3, threshold=999)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        # Mark first proxy unhealthy far into the future
        bad = "socks5://127.0.0.1:8080"
        health_tracker[bad] = {"failures": 2, "unhealthy_until": 10**9}

        calls = _install_fake_scrapling_track_proxies(monkeypatch, statuses=[500, 500, 500])

        import random

        random.seed(1)
        with patch("time.sleep"), patch("time.time", return_value=100.0):
            res = execute_crawl_with_retries(_make_request())

        assert res.status == "failure"
        used = calls["proxies_used"]
        # Unhealthy proxy should never be used
        assert bad not in used
        # Only the second proxy is used
        assert set(used) == {"socks5://127.0.0.2:8080"}
    finally:
        import os
        os.unlink(proxy_file)
