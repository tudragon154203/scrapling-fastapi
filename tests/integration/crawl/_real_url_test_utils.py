"""Shared fixtures and helpers for crawl integration tests using real URLs."""

import pytest
from app.core.config import get_settings


pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


# Disable proxies and keep retries minimal within this module to reduce flakiness/hangs
@pytest.fixture(autouse=True)
def _disable_proxies_and_reduce_retries(monkeypatch):
    from app.core import config as app_config

    real_get_settings = app_config.get_settings

    def _wrapped():
        settings = real_get_settings()

        class _Proxy:
            """Shallow proxy allowing temporary overrides without mutating cache."""

        proxy = _Proxy()
        for key, value in settings.__dict__.items():
            setattr(proxy, key, value)
        proxy.proxy_list_file_path = None
        proxy.private_proxy_url = None
        proxy.max_retries = 1
        # HTTP fallback removed from service; rely on Scrapling only
        return proxy

    monkeypatch.setattr(app_config, "get_settings", _wrapped)


def make_body(url: str) -> dict:
    return {
        "url": url,
        "wait_for_selector": "body",
        "wait_for_selector_state": "visible",
        "network_idle": False,
        "timeout_seconds": 60,
    }


def min_html_length() -> int:
    """Return the service's minimum acceptable HTML length."""
    try:
        settings = get_settings()
        value = getattr(settings, "min_html_content_length", None)
        return int(value) if value is not None else 500
    except Exception:
        return 500


__all__ = ["make_body", "min_html_length"]
