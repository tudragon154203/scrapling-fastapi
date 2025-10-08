from app.services.browser.options.resolver import OptionsResolver
from app.schemas.crawl import CrawlRequest

import pytest

pytestmark = [pytest.mark.unit]



class DummySettings:
    """Simple settings stand-in for tests."""
    default_headless = True
    default_network_idle = False
    default_timeout_ms = 15000


def test_force_headful_overrides_default_headless():
    req = CrawlRequest(url="https://example.com", force_headful=True)
    settings = DummySettings()

    opts = OptionsResolver().resolve(req, settings)

    assert opts == {
        "wait_for_selector": "body",
        "wait_for_selector_state": "attached",
        "timeout_ms": settings.default_timeout_ms,
        "timeout_seconds": None,
        "headless": False,
        "network_idle": False,
        "disable_timeout": False,
        "prefer_domcontentloaded": True,
    }


def test_wait_for_selector_state_only_when_selector_present():
    settings = DummySettings()
    resolver = OptionsResolver()

    req_with_selector = CrawlRequest(
        url="https://example.com", wait_for_selector="#main", wait_for_selector_state="hidden"
    )
    opts_with_selector = resolver.resolve(req_with_selector, settings)

    assert opts_with_selector == {
        "wait_for_selector": "#main",
        "wait_for_selector_state": "hidden",
        "timeout_ms": settings.default_timeout_ms,
        "timeout_seconds": None,
        "headless": settings.default_headless,
        "network_idle": False,
        "disable_timeout": False,
        "prefer_domcontentloaded": True,
    }

    req_without_selector = CrawlRequest(url="https://example.com", wait_for_selector=None)
    opts_without_selector = resolver.resolve(req_without_selector, settings)

    assert opts_without_selector == {
        "wait_for_selector": None,
        "wait_for_selector_state": None,
        "timeout_ms": settings.default_timeout_ms,
        "timeout_seconds": None,
        "headless": settings.default_headless,
        "network_idle": False,
        "disable_timeout": False,
        "prefer_domcontentloaded": False,
    }


def test_timeout_defaults_when_seconds_absent():
    req = CrawlRequest(url="https://example.com")
    settings = DummySettings()

    opts = OptionsResolver().resolve(req, settings)

    assert opts["timeout_ms"] == settings.default_timeout_ms
    assert opts["timeout_seconds"] is None
