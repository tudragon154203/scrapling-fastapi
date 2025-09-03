import types

import pytest


def make_stub_response(status=200, html="<html>ok</html>"):
    obj = types.SimpleNamespace()
    obj.status = status
    obj.html_content = html
    return obj


def test_generic_crawl_maps_new_and_legacy_fields(monkeypatch):
    from app.services.crawler.generic import crawl_generic
    from app.schemas.crawl import CrawlRequest
    from app.core.config import get_settings

    captured = {}

    def fake_fetch(url, **kwargs):  # scrapling.fetchers.StealthyFetcher.fetch
        captured["url"] = url
        captured["kwargs"] = kwargs
        return make_stub_response(status=200, html="<html>fine</html>")

    # Patch the classmethod before import usage inside service function
    import scrapling.fetchers as fetchers

    monkeypatch.setattr(fetchers.StealthyFetcher, "fetch", staticmethod(fake_fetch))

    req = CrawlRequest(
        url="https://example.com",
        wait_selector="body",
        wait_selector_state="visible",
        timeout_ms=5000,
        headless=True,
        network_idle=True,
        x_wait_time=2,  # seconds
    )

    res = crawl_generic(req)
    assert res.status == "success"
    assert res.html == "<html>fine</html>"
    assert captured["url"].rstrip("/") == "https://example.com".rstrip("/")

    kwargs = captured["kwargs"]
    # New fields pass through
    assert kwargs["wait_selector"] == "body"
    assert kwargs["wait_selector_state"] == "visible"
    assert kwargs["timeout"] == 5000
    assert kwargs["headless"] is True
    assert kwargs["network_idle"] is True
    # Legacy x_wait_time -> wait (ms)
    assert kwargs["wait"] == 2000


def test_generic_crawl_legacy_only_maps_correctly(monkeypatch):
    from app.services.crawler.generic import crawl_generic
    from app.schemas.crawl import CrawlRequest
    from app.core.config import get_settings

    settings = get_settings()
    captured = {}

    def fake_fetch(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return make_stub_response(status=200, html="<html>legacy</html>")

    import scrapling.fetchers as fetchers

    monkeypatch.setattr(fetchers.StealthyFetcher, "fetch", staticmethod(fake_fetch))

    req = CrawlRequest(
        url="https://example.com",
        x_wait_for_selector="#app",
        x_wait_time=7,
        x_force_headful=True,
    )

    res = crawl_generic(req)
    assert res.status == "success"
    assert res.html == "<html>legacy</html>"

    kwargs = captured["kwargs"]
    # wait_selector pulled from legacy field
    assert kwargs["wait_selector"] == "#app"
    # headless forced off by legacy flag
    assert kwargs["headless"] is False
    # default settings for unspecified fields
    assert kwargs["network_idle"] is settings.default_network_idle
    assert kwargs["timeout"] == settings.default_timeout_ms
    # legacy wait seconds -> ms
    assert kwargs["wait"] == 7000


def test_generic_crawl_handles_non_200_status(monkeypatch):
    from app.services.crawler.generic import crawl_generic
    from app.schemas.crawl import CrawlRequest

    def fake_fetch(url, **kwargs):
        return make_stub_response(status=500, html="<html>err</html>")

    import scrapling.fetchers as fetchers

    monkeypatch.setattr(fetchers.StealthyFetcher, "fetch", staticmethod(fake_fetch))

    req = CrawlRequest(url="https://example.com")
    res = crawl_generic(req)
    assert res.status == "failure"
    assert res.html is None
    assert "HTTP status" in (res.message or "")


def test_generic_crawl_handles_exception(monkeypatch):
    from app.services.crawler.generic import crawl_generic
    from app.schemas.crawl import CrawlRequest

    def fake_fetch(url, **kwargs):
        raise RuntimeError("boom")

    import scrapling.fetchers as fetchers

    monkeypatch.setattr(fetchers.StealthyFetcher, "fetch", staticmethod(fake_fetch))

    req = CrawlRequest(url="https://example.com")
    res = crawl_generic(req)
    assert res.status == "failure"
    assert res.html is None
    assert "Exception during crawl" in (res.message or "")

