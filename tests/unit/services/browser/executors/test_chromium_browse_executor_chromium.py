"""Tests for ChromiumBrowseExecutor when running with Chromium engine."""

import os
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

from app.schemas.crawl import CrawlRequest
from app.services.browser.executors.chromium_browse_executor import ChromiumBrowseExecutor

pytestmark = pytest.mark.unit


class _FakeFetcherBase:
    """Base fake fetcher capturing init kwargs and fetch invocations."""

    init_kwargs: Optional[Dict[str, Any]] = None
    last_fetch: Optional[Dict[str, Any]] = None
    return_value: Any = None
    fetch_side_effect: Optional[BaseException] = None

    def __init__(self, **kwargs: Any) -> None:
        type(self).init_kwargs = kwargs

    def fetch(self, url: str, **kwargs: Any) -> Any:
        type(self).last_fetch = {"url": url, "kwargs": kwargs}
        if type(self).fetch_side_effect is not None:
            raise type(self).fetch_side_effect
        return type(self).return_value


@pytest.fixture
def fake_fetchers(monkeypatch: pytest.MonkeyPatch):
    """Patch Chromium fetchers with controllable stand-ins."""

    class FakePersistentChromiumFetcher(_FakeFetcherBase):
        pass

    class FakeDynamicFetcher(_FakeFetcherBase):
        pass

    FakePersistentChromiumFetcher.return_value = object()
    FakeDynamicFetcher.return_value = None

    from app.services.browser.executors import chromium_browse_executor as executor_module

    monkeypatch.setattr(executor_module, "PersistentChromiumFetcher", FakePersistentChromiumFetcher)
    monkeypatch.setattr(executor_module, "DynamicFetcher", FakeDynamicFetcher)
    monkeypatch.setattr(executor_module, "PERSISTENT_CHROMIUM_AVAILABLE", True)
    monkeypatch.setattr(executor_module, "DYNAMIC_FETCHER_AVAILABLE", True)

    return SimpleNamespace(
        persistent=FakePersistentChromiumFetcher,
        dynamic=FakeDynamicFetcher,
        module=executor_module,
    )


@pytest.fixture
def chromium_executor(monkeypatch: pytest.MonkeyPatch, fake_fetchers):
    """Provide an executor with patched settings factory."""

    def _make(settings: Any) -> ChromiumBrowseExecutor:
        monkeypatch.setattr(
            "app.services.browser.executors.chromium_browse_executor.app_config.get_settings",
            lambda: settings,
        )
        return ChromiumBrowseExecutor()

    return _make


def _make_request(url: str = "https://example.com") -> CrawlRequest:
    return CrawlRequest(url=url)


def test_persistent_fetcher_used_when_user_data_dir_configured(fake_fetchers, chromium_executor):
    settings = SimpleNamespace(chromium_runtime_effective_user_data_dir="./relative-profile")
    executor = chromium_executor(settings)

    request = _make_request()
    response = executor.execute(request)

    expected_dir = os.path.abspath(settings.chromium_runtime_effective_user_data_dir)

    assert fake_fetchers.persistent.init_kwargs == {"user_data_dir": expected_dir}
    assert fake_fetchers.persistent.last_fetch is not None
    fetch_kwargs = fake_fetchers.persistent.last_fetch["kwargs"]
    assert "browser_args" in fetch_kwargs
    assert fetch_kwargs["browser_args"]
    assert "--headless" in fetch_kwargs["browser_args"]
    assert fetch_kwargs["user_data_dir"] == expected_dir
    assert fetch_kwargs["additional_args"]["user_data_dir"] == expected_dir
    assert response.status == "success"


def test_dynamic_fetcher_used_without_user_data_dir(fake_fetchers, chromium_executor):
    settings = SimpleNamespace(chromium_runtime_effective_user_data_dir=None)
    executor = chromium_executor(settings)

    request = _make_request()
    response = executor.execute(request)

    assert isinstance(executor.fetcher, fake_fetchers.dynamic)
    assert fake_fetchers.dynamic.last_fetch is not None
    fetch_kwargs = fake_fetchers.dynamic.last_fetch["kwargs"]
    assert "browser_args" not in fetch_kwargs
    assert response.status == "failure"
    assert "returned None" in response.message


def test_dependency_guidance_returned_on_import_error(fake_fetchers, chromium_executor):
    settings = SimpleNamespace(chromium_runtime_effective_user_data_dir=None)
    executor = chromium_executor(settings)

    fake_fetchers.dynamic.fetch_side_effect = ImportError("Playwright not installed")

    request = _make_request()
    response = executor.execute(request)

    assert response.status == "failure"
    assert "ImportError: Playwright not installed" in response.message
    assert "pip install 'scrapling[chromium]'" in response.message
    assert "playwright install chromium" in response.message
