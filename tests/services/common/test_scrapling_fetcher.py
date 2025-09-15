import sys
import types
import inspect
import pytest
from unittest.mock import MagicMock

from app.services.common.adapters.arg_composer import FetchArgComposer
from app.services.common.adapters.fetch_adapter import ScraplingFetcherAdapter
from app.services.common.types import FetchCapabilities


def _create_fake_caps(supports_geoip=False, **kwargs):
    """Create fake FetchCapabilities with specified support."""
    caps = FetchCapabilities(
        supports_proxy=False,
        supports_network_idle=False,
        supports_timeout=False,
        supports_additional_args=False,
        supports_page_action=False,
    )
    # Add geoip support dynamically
    if supports_geoip:
        caps.supports_geoip = True
    for k, v in kwargs.items():
        setattr(caps, k, v)
    return caps


def _create_mock_settings(**kwargs):
    """Create mock settings object."""
    settings = MagicMock()
    for k, v in kwargs.items():
        setattr(settings, k, v)
    return settings


def test_compose_geoip_enabled_when_supported_with_proxy():
    """Test that geoip=True is set when supported, even with proxy."""
    caps = _create_fake_caps(supports_geoip=True)
    settings = _create_mock_settings(camoufox_geoip=False)  # Should be ignored

    result = FetchArgComposer.compose(
        options={},
        caps=caps,
        selected_proxy="http://proxy.example.com",
        additional_args={},
        extra_headers=None,
        settings=settings
    )

    assert result.get("geoip") is True


def test_compose_geoip_enabled_when_supported_without_proxy():
    """Test that geoip=True is set when supported, even without proxy."""
    caps = _create_fake_caps(supports_geoip=True)
    settings = _create_mock_settings(camoufox_geoip=False)  # Should be ignored

    result = FetchArgComposer.compose(
        options={},
        caps=caps,
        selected_proxy=None,
        additional_args={},
        extra_headers=None,
        settings=settings
    )

    assert result.get("geoip") is True


def test_compose_geoip_not_set_when_not_supported():
    """Test that geoip is not set when not supported."""
    caps = _create_fake_caps(supports_geoip=False)
    settings = _create_mock_settings(camoufox_geoip=True)

    result = FetchArgComposer.compose(
        options={},
        caps=caps,
        selected_proxy="http://proxy.example.com",
        additional_args={},
        extra_headers=None,
        settings=settings
    )

    assert "geoip" not in result


def test_compose_geoip_independent_of_settings():
    """Test that geoip setting is independent of camoufox_geoip setting."""
    caps = _create_fake_caps(supports_geoip=True)

    # Test with camoufox_geoip=True
    settings_true = _create_mock_settings(camoufox_geoip=True)
    result_true = FetchArgComposer.compose(
        options={},
        caps=caps,
        selected_proxy=None,
        additional_args={},
        extra_headers=None,
        settings=settings_true
    )
    assert result_true.get("geoip") is True

    # Test with camoufox_geoip=False
    settings_false = _create_mock_settings(camoufox_geoip=False)
    result_false = FetchArgComposer.compose(
        options={},
        caps=caps,
        selected_proxy=None,
        additional_args={},
        extra_headers=None,
        settings=settings_false
    )
    assert result_false.get("geoip") is True


def test_fetch_with_geoip_fallback_on_database_error(monkeypatch):
    """Test that fetch retries without geoip when database error occurs."""
    calls = {"count": 0, "kwargs": []}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):
            calls["count"] += 1
            calls["kwargs"].append(kwargs.copy())

            if calls["count"] == 1 and kwargs.get("geoip"):
                # First call with geoip fails with database error
                raise Exception("InvalidDatabaseError: GeoLite2-City.mmdb not found")
            else:
                # Second call without geoip succeeds
                resp = types.SimpleNamespace()
                resp.status = 200
                resp.html_content = "<html>success</html>"
                return resp

    # Mock signature to support geoip
    fake_sig = inspect.Signature([
        inspect.Parameter('url', inspect.Parameter.POSITIONAL_OR_KEYWORD),
        inspect.Parameter('geoip', inspect.Parameter.KEYWORD_ONLY),
    ], return_annotation=None)
    FakeStealthyFetcher.fetch.__signature__ = fake_sig

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)

    adapter = ScraplingFetcherAdapter()
    result = adapter._fetch_with_geoip_fallback(
        "https://example.com", {"geoip": True, "headless": True}
    )

    assert calls["count"] == 2
    assert calls["kwargs"][0]["geoip"] is True  # First attempt with geoip
    assert "geoip" not in calls["kwargs"][1]  # Second attempt without geoip
    assert result.status == 200


def test_fetch_with_geoip_fallback_on_geolite_error(monkeypatch):
    """Test that fetch retries without geoip when GeoLite2 error occurs."""
    calls = {"count": 0, "kwargs": []}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):
            calls["count"] += 1
            calls["kwargs"].append(kwargs.copy())

            if calls["count"] == 1 and kwargs.get("geoip"):
                # First call with geoip fails with GeoLite2 error
                raise Exception("GeoLite2-City.mmdb database file not found")
            else:
                # Second call without geoip succeeds
                resp = types.SimpleNamespace()
                resp.status = 200
                resp.html_content = "<html>success</html>"
                return resp

    # Mock signature to support geoip
    fake_sig = inspect.Signature([
        inspect.Parameter('url', inspect.Parameter.POSITIONAL_OR_KEYWORD),
        inspect.Parameter('geoip', inspect.Parameter.KEYWORD_ONLY),
    ], return_annotation=None)
    FakeStealthyFetcher.fetch.__signature__ = fake_sig

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)

    adapter = ScraplingFetcherAdapter()
    result = adapter._fetch_with_geoip_fallback(
        "https://example.com", {"geoip": True, "headless": True}
    )

    assert calls["count"] == 2
    assert calls["kwargs"][0]["geoip"] is True  # First attempt with geoip
    assert "geoip" not in calls["kwargs"][1]  # Second attempt without geoip
    assert result.status == 200


def test_fetch_with_geoip_fallback_http_timeout_triggers_http_fallback(monkeypatch):
    """Timeout errors with selector should trigger HTTP fallback."""

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):
            raise Exception("TimeoutError: Page.goto timeout")

    adapter = ScraplingFetcherAdapter()
    monkeypatch.setattr(adapter, "_get_stealthy_fetcher", lambda: FakeStealthyFetcher)

    fallback_result = types.SimpleNamespace(status=200, html_content="fallback")
    fallback_mock = MagicMock(return_value=fallback_result)
    monkeypatch.setattr(adapter, "_http_fallback", fallback_mock)

    args = {"wait_selector": "#app", "network_idle": False}

    result = adapter._fetch_with_geoip_fallback("https://example.com", args)

    fallback_mock.assert_called_once_with("https://example.com")
    assert result is fallback_result


def test_geoip_no_fallback_on_other_errors(monkeypatch):
    """Test that fetch does not retry on non-geoip errors."""
    calls = {"count": 0}

    class FakeStealthyFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):
            calls["count"] += 1
            # Fail with non-geoip error
            raise Exception("Network timeout")

    # Mock signature to support geoip
    fake_sig = inspect.Signature([
        inspect.Parameter('url', inspect.Parameter.POSITIONAL_OR_KEYWORD),
        inspect.Parameter('geoip', inspect.Parameter.KEYWORD_ONLY),
    ], return_annotation=None)
    FakeStealthyFetcher.fetch.__signature__ = fake_sig

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
    monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)

    adapter = ScraplingFetcherAdapter()

    with pytest.raises(Exception, match="Network timeout"):
        adapter.fetch("https://example.com", {"geoip": True, "headless": True})

    assert calls["count"] == 1  # Only one attempt, no retry


def test_fetch_sets_adaptive_and_uses_geoip_flow_when_no_loop(monkeypatch):
    """Fetch should set adaptive flag and delegate to geoip fallback when loop idle."""

    adapter = ScraplingFetcherAdapter()
    sentinel_result = object()
    fallback_mock = MagicMock(return_value=sentinel_result)
    monkeypatch.setattr(adapter, "_fetch_with_geoip_fallback", fallback_mock)
    monkeypatch.setattr(adapter, "_has_running_loop", lambda: False)

    dummy_fetcher = types.SimpleNamespace(adaptive=False)
    monkeypatch.setattr(adapter, "_get_stealthy_fetcher", lambda: dummy_fetcher)

    args = {"geoip": True, "headless": True}

    result = adapter.fetch("https://example.com", args)

    assert result is sentinel_result
    assert dummy_fetcher.adaptive is True
    fallback_mock.assert_called_once_with("https://example.com", args)


def test_fetch_uses_thread_when_event_loop_present(monkeypatch):
    """Fetch should hand off to thread path when an event loop is running."""

    adapter = ScraplingFetcherAdapter()
    sentinel_result = object()
    thread_mock = MagicMock(return_value=sentinel_result)
    monkeypatch.setattr(adapter, "_fetch_in_thread", thread_mock)
    monkeypatch.setattr(adapter, "_has_running_loop", lambda: True)

    dummy_fetcher = types.SimpleNamespace(adaptive=False)
    monkeypatch.setattr(adapter, "_get_stealthy_fetcher", lambda: dummy_fetcher)

    args = {"geoip": True, "headless": True}

    result = adapter.fetch("https://example.com", args)

    assert result is sentinel_result
    assert dummy_fetcher.adaptive is True
    thread_mock.assert_called_once_with("https://example.com", args)
