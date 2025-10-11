import pytest
import types

from app.services.common.adapters import scrapling_fetcher as scrapling_fetcher_module
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("require_scrapling")]


@pytest.mark.integration
def test_fetch_uses_http_fallback_on_timeout(monkeypatch):
    """Timeout errors should fall back to the lightweight HTTP fetch."""

    adapter = ScraplingFetcherAdapter()

    class FakeFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):  # pragma: no cover - bypassed in this test
            raise AssertionError("fetch should use _execute_fetch mock")

    monkeypatch.setattr(adapter, "_get_stealthy_fetcher", lambda: FakeFetcher)

    attempts = {"execute": 0, "fallback": 0}

    def fake_execute(url, params):
        attempts["execute"] += 1
        assert params.wait_selector == "#app"
        raise TimeoutError("Page.goto Timeout 30000ms exceeded")

    def fake_http_fallback(url):
        attempts["fallback"] += 1
        return types.SimpleNamespace(status=200, html_content="fallback")

    monkeypatch.setattr(adapter, "_execute_fetch", fake_execute)
    monkeypatch.setattr(adapter, "_http_fallback", fake_http_fallback)

    result = adapter.fetch("https://example.com", {"wait_selector": "#app"})

    assert result.html_content == "fallback"
    assert attempts["execute"] == 1
    assert attempts["fallback"] == 1


@pytest.mark.integration
def test_fetch_http_fallback_failure_reraises_timeout(monkeypatch):
    """If HTTP fallback also fails, the original timeout error should surface."""

    adapter = ScraplingFetcherAdapter()

    class FakeFetcher:
        adaptive = False

        @staticmethod
        def fetch(url, **kwargs):  # pragma: no cover - bypassed in this test
            raise AssertionError("fetch should use _execute_fetch mock")

    monkeypatch.setattr(adapter, "_get_stealthy_fetcher", lambda: FakeFetcher)

    attempts = {"execute": 0, "fallback": 0}

    def fake_execute(url, params):
        attempts["execute"] += 1
        raise TimeoutError("Timeout navigating")

    def failing_fallback(url):
        attempts["fallback"] += 1
        raise RuntimeError("fallback failed")

    monkeypatch.setattr(adapter, "_execute_fetch", fake_execute)
    monkeypatch.setattr(adapter, "_http_fallback", failing_fallback)

    with pytest.raises(TimeoutError):
        adapter.fetch("https://example.com", {"wait_selector": "#root"})

    assert attempts["execute"] == 1
    assert attempts["fallback"] == 1


@pytest.mark.integration
def test_http_fallback_returns_response_like_object(monkeypatch):
    """The raw HTTP fallback should produce a simple namespace result."""

    adapter = ScraplingFetcherAdapter()

    class DummyResponse:
        def __init__(self):
            self.status = 202

        def read(self):
            return b"<html>ok</html>"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        scrapling_fetcher_module, "urlopen", lambda req, timeout=30: DummyResponse()
    )

    result = adapter._http_fallback("https://example.com")

    assert result.status == 202
    assert result.html_content == "<html>ok</html>"


@pytest.mark.integration
def test_http_fallback_failure_bubbles_exception(monkeypatch):
    """Errors from the HTTP fallback should be propagated."""

    adapter = ScraplingFetcherAdapter()

    def fake_urlopen(req, timeout=30):
        raise ValueError("boom")

    monkeypatch.setattr(scrapling_fetcher_module, "urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="boom"):
        adapter._http_fallback("https://example.com")
