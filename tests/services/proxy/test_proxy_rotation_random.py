import sys
import types
import tempfile
import os
from unittest.mock import patch

from app.services.common.engine import CrawlerEngine
from app.services.crawler.proxy.health import get_health_tracker, reset_health_tracker
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


def _mock_settings_random(proxy_list_file_path, private_proxy_url="socks5://127.0.0.1:1080"):
    class MockSettings:
        pass

    settings = MockSettings()
    settings.max_retries = 5
    settings.retry_backoff_base_ms = 1
    settings.retry_backoff_max_ms = 1
    settings.retry_jitter_ms = 0
    settings.proxy_list_file_path = proxy_list_file_path
    settings.private_proxy_url = private_proxy_url
    settings.proxy_rotation_mode = "random"
    settings.default_headless = True
    settings.default_network_idle = False
    settings.default_timeout_ms = 2000
    settings.proxy_health_failure_threshold = 2
    settings.proxy_unhealthy_cooldown_minute = 1
    settings.min_html_content_length = 1
    return settings


def _make_request():
    return CrawlRequest(
        url="https://example.com",
        wait_for_selector="body",
        wait_for_selector_state="visible",
        timeout_seconds=2,
        network_idle=False,
    )


def test_random_rotation_with_seeded_rng(monkeypatch):
    """With a seeded RNG, assert the chosen sequence matches expectation."""
    # Clear health tracker
    reset_health_tracker()

    # Seed random for deterministic behavior
    random.seed(42)

    # Create temporary proxy file with multiple proxies
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("127.0.0.1:8080\n")
        f.write("127.0.0.1:8081\n")
        f.write("127.0.0.1:8082\n")
        proxy_file = f.name

    try:
        # Mock settings
        settings = _mock_settings_random(proxy_file)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        # Install fake scrapling
        calls = _install_fake_scrapling_with_proxy_tracking(monkeypatch, side_effects=[500, 500, 500, 200])

        with patch("time.sleep"):
            # Use new OOP structure
            engine = CrawlerEngine.from_settings(settings)
            res = engine.run(_make_request())

        assert res.status == "success"
        assert calls["count"] == 4

        # With seed 42, random.choice should select specific proxies
        # Note: random mode starts with a proxy selection, not direct (as per current implementation)
        # The actual sequence shows: proxy1, proxy2, proxy1, private
        expected_proxies = ["socks5://127.0.0.1:8080", "socks5://127.0.0.1:8081", "socks5://127.0.0.1:8080", settings.private_proxy_url]
        assert calls["proxies_used"] == expected_proxies

    finally:
        os.unlink(proxy_file)


def test_random_rotation_excludes_unhealthy_proxies(monkeypatch):
    """Ensure unhealthy proxies are excluded from random selection."""
    # Clear health tracker and mark some as unhealthy
    reset_health_tracker()
    get_health_tracker().health_map["socks5://127.0.0.1:8080"] = {"failures": 3, "unhealthy_until": float('inf')}  # Unhealthy
    # 8081 and 8082 are healthy

    # Seed random
    random.seed(123)

    # Create temporary proxy file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("127.0.0.1:8080\n")  # Unhealthy
        f.write("127.0.0.1:8081\n")  # Healthy
        f.write("127.0.0.1:8082\n")  # Healthy
        proxy_file = f.name

    try:
        # Mock settings
        settings = _mock_settings_random(proxy_file)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        # Install fake scrapling
        calls = _install_fake_scrapling_with_proxy_tracking(monkeypatch, side_effects=[500, 500, 200])

        with patch("time.sleep"):
            # Use new OOP structure
            engine = CrawlerEngine.from_settings(settings)
            res = engine.run(_make_request())

        assert res.status == "success"
        assert calls["count"] == 3

        # Should only use healthy proxies
        used_proxies = [p for p in calls["proxies_used"] if p is not None and p != settings.private_proxy_url]
        assert "socks5://127.0.0.1:8080" not in used_proxies  # Unhealthy not used
        assert "socks5://127.0.0.1:8081" in used_proxies or "socks5://127.0.0.1:8082" in used_proxies

    finally:
        os.unlink(proxy_file)


def test_random_rotation_avoids_last_used_proxy(monkeypatch):
    """Test that random mode avoids immediate repetition when multiple healthy proxies available."""
    # Clear health tracker
    reset_health_tracker()

    # Seed random
    random.seed(456)

    # Create temporary proxy file with only two proxies
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("127.0.0.1:8080\n")
        f.write("127.0.0.1:8081\n")
        proxy_file = f.name

    try:
        # Mock settings
        settings = _mock_settings_random(proxy_file)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        # Install fake scrapling - force multiple attempts
        calls = _install_fake_scrapling_with_proxy_tracking(monkeypatch, side_effects=[500, 500, 500, 200])

        with patch("time.sleep"):
            # Use new OOP structure
            engine = CrawlerEngine.from_settings(settings)
            res = engine.run(_make_request())

        assert res.status == "success"
        assert calls["count"] == 4

        # Check that consecutive proxy uses are different when possible
        proxies = calls["proxies_used"]
        public_proxies = [p for p in proxies if p and p.startswith("socks5://127.0.0.1:808")]
        if len(public_proxies) > 1:
            # If multiple public proxies used, they should alternate
            assert public_proxies[0] != public_proxies[1]

    finally:
        os.unlink(proxy_file)
