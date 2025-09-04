import time
import types
from unittest.mock import patch, MagicMock
import sys

import pytest


def make_stub_response(status=200, html="<html>ok</html>"):
    obj = types.SimpleNamespace()
    obj.status = status
    obj.html_content = html
    return obj


def test_retry_strategy_backoff_calculation():
    """Test that backoff delay is calculated correctly."""
    from app.services.crawler.generic import _calculate_backoff_delay
    
    # Create a mock settings object
    class MockSettings:
        retry_backoff_base_ms = 500
        retry_backoff_max_ms = 5000
        retry_jitter_ms = 100

    settings = MockSettings()

    # Test first attempt (no backoff)
    delay = _calculate_backoff_delay(0, settings)
    # Should be between 0.5s and 0.6s (base + jitter)
    assert 0.5 <= delay <= 0.6

    # Test second attempt
    delay = _calculate_backoff_delay(1, settings)
    # Should be between 1.0s and 1.1s (base*2 + jitter)
    assert 1.0 <= delay <= 1.1

    # Test third attempt
    delay = _calculate_backoff_delay(2, settings)
    # Should be between 2.0s and 2.1s (base*4 + jitter)
    assert 2.0 <= delay <= 2.1


def test_proxy_plan_order_no_proxies():
    """Test proxy plan order when no proxies are configured."""
    from app.services.crawler.generic import _build_attempt_plan

    # Mock settings with no proxies
    class MockSettings:
        max_retries = 3
        private_proxy_url = None

    settings = MockSettings()

    plan = _build_attempt_plan(settings, [])
    
    # Should only have direct connections
    assert len(plan) == 3
    assert all(attempt["mode"] == "direct" for attempt in plan)
    assert all(attempt["proxy"] is None for attempt in plan)


def test_proxy_plan_order_with_public_proxies():
    """Test proxy plan order with public proxies configured."""
    from app.services.crawler.generic import _build_attempt_plan

    # Mock settings with public proxies
    class MockSettings:
        max_retries = 5
        private_proxy_url = None

    settings = MockSettings()

    public_proxies = ["socks5://192.168.1.1:1080", "socks5://192.168.1.2:1080"]
    plan = _build_attempt_plan(settings, public_proxies)
    
    # Should have direct -> public -> public -> direct -> public
    assert len(plan) == 5
    assert plan[0]["mode"] == "direct"
    assert plan[0]["proxy"] is None
    assert plan[1]["mode"] == "public"
    assert plan[1]["proxy"] == "socks5://192.168.1.1:1080"
    assert plan[2]["mode"] == "public"
    assert plan[2]["proxy"] == "socks5://192.168.1.2:1080"
    assert plan[3]["mode"] == "direct"
    assert plan[3]["proxy"] is None
    assert plan[4]["mode"] == "public"
    assert plan[4]["proxy"] == "socks5://192.168.1.1:1080"


def test_proxy_plan_order_with_private_proxy():
    """Test proxy plan order with private proxy configured."""
    from app.services.crawler.generic import _build_attempt_plan

    # Mock settings with private proxy
    class MockSettings:
        max_retries = 4
        private_proxy_url = "http://private-proxy.com"

    settings = MockSettings()

    plan = _build_attempt_plan(settings, [])
    
    # Should have direct -> private -> direct -> direct
    assert len(plan) == 4
    assert plan[0]["mode"] == "direct"
    assert plan[0]["proxy"] is None
    assert plan[1]["mode"] == "private"
    assert plan[1]["proxy"] == "http://private-proxy.com"
    assert plan[2]["mode"] == "direct"
    assert plan[2]["proxy"] is None
    assert plan[3]["mode"] == "direct"
    assert plan[3]["proxy"] is None


def test_load_public_proxies_file_not_found():
    """Test loading public proxies when file doesn't exist."""
    from app.services.crawler.generic import _load_public_proxies
    
    proxies = _load_public_proxies("/non/existent/file.txt")
    assert proxies == []


def test_load_public_proxies_valid_file(tmp_path):
    """Test loading public proxies from a valid file."""
    from app.services.crawler.generic import _load_public_proxies
    
    # Create a temporary proxy file with mixed formats
    proxy_file = tmp_path / "proxies.txt"
    proxy_file.write_text("""# Sample proxy list
192.168.1.1:1080
192.168.1.2:1080

192.168.1.3:1081
# Commented proxy
http://proxy4.com:8080
socks5://192.168.1.5:1080
""")
    
    proxies = _load_public_proxies(str(proxy_file))
    assert len(proxies) == 5
    # IPs without protocol should be prefixed with socks5://
    assert "socks5://192.168.1.1:1080" in proxies
    assert "socks5://192.168.1.2:1080" in proxies
    assert "socks5://192.168.1.3:1081" in proxies
    # URLs with explicit protocols should remain unchanged
    assert "http://proxy4.com:8080" in proxies
    assert "socks5://192.168.1.5:1080" in proxies