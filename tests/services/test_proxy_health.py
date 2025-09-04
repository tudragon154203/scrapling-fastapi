import sys
import types
import tempfile
import os
from unittest.mock import patch

import pytest

from app.services.crawler.generic import execute_crawl_with_retries, health_tracker, reset_health_tracker
from app.schemas.crawl import CrawlRequest


def _install_fake_scrapling_with_proxy_tracking(monkeypatch, side_effects):
    """Install fake scrapling that tracks proxy usage."""
    calls = {"count": 0, "proxies_used": []}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, proxy=None, **kwargs):
            calls["proxies_used"].append(proxy)
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


def _mock_settings_health(proxy_list_file_path, private_proxy_url="socks5://127.0.0.1:1080"):
    class MockSettings:
        pass

    settings = MockSettings()
    settings.max_retries = 5
    settings.retry_backoff_base_ms = 1
    settings.retry_backoff_max_ms = 1
    settings.retry_jitter_ms = 0
    settings.proxy_list_file_path = proxy_list_file_path
    settings.private_proxy_url = private_proxy_url
    settings.proxy_rotation_mode = "sequential"
    settings.default_headless = True
    settings.default_network_idle = False
    settings.default_timeout_ms = 2000
    settings.proxy_health_failure_threshold = 2  # Low for testing
    settings.proxy_unhealthy_cooldown_ms = 1000  # 1 second for testing
    return settings


def _make_request():
    return CrawlRequest(
        url="https://example.com",
        wait_selector="body",
        wait_selector_state="visible",
        timeout_ms=2000,
        headless=True,
        network_idle=False,
    )


def test_proxy_marked_unhealthy_after_n_failures(monkeypatch):
    """Verify that after N consecutive failures, a proxy is marked unhealthy."""
    # Clear health tracker
    reset_health_tracker()

    # Create temporary proxy file with one proxy
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("127.0.0.1:8080\n")
        proxy_file = f.name

    try:
        # Mock settings
        settings = _mock_settings_health(proxy_file)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        # Install fake scrapling - force failures
        calls = _install_fake_scrapling_with_proxy_tracking(monkeypatch, side_effects=[500, 500, 500])  # 3 failures

        with patch("time.sleep"):
            with patch("time.time", return_value=1000.0):  # Fixed time
                res = execute_crawl_with_retries(_make_request())

        assert res.status == "failure"
        # The implementation tries more combinations: direct, public proxy, private, then retries
        assert calls["count"] >= 3  # Allow more attempts as per implementation

        # Check that proxy was marked unhealthy
        proxy_url = "socks5://127.0.0.1:8080"
        assert proxy_url in health_tracker
        ht = health_tracker[proxy_url]
        assert ht["failures"] == 2  # Threshold reached, marked unhealthy
        assert ht["unhealthy_until"] == 1000.0 + settings.proxy_unhealthy_cooldown_ms / 1000

    finally:
        os.unlink(proxy_file)


def test_proxy_becomes_eligible_after_cooldown(monkeypatch):
    """Verify that after the cooldown period, the proxy becomes eligible again."""
    # Clear health tracker and pre-mark a proxy as unhealthy
    reset_health_tracker()
    proxy_url = "socks5://127.0.0.1:8080"
    health_tracker[proxy_url] = {"failures": 2, "unhealthy_until": 1000.0}  # Unhealthy until 1000

    # Create temporary proxy file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("127.0.0.1:8080\n")
        proxy_file = f.name

    try:
        # Mock settings
        settings = _mock_settings_health(proxy_file)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        # Install fake scrapling - success after cooldown
        calls = _install_fake_scrapling_with_proxy_tracking(monkeypatch, side_effects=[500, 200])  # direct fail, proxy success

        with patch("time.sleep"):
            with patch("time.time", side_effect=[1000.0, 1001.0]):  # First call at 1000 (unhealthy), second at 1001 (healthy)
                res = execute_crawl_with_retries(_make_request())

        assert res.status == "success"
        assert calls["count"] == 2

        # Check that proxy was used in second attempt
        assert calls["proxies_used"][1] == proxy_url

    finally:
        os.unlink(proxy_file)


def test_success_resets_failure_count_and_health(monkeypatch):
    """Verify that success resets the failure count and health status for a proxy."""
    # Clear health tracker and pre-set failures
    reset_health_tracker()
    proxy_url = "socks5://127.0.0.1:8080"
    health_tracker[proxy_url] = {"failures": 1, "unhealthy_until": 0}  # 1 failure, healthy

    # Create temporary proxy file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("127.0.0.1:8080\n")
        proxy_file = f.name

    try:
        # Mock settings
        settings = _mock_settings_health(proxy_file)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        # Install fake scrapling - direct fail, proxy success
        calls = _install_fake_scrapling_with_proxy_tracking(monkeypatch, side_effects=[500, 200])

        with patch("time.sleep"):
            with patch("time.time", return_value=1000.0):
                res = execute_crawl_with_retries(_make_request())

        assert res.status == "success"
        assert calls["count"] == 2

        # Check that health was reset
        ht = health_tracker[proxy_url]
        assert ht["failures"] == 0
        assert ht["unhealthy_until"] == 0

    finally:
        os.unlink(proxy_file)


def test_proxy_skipped_during_cooldown_period(monkeypatch):
    """Verify that unhealthy proxy is skipped during cooldown."""
    # Clear health tracker and mark proxy as unhealthy
    reset_health_tracker()
    proxy_url = "socks5://127.0.0.1:8080"
    health_tracker[proxy_url] = {"failures": 2, "unhealthy_until": 2000.0}  # Unhealthy until 2000

    # Create temporary proxy file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("127.0.0.1:8080\n")
        proxy_file = f.name

    try:
        # Mock settings
        settings = _mock_settings_health(proxy_file)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        # Install fake scrapling - direct fail, skip unhealthy proxy, use private
        calls = _install_fake_scrapling_with_proxy_tracking(monkeypatch, side_effects=[500, 200])

        with patch("time.sleep"):
            with patch("time.time", return_value=1500.0):  # During cooldown (1500 < 2000)
                res = execute_crawl_with_retries(_make_request())

        assert res.status == "success"
        assert calls["count"] == 2

        # Check that unhealthy proxy was skipped
        assert calls["proxies_used"][1] == settings.private_proxy_url  # Used private instead
        assert proxy_url not in calls["proxies_used"]

    finally:
        os.unlink(proxy_file)