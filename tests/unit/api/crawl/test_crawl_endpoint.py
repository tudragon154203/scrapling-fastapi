from fastapi.responses import JSONResponse
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.unit]


def test_crawl_success_with_stub(monkeypatch, client):
    # Import inside test to ensure app/router is loaded
    from app.services.crawler.generic import GenericCrawler
    from app.schemas.crawl import CrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        # capture for assertions
        captured_payload["payload"] = payload
        return CrawlResponse(status="success", url=payload.url, html="<html>ok</html>")

    # monkeypatch the service function used by the route
    monkeypatch.setattr(GenericCrawler, "run", _fake_crawl_run)

    body = {
        "url": "https://example.com",
        "timeout_seconds": 5,
    }
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["html"].startswith("<html>")

    # ensure payload mapping worked
    p = captured_payload["payload"]
    assert str(p.url).rstrip("/") == body["url"].rstrip("/")
    assert p.wait_for_selector == "body"
    assert p.wait_for_selector_state == "attached"
    assert p.timeout_seconds == body["timeout_seconds"]
    assert p.force_headful is False
    assert p.force_user_data is False


def test_crawl_legacy_fields(monkeypatch, client):
    """Test that legacy fields are no longer supported and return 422."""
    body = {
        "url": "https://example.com",
        "x_wait_for_selector": "#app",
        "x_wait_time": 7,
        "x_force_headful": True,
    }
    resp = client.post("/crawl", json=body)
    # Legacy fields should now be rejected with 422
    assert resp.status_code == 422


def test_crawl_requires_url(client):
    resp = client.post("/crawl", json={})
    assert resp.status_code == 422


def test_crawl_endpoint_patch_uses_simplenamespace(monkeypatch):
    from app.api import crawl as crawl_module
    from app.schemas.crawl import CrawlRequest, CrawlResponse

    payload = CrawlRequest(url="https://example.com/path/", force_user_data=True)
    patched = MagicMock(return_value=CrawlResponse(
        status="success",
        url="https://example.com/path/",
        html="<html>patched</html>",
    ))
    monkeypatch.setattr(crawl_module, "crawl", patched)

    response = crawl_module.crawl_endpoint(payload)

    patched.assert_called_once()
    req_obj = patched.call_args.kwargs["request"]
    assert isinstance(req_obj, SimpleNamespace)
    assert req_obj.url == "https://example.com/path"
    assert req_obj.wait_for_selector == "body"
    assert req_obj.wait_for_selector_state == "attached"
    assert req_obj.timeout_seconds is None
    assert req_obj.network_idle is False
    assert req_obj.force_headful is False
    assert req_obj.force_user_data is True
    assert response is patched.return_value


def test_crawl_endpoint_patch_fallback_json_response(monkeypatch):
    from app.api import crawl as crawl_module
    from app.schemas.crawl import CrawlRequest

    payload = CrawlRequest(url="https://fallback.example.com/", force_user_data=False)
    fallback_result = SimpleNamespace(status_code=207, json={"status": "patched"})
    patched = MagicMock(return_value=fallback_result)
    monkeypatch.setattr(crawl_module, "crawl", patched)

    response = crawl_module.crawl_endpoint(payload)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 207
    assert json.loads(response.body) == {"status": "patched"}

    patched.assert_called_once()
    req_obj = patched.call_args.kwargs["request"]
    assert isinstance(req_obj, SimpleNamespace)
    assert req_obj.url == "https://fallback.example.com"
    assert req_obj.wait_for_selector == "body"
    assert req_obj.wait_for_selector_state == "attached"
    assert req_obj.timeout_seconds is None
    assert req_obj.network_idle is False
    assert req_obj.force_headful is False
    assert req_obj.force_user_data is False


def test_crawl_endpoint_mock_without_json_payload(monkeypatch):
    from app.api import crawl as crawl_module
    from app.schemas.crawl import CrawlRequest

    payload = CrawlRequest(url="https://fallback.example.com/", force_user_data=True)
    fallback_result = MagicMock(spec_set=["status_code"], status_code=555)
    patched = MagicMock(return_value=fallback_result)
    monkeypatch.setattr(crawl_module, "crawl", patched)

    response = crawl_module.crawl_endpoint(payload)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 555
    assert json.loads(response.body) == {}

    patched.assert_called_once()
    req_obj = patched.call_args.kwargs["request"]
    assert isinstance(req_obj, SimpleNamespace)
    assert req_obj.url == "https://fallback.example.com"
    assert req_obj.wait_for_selector == "body"
    assert req_obj.wait_for_selector_state == "attached"
    assert req_obj.timeout_seconds is None
    assert req_obj.network_idle is False
    assert req_obj.force_headful is False
    assert req_obj.force_user_data is True


def test_crawl_rejects_non_json_content_type(monkeypatch, client):
    """Ensure middleware blocks non-JSON requests before hitting crawler."""
    from app.api import crawl as crawl_module

    crawl_spy = MagicMock()
    monkeypatch.setattr(crawl_module, "crawl", crawl_spy)

    response = client.post(
        "/crawl",
        data="plain text body",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["header", "Content-Type"],
                "msg": "Content-Type must be application/json",
                "type": "value_error.content_type",
            }
        ]
    }
    crawl_spy.assert_not_called()
