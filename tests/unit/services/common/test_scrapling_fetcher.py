import sys
import threading
import types
import inspect
import pytest
from unittest.mock import MagicMock

from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter
from app.services.common.adapters.fetch_arg_composer import FetchArgComposer
from app.services.common.adapters.fetch_params import FetchParams
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


def test_geoip_fallback_on_database_error(monkeypatch):
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
    result = adapter.fetch("https://example.com", {"geoip": True, "headless": True})

    assert calls["count"] == 2
    assert calls["kwargs"][0]["geoip"] is True  # First attempt with geoip
    assert "geoip" not in calls["kwargs"][1]  # Second attempt without geoip
    assert result.status == 200


def test_geoip_fallback_on_geolite_error(monkeypatch):
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
    result = adapter.fetch("https://example.com", {"geoip": True, "headless": True})

    assert calls["count"] == 2
    assert calls["kwargs"][0]["geoip"] is True  # First attempt with geoip
    assert "geoip" not in calls["kwargs"][1]  # Second attempt without geoip
    assert result.status == 200


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


def test_fetch_params_state_helpers():
    """Ensure FetchParams helpers manage state and copies correctly."""

    params = FetchParams({"geoip": True})
    assert params.geoip_enabled is True

    clone = params.copy()
    assert clone is not params
    clone["wait_selector"] = "#app"
    assert clone.wait_selector == "#app"
    assert clone.allows_http_fallback is True

    clone["network_idle"] = True
    assert clone.network_idle_enabled is True
    assert clone.allows_http_fallback is False

    trimmed = clone.without_geoip()
    assert "geoip" not in trimmed
    assert trimmed.geoip_enabled is False
    assert params.geoip_enabled is True  # Original untouched

    trimmed.setdefault("geoip", False)
    assert trimmed.geoip_enabled is False

    trimmed.update({"network_idle": False})
    assert trimmed.allows_http_fallback is True
    assert "wait_selector" in trimmed
    assert trimmed.get("missing") is None
    assert trimmed.as_kwargs()["wait_selector"] == "#app"


def test_fetch_runs_in_background_thread_when_loop_running(monkeypatch):
    """When an event loop is active, fetch should run inside a thread."""

    adapter = ScraplingFetcherAdapter()

    class FakeFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):  # pragma: no cover - should not run here
            raise AssertionError("fetch should be delegated through _fetch_with_retry")

    monkeypatch.setattr(adapter, "_get_stealthy_fetcher", lambda: FakeFetcher)

    thread_names = []

    def fake_fetch_with_retry(url, params):
        thread_names.append(threading.current_thread().name)
        assert isinstance(params, FetchParams)
        return "sentinel"

    monkeypatch.setattr(adapter, "_fetch_with_retry", fake_fetch_with_retry)
    monkeypatch.setattr(adapter, "_has_running_loop", lambda: True)

    result = adapter.fetch("https://example.com", {"headless": False})

    assert result == "sentinel"
    assert thread_names
    assert thread_names[0] != threading.main_thread().name


def test_fetch_arg_composer_filters_additional_args_and_headers():
    """Additional args should be sanitized using capability awareness."""

    caps = FetchCapabilities(
        supports_proxy=False,
        supports_network_idle=False,
        supports_timeout=True,
        supports_additional_args=True,
        supports_page_action=True,
        supports_geoip=False,
        supports_extra_headers=True,
    )
    caps.supports_custom_flag = True
    caps.supports_user_data_dir = True

    additional_args = {
        "custom_flag": "yes",
        "_private": "hidden",
        "user_data_dir": "/tmp/user",
        "profile_path": "/tmp/profile",
        "firefox_user_prefs": {"dom.audiochannel.mutedByDefault": True},
        "unsupported": "nope",
    }
    extra_headers = {"X-Test": "1"}

    result = FetchArgComposer.compose(
        options={"timeout_ms": 1000},
        caps=caps,
        selected_proxy=None,
        additional_args=additional_args,
        extra_headers=extra_headers,
        settings=_create_mock_settings(write_mode_timeout_ms=9999),
    )

    assert isinstance(result, FetchParams)
    assert result["additional_args"] == {
        "custom_flag": "yes",
        "user_data_dir": "/tmp/user",
        "profile_path": "/tmp/profile",
        "firefox_user_prefs": {"dom.audiochannel.mutedByDefault": True},
    }
    assert "_private" not in result["additional_args"]
    assert "unsupported" not in result["additional_args"]
    assert result["extra_headers"] == extra_headers


def test_fetch_arg_composer_additional_args_error_fallback():
    """If filtering additional args fails, the original mapping should be used."""

    caps = FetchCapabilities(supports_additional_args=True)
    caps.supports_user_data_dir = True

    class FailingDict(dict):
        def items(self):
            raise RuntimeError("boom")

    additional_args = FailingDict({"user_data_dir": "/tmp/user", "_private": "hidden"})

    result = FetchArgComposer.compose(
        options={},
        caps=caps,
        selected_proxy=None,
        additional_args=additional_args,
        extra_headers=None,
        settings=_create_mock_settings(),
    )

    assert result["additional_args"] == dict(additional_args)


def test_fetch_arg_composer_skips_headers_without_support():
    """Headers must be omitted when the fetcher cannot accept them."""

    caps = FetchCapabilities(supports_additional_args=True, supports_extra_headers=False)

    result = FetchArgComposer.compose(
        options={},
        caps=caps,
        selected_proxy=None,
        additional_args={"user_data_dir": "/tmp"},
        extra_headers={"X-Test": "1"},
        settings=_create_mock_settings(),
    )

    assert "extra_headers" not in result
