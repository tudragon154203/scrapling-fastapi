import json
from typing import Optional

import pytest


def test_crawl_success_with_stub(monkeypatch, client):
    # Import inside test to ensure app/router is loaded
    from app.api import routes
    from app.schemas.crawl import CrawlResponse

    captured_payload = {}

    def _fake_crawl_generic(payload):
        # capture for assertions
        captured_payload["payload"] = payload
        return CrawlResponse(status="success", url=payload.url, html="<html>ok</html>")

    # monkeypatch the service function used by the route
    monkeypatch.setattr(routes, "crawl_generic", _fake_crawl_generic)

    body = {
        "url": "https://example.com",
        "wait_selector": "body",
        "timeout_ms": 5000,
        "headless": True,
    }
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["html"].startswith("<html>")

    # ensure payload mapping worked
    p = captured_payload["payload"]
    assert str(p.url).rstrip("/") == body["url"].rstrip("/")
    assert p.wait_selector == body["wait_selector"]
    assert p.timeout_ms == body["timeout_ms"]
    assert p.headless is True


def test_crawl_legacy_fields(monkeypatch, client):
    from app.api import routes
    from app.schemas.crawl import CrawlResponse

    captured_payload = {}

    def _fake_crawl_generic(payload):
        captured_payload["payload"] = payload
        return CrawlResponse(status="success", url=payload.url, html="<html>legacy</html>")

    monkeypatch.setattr(routes, "crawl_generic", _fake_crawl_generic)

    body = {
        "url": "https://example.com",
        "x_wait_for_selector": "#app",
        "x_wait_time": 7,
        "x_force_headful": True,
    }
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"

    p = captured_payload["payload"]
    # legacy field bridged to new
    assert p.wait_selector is None  # field remains None; mapping happens in service
    assert p.x_wait_for_selector == "#app"
    assert p.x_wait_time == 7
    assert p.x_force_headful is True


def test_crawl_requires_url(client):
    resp = client.post("/crawl", json={})
    assert resp.status_code == 422
