from fastapi.responses import JSONResponse
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.unit]


def test_toplogistics_crawl_success_with_stub(monkeypatch, client):
    """Test successful TopLogistics crawl via API endpoint."""
    from app.services.crawler.toplogistics import TopLogisticsCrawler
    from app.schemas.toplogistics import TopLogisticsCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        # capture for assertions
        captured_payload["payload"] = payload
        return TopLogisticsCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>TopLogistics tracking results</html>"
        )

    # monkeypatch service function used by route
    monkeypatch.setattr(TopLogisticsCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "33EVH0319358"
    }
    resp = client.post("/crawl/toplogistics", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tracking_code"] == "33EVH0319358"
    assert data["html"] == "<html>TopLogistics tracking results</html>"
    assert data["message"] is None

    # ensure payload mapping worked
    p = captured_payload["payload"]
    assert p.tracking_code == body["tracking_code"]
    assert p.force_user_data is False
    assert p.force_headful is False


def test_toplogistics_crawl_with_search_url(monkeypatch, client):
    """Test TopLogistics crawl with search URL input."""
    from app.services.crawler.toplogistics import TopLogisticsCrawler
    from app.schemas.toplogistics import TopLogisticsCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return TopLogisticsCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>TopLogistics search URL results</html>"
        )

    monkeypatch.setattr(TopLogisticsCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "https://toplogistics.com.au/?s=33EVH0319358"
    }
    resp = client.post("/crawl/toplogistics", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tracking_code"] == "33EVH0319358"  # Should be extracted
    assert data["html"] == "<html>TopLogistics search URL results</html>"

    # Check that extracted code was passed to service
    p = captured_payload["payload"]
    assert p.tracking_code == "33EVH0319358"


def test_toplogistics_crawl_with_all_flags(monkeypatch, client):
    """Test TopLogistics crawl with all optional flags set."""
    from app.services.crawler.toplogistics import TopLogisticsCrawler
    from app.schemas.toplogistics import TopLogisticsCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return TopLogisticsCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>TopLogistics with flags</html>"
        )

    monkeypatch.setattr(TopLogisticsCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "33EVH0319358",
        "force_user_data": True,
        "force_headful": True
    }
    resp = client.post("/crawl/toplogistics", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tracking_code"] == "33EVH0319358"

    # Check that flags were passed correctly
    p = captured_payload["payload"]
    assert p.tracking_code == "33EVH0319358"
    assert p.force_user_data is True
    assert p.force_headful is True


def test_toplogistics_crawl_failure_with_stub(monkeypatch, client):
    """Test TopLogistics crawl failure via API endpoint."""
    from app.services.crawler.toplogistics import TopLogisticsCrawler
    from app.schemas.toplogistics import TopLogisticsCrawlResponse

    def _fake_crawl_run(self, payload):
        return TopLogisticsCrawlResponse(
            status="failure",
            tracking_code=payload.tracking_code,
            message="HTTP status: 404"
        )

    monkeypatch.setattr(TopLogisticsCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "33EVH0319358"
    }
    resp = client.post("/crawl/toplogistics", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failure"
    assert data["tracking_code"] == "33EVH0319358"
    assert data["html"] is None
    assert data["message"] == "HTTP status: 404"


def test_toplogistics_crawl_requires_tracking_code(client):
    """Test that tracking_code is required."""
    resp = client.post("/crawl/toplogistics", json={})
    assert resp.status_code == 422

    error_detail = resp.json()
    assert "detail" in error_detail
    # Check that error mentions tracking_code
    error_str = str(error_detail["detail"])
    assert "tracking_code" in error_str


def test_toplogistics_crawl_empty_tracking_code(client):
    """Test that empty tracking_code is rejected."""
    body = {
        "tracking_code": ""
    }
    resp = client.post("/crawl/toplogistics", json=body)
    assert resp.status_code == 422

    error_detail = resp.json()
    error_str = str(error_detail["detail"])
    assert "tracking_code must be a non-empty string" in error_str


def test_toplogistics_crawl_whitespace_tracking_code(client):
    """Test that whitespace-only tracking_code is rejected."""
    body = {
        "tracking_code": "   "
    }
    resp = client.post("/crawl/toplogistics", json=body)
    assert resp.status_code == 422

    error_detail = resp.json()
    error_str = str(error_detail["detail"])
    assert "tracking_code must be a non-empty string" in error_str


def test_toplogistics_crawl_invalid_search_url(client):
    """Test that search URL without s parameter is rejected."""
    body = {
        "tracking_code": "https://toplogistics.com.au/"
    }
    resp = client.post("/crawl/toplogistics", json=body)
    assert resp.status_code == 422

    error_detail = resp.json()
    error_str = str(error_detail["detail"])
    assert "could not extract 's' parameter" in error_str


def test_toplogistics_crawl_trimmed_tracking_code(monkeypatch, client):
    """Test that tracking_code is trimmed of whitespace."""
    from app.services.crawler.toplogistics import TopLogisticsCrawler
    from app.schemas.toplogistics import TopLogisticsCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return TopLogisticsCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>TopLogistics tracking</html>"
        )

    monkeypatch.setattr(TopLogisticsCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "  33EVH0319358  "
    }
    resp = client.post("/crawl/toplogistics", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["tracking_code"] == "33EVH0319358"

    # Check that service received the trimmed code
    p = captured_payload["payload"]
    assert p.tracking_code == "33EVH0319358"


def test_toplogistics_crawl_default_values(monkeypatch, client):
    """Test that optional flags default to False."""
    from app.services.crawler.toplogistics import TopLogisticsCrawler
    from app.schemas.toplogistics import TopLogisticsCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return TopLogisticsCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>TopLogistics tracking</html>"
        )

    monkeypatch.setattr(TopLogisticsCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "33EVH0319358"
    }
    resp = client.post("/crawl/toplogistics", json=body)

    assert resp.status_code == 200

    # Check defaults
    p = captured_payload["payload"]
    assert p.force_user_data is False
    assert p.force_headful is False


def test_toplogistics_crawl_explicit_false_values(monkeypatch, client):
    """Test that explicitly setting False values works."""
    from app.services.crawler.toplogistics import TopLogisticsCrawler
    from app.schemas.toplogistics import TopLogisticsCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return TopLogisticsCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>TopLogistics tracking</html>"
        )

    monkeypatch.setattr(TopLogisticsCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "33EVH0319358",
        "force_user_data": False,
        "force_headful": False
    }
    resp = client.post("/crawl/toplogistics", json=body)

    assert resp.status_code == 200

    # Check explicit False values
    p = captured_payload["payload"]
    assert p.force_user_data is False
    assert p.force_headful is False


def test_toplogistics_crawl_invalid_json(client):
    """Test that invalid JSON is handled properly."""
    resp = client.post(
        "/crawl/toplogistics",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422


def test_toplogistics_crawl_additional_fields_rejected(client):
    """Test that additional fields in request are rejected."""
    body = {
        "tracking_code": "33EVH0319358",
        "extra_field": "should be rejected",
        "another_field": 123
    }
    resp = client.post("/crawl/toplogistics", json=body)

    assert resp.status_code == 422
    error_detail = resp.json()
    assert "detail" in error_detail
    error_str = str(error_detail["detail"])
    assert "extra" in error_str.lower() or "forbid" in error_str.lower()


def test_crawl_toplogistics_endpoint_patch_passthrough(monkeypatch):
    """Test endpoint behavior when crawl_toplogistics function is patched."""
    from app.api import crawl as crawl_module
    from app.schemas.toplogistics import TopLogisticsCrawlRequest, TopLogisticsCrawlResponse

    payload = TopLogisticsCrawlRequest(tracking_code=" 33EVH0319358 ", force_user_data=True)
    patched = MagicMock(return_value=TopLogisticsCrawlResponse(
        status="success",
        tracking_code="33EVH0319358",
        html="<html>patched</html>",
    ))
    monkeypatch.setattr(crawl_module, "crawl_toplogistics", patched)

    response = crawl_module.crawl_toplogistics_endpoint(payload)

    patched.assert_called_once()
    req_obj = patched.call_args.kwargs["request"]
    assert isinstance(req_obj, SimpleNamespace)
    assert req_obj.tracking_code == "33EVH0319358"
    assert req_obj.force_user_data is True
    assert response is patched.return_value


def test_crawl_toplogistics_endpoint_patch_fallback(monkeypatch):
    """Test endpoint fallback behavior when crawl_toplogistics returns mock-like result."""
    from app.api import crawl as crawl_module
    from app.schemas.toplogistics import TopLogisticsCrawlRequest

    payload = TopLogisticsCrawlRequest(tracking_code="33EVH0319358", force_user_data=False)
    fallback_result = SimpleNamespace(status_code="418", json={"error": "teapot"})
    patched = MagicMock(return_value=fallback_result)
    monkeypatch.setattr(crawl_module, "crawl_toplogistics", patched)

    response = crawl_module.crawl_toplogistics_endpoint(payload)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 418
    assert json.loads(response.body) == {"error": "teapot"}

    patched.assert_called_once()
    req_obj = patched.call_args.kwargs["request"]
    assert isinstance(req_obj, SimpleNamespace)
    assert req_obj.tracking_code == "33EVH0319358"
    assert req_obj.force_user_data is False


def test_toplogistics_endpoint_mock_without_json_payload(monkeypatch, client):
    """Ensure API fallback returns empty JSON when patched crawl_toplogistics lacks `.json`."""
    from app.api import crawl as crawl_module

    fallback_result = MagicMock(spec_set=["status_code"], status_code=511)
    patched = MagicMock(return_value=fallback_result)
    monkeypatch.setattr(crawl_module, "crawl_toplogistics", patched)

    resp = client.post("/crawl/toplogistics", json={"tracking_code": "33EVH0319358"})

    assert resp.status_code == 511
    assert resp.json() == {}

    patched.assert_called_once()
    req_obj = patched.call_args.kwargs["request"]
    assert isinstance(req_obj, SimpleNamespace)
    assert req_obj.tracking_code == "33EVH0319358"
    assert req_obj.force_user_data is False
