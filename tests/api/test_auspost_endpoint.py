
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.responses import JSONResponse


def test_auspost_crawl_success_with_stub(monkeypatch, client):
    from app.services.crawler.auspost import AuspostCrawler
    from app.schemas.auspost import AuspostCrawlResponse
    import threading

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return AuspostCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html><h3 id=\"trackingPanelHeading\">Details</h3></html>",
        )

    monkeypatch.setattr(AuspostCrawler, "run", _fake_crawl_run)

    body = {"tracking_code": "36LB4503170001000930309"}

    def test_with_timeout():
        return client.post("/crawl/auspost", json=body)

    # Add timeout wrapper to prevent hanging
    def run_with_timeout(func, timeout=45):
        result = [None]
        exception = [None]

        def target():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            raise TimeoutError(f"Test timed out after {timeout} seconds")

        if exception[0]:
            raise exception[0]

        return result[0]

    resp = run_with_timeout(test_with_timeout)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tracking_code"] == "36LB4503170001000930309"
    assert "trackingPanelHeading" in data["html"]
    assert data.get("message") is None

    p = captured_payload["payload"]
    assert p.tracking_code == body["tracking_code"]
    assert p.force_user_data is False
    assert p.force_headful is False


def test_auspost_crawl_with_all_flags(monkeypatch, client):
    from app.services.crawler.auspost import AuspostCrawler
    from app.schemas.auspost import AuspostCrawlResponse
    import threading

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return AuspostCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>ok</html>",
        )

    monkeypatch.setattr(AuspostCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "ABC123",
        "force_user_data": True,
        "force_headful": False,
    }

    def test_with_timeout():
        return client.post("/crawl/auspost", json=body)

    # Add timeout wrapper to prevent hanging
    def run_with_timeout(func, timeout=45):
        result = [None]
        exception = [None]

        def target():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            raise TimeoutError(f"Test timed out after {timeout} seconds")

        if exception[0]:
            raise exception[0]

        return result[0]

    resp = run_with_timeout(test_with_timeout)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tracking_code"] == "ABC123"

    p = captured_payload["payload"]
    assert p.force_user_data is True
    assert p.force_headful is False


def test_auspost_crawl_requires_tracking_code(client):
    resp = client.post("/crawl/auspost", json={})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "tracking_code" in str(detail)


def test_auspost_crawl_rejects_empty_tracking_code(client):
    resp = client.post("/crawl/auspost", json={"tracking_code": ""})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "tracking_code must be a non-empty string" in str(detail)


def test_auspost_crawl_accepts_full_details_url(monkeypatch, client):
    from app.services.crawler.auspost import AuspostCrawler
    from app.schemas.auspost import AuspostCrawlResponse
    import threading

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return AuspostCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>ok</html>",
        )

    monkeypatch.setattr(AuspostCrawler, "run", _fake_crawl_run)

    url = "https://auspost.com.au/mypost/track/details/36LB45032230"

    def test_with_timeout():
        return client.post("/crawl/auspost", json={"tracking_code": url})

    # Add timeout wrapper to prevent hanging
    def run_with_timeout(func, timeout=45):
        result = [None]
        exception = [None]

        def target():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            raise TimeoutError(f"Test timed out after {timeout} seconds")

        if exception[0]:
            raise exception[0]

        return result[0]

    resp = run_with_timeout(test_with_timeout)

    assert resp.status_code == 200
    data = resp.json()
    # Validator should extract the code from the URL
    assert data["tracking_code"] == "36LB45032230"

    # Payload passed to crawler should be normalized as well
    p = captured_payload["payload"]
    assert p.tracking_code == "36LB45032230"


def test_crawl_auspost_endpoint_patch_passthrough(monkeypatch):
    from app.api import crawl as crawl_module
    from app.schemas.auspost import AuspostCrawlRequest, AuspostCrawlResponse

    payload = AuspostCrawlRequest(tracking_code="AUS123", force_user_data=True)
    object.__setattr__(payload, "details_url", "https://auspost.com.au/mypost/track/details/AUS123")

    patched = MagicMock(return_value=AuspostCrawlResponse(
        status="success",
        tracking_code="AUS123",
        html="<html>patched</html>",
    ))
    monkeypatch.setattr(crawl_module, "crawl_auspost", patched)

    response = crawl_module.crawl_auspost_endpoint(payload)

    patched.assert_called_once()
    req_obj = patched.call_args.kwargs["request"]
    assert isinstance(req_obj, SimpleNamespace)
    assert req_obj.tracking_code == "AUS123"
    assert req_obj.details_url == "https://auspost.com.au/mypost/track/details/AUS123"
    assert req_obj.force_user_data is True
    assert response is patched.return_value


def test_crawl_auspost_endpoint_patch_fallback(monkeypatch):
    from app.api import crawl as crawl_module
    from app.schemas.auspost import AuspostCrawlRequest

    payload = AuspostCrawlRequest(tracking_code="ZXCVBN")
    object.__setattr__(payload, "details_url", None)

    fallback_result = SimpleNamespace(status_code=503)
    patched = MagicMock(return_value=fallback_result)
    monkeypatch.setattr(crawl_module, "crawl_auspost", patched)

    response = crawl_module.crawl_auspost_endpoint(payload)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert json.loads(response.body) == {}

    patched.assert_called_once()
    req_obj = patched.call_args.kwargs["request"]
    assert isinstance(req_obj, SimpleNamespace)
    assert req_obj.tracking_code == "ZXCVBN"
    assert hasattr(req_obj, "details_url")
    assert req_obj.details_url is None
    assert req_obj.force_user_data is False


def test_auspost_endpoint_mock_without_json_payload(monkeypatch):
    """Ensure crawl_auspost patched with mock lacking `.json` triggers empty JSON fallback."""
    from app.api import crawl as crawl_module
    from app.schemas.auspost import AuspostCrawlRequest

    payload = AuspostCrawlRequest(tracking_code="AUS123456789", force_user_data=False)
    object.__setattr__(payload, "details_url", None)

    fallback_result = MagicMock(spec_set=["status_code"], status_code=512)
    patched = MagicMock(return_value=fallback_result)
    monkeypatch.setattr(crawl_module, "crawl_auspost", patched)

    response = crawl_module.crawl_auspost_endpoint(payload)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 512
    assert json.loads(response.body) == {}

    patched.assert_called_once()
    req_obj = patched.call_args.kwargs["request"]
    assert isinstance(req_obj, SimpleNamespace)
    assert req_obj.tracking_code == "AUS123456789"
    assert hasattr(req_obj, "details_url")
    assert req_obj.details_url is None
    assert req_obj.force_user_data is False
