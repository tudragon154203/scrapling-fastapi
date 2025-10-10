import sys
import types
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit]


def _install_fake_scrapling_without_proxy(monkeypatch):
    """Install fake scrapling with a StealthyFetcher.fetch that does NOT support `proxy`.

    Signature is explicit without **kwargs so feature detection should mark proxy as unsupported.
    """
    calls = {"count": 0}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(
            url,
            headless=None,
            network_idle=None,
            wait_selector=None,
            wait_selector_state=None,
            timeout=None,
            wait=None,
            additional_args=None,
            extra_headers=None,
        ):
            # If the implementation wrongly passes `proxy`, Python would raise TypeError.
            calls["count"] += 1
            obj = types.SimpleNamespace()
            obj.status = 200
            obj.html_content = "<html>ok</html>"
            return obj

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)
    return calls


def _mock_settings_no_proxy():
    class MockSettings:
        pass

    s = MockSettings()
    s.max_retries = 2
    s.retry_backoff_base_ms = 1
    s.retry_backoff_max_ms = 1
    s.retry_jitter_ms = 0
    s.proxy_list_file_path = None
    s.private_proxy_url = None
    s.proxy_rotation_mode = "sequential"
    s.default_headless = True
    s.default_network_idle = False
    s.default_timeout_ms = 2000
    s.proxy_health_failure_threshold = 2
    s.proxy_unhealthy_cooldown_minute = 1
    s.min_html_content_length = 1
    return s


def test_graceful_no_proxy_when_unsupported(monkeypatch):
    from app.services.common.engine import CrawlerEngine
    from app.schemas.crawl import CrawlRequest

    # Install fake scrapling without proxy support, and patch settings
    _install_fake_scrapling_without_proxy(monkeypatch)
    monkeypatch.setattr("app.core.config.get_settings", _mock_settings_no_proxy)

    req = CrawlRequest(
        url="https://example.com",
        wait_for_selector="body",
        wait_for_selector_state="visible",
        timeout_seconds=2,
        network_idle=False,
    )

    # Avoid sleeping delays
    with patch("time.sleep"):
        engine = CrawlerEngine.from_settings(_mock_settings_no_proxy())
        res = engine.run(req)

    assert res.status == "success"
    assert (res.html or "").startswith("<html>")
