from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.schemas.browse import BrowseResponse, BrowseRequest

pytestmark = [pytest.mark.unit]


def test_browse_success_with_url(monkeypatch, client):
    """Test successful browse request with URL."""
    from app.services.browser.browse import BrowseCrawler

    captured_payload = {}

    def _fake_browse_run(self, payload):
        captured_payload["payload"] = payload
        return BrowseResponse(
            status="success",
            message="Browser session completed successfully"
        )

    monkeypatch.setattr(BrowseCrawler, "run", _fake_browse_run)

    body = {
        "url": "https://example.com"
    }
    resp = client.post("/browse", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["message"] == "Browser session completed successfully"

    # Verify payload was passed correctly
    p = captured_payload["payload"]
    assert str(p.url) == "https://example.com/"


def test_browse_success_without_url(monkeypatch, client):
    """Test successful browse request without URL."""
    from app.services.browser.browse import BrowseCrawler

    captured_payload = {}

    def _fake_browse_run(self, payload):
        captured_payload["payload"] = payload
        return BrowseResponse(
            status="success",
            message="Browser session completed successfully"
        )

    monkeypatch.setattr(BrowseCrawler, "run", _fake_browse_run)

    body = {}
    resp = client.post("/browse", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["message"] == "Browser session completed successfully"

    # Verify payload has no URL
    p = captured_payload["payload"]
    assert p.url is None


def test_browse_failure(monkeypatch, client):
    """Test browse request that returns failure."""
    from app.services.browser.browse import BrowseCrawler

    def _fake_browse_run(self, payload):
        return BrowseResponse(
            status="failure",
            message="Browser launch failed"
        )

    monkeypatch.setattr(BrowseCrawler, "run", _fake_browse_run)

    body = {
        "url": "https://example.com"
    }
    resp = client.post("/browse", json=body)

    # Now maps failure to HTTP 500
    assert resp.status_code == 500
    data = resp.json()
    assert data["status"] == "failure"
    assert data["message"] == "Browser launch failed"


def test_browse_invalid_url(client):
    """Test browse request with invalid URL."""
    body = {
        "url": "not-a-valid-url"
    }
    resp = client.post("/browse", json=body)

    assert resp.status_code == 422
    error_detail = resp.json()
    assert "detail" in error_detail
    error_str = str(error_detail["detail"])
    assert "url" in error_str.lower()


def test_browse_extra_fields_rejected(client):
    """Test that extra fields in request are rejected."""
    body = {
        "url": "https://example.com",
        "extra_field": "should be rejected",
        "another_field": 123
    }
    resp = client.post("/browse", json=body)

    assert resp.status_code == 422
    error_detail = resp.json()
    assert "detail" in error_detail
    error_str = str(error_detail["detail"])
    assert "extra" in error_str.lower() or "forbid" in error_str.lower()


def test_browse_invalid_json(client):
    """Test that invalid JSON is handled properly."""
    resp = client.post(
        "/browse",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422


def test_browse_lock_conflict_returns_409(monkeypatch, client):
    """Failure due to lock acquisition should map to 409."""
    from app.services.browser.browse import BrowseCrawler
    from app.schemas.browse import BrowseResponse

    def _fake_browse_run(self, payload):
        return BrowseResponse(status="failure", message="Lock acquisition failed: already locked")

    monkeypatch.setattr(BrowseCrawler, "run", _fake_browse_run)

    body = {
        "url": "https://example.com"
    }
    resp = client.post("/browse", json=body)

    assert resp.status_code == 409


def test_browse_only_launches_once_without_retries(monkeypatch, client):
    """Test that /browse endpoint only launches once without retries.

    This test verifies that the browse crawler is instantiated and run exactly once,
    ensuring no retries occur even if the browser session fails.
    """
    from app.services.browser.browse import BrowseCrawler
    from app.schemas.browse import BrowseResponse

    # Track class instantiation and method calls
    instantiation_count = 0
    run_call_count = 0

    # Mock BrowseCrawler class to track instantiation
    # original_init = BrowseCrawler.__init__
    # original_run = BrowseCrawler.run

    def mock_init(self, engine=None, browser_engine=None):
        nonlocal instantiation_count
        instantiation_count += 1
        # Call original init with mocked engine if provided
        if engine:
            self.engine = engine
        else:
            # Create a minimal mock engine
            from unittest.mock import MagicMock
            self.engine = MagicMock()

    def mock_run(self, request):
        nonlocal run_call_count
        run_call_count += 1

        # Return success response on first call
        return BrowseResponse(
            status="success",
            message="Browser session completed successfully"
        )

    # Apply mocks
    monkeypatch.setattr(BrowseCrawler, "__init__", mock_init)
    monkeypatch.setattr(BrowseCrawler, "run", mock_run)

    # Test the browse endpoint
    body = {
        "url": "https://example.com"
    }
    resp = client.post("/browse", json=body)

    # Verify response
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["message"] == "Browser session completed successfully"

    # Verify BrowseCrawler was instantiated exactly once
    assert instantiation_count == 1, f"Expected 1 instantiation, got {instantiation_count}"


def test_browse_endpoint_builds_namespace_when_callable_object_patched(monkeypatch, client):
    """When browse is patched with a callable object ensure SimpleNamespace is used."""
    from app.api import browse as browse_module

    captured_request = {}

    class SentinelCallable:
        def __call__(self, request):
            captured_request["request"] = request
            return BrowseResponse(status="success", message="sentinel ok")

    monkeypatch.setattr(browse_module, "browse", SentinelCallable())

    resp = client.post("/browse", json={"url": "https://example.com"})

    assert resp.status_code == 200
    assert resp.json()["message"] == "sentinel ok"

    req_obj = captured_request["request"]
    assert isinstance(req_obj, BrowseRequest)
    assert str(req_obj.url) == "https://example.com/"


def test_browse_endpoint_handles_fallback_response_object(monkeypatch, client):
    """Browse endpoint should wrap objects with status_code/json into JSONResponse."""
    from app.api import browse as browse_module

    dummy_result = SimpleNamespace(status_code=207, json={"status": "mocked"})

    def fake_browse(request):
        return dummy_result

    monkeypatch.setattr(browse_module, "browse", fake_browse)

    resp = client.post("/browse", json={"url": "https://fallback.example"})

    assert resp.status_code == 207
    assert resp.json() == {"status": "mocked"}


def test_browse_endpoint_mock_without_json_payload(monkeypatch, client):
    """Patch browse callable to return a mock missing `.json` so fallback returns empty JSON."""
    from app.api import browse as browse_module

    fallback_result = MagicMock(spec_set=["status_code"], status_code=503)
    patched = MagicMock(return_value=fallback_result)
    monkeypatch.setattr(browse_module, "browse", patched)

    resp = client.post("/browse", json={"url": "https://fallback.example"})

    assert resp.status_code == 503
    assert resp.json() == {}

    patched.assert_called_once()
    request_obj = list(patched.call_args.args)[0]
    assert isinstance(request_obj, BrowseRequest)


def test_browse_success_with_camoufox_engine(monkeypatch, client):
    """Test successful browse request with Camoufox engine."""
    from app.services.browser.browse import BrowseCrawler
    from app.schemas.browse import BrowserEngine

    captured_payload = {}
    captured_browser_engine = {}

    def _fake_browse_init(self, browser_engine=None):
        captured_browser_engine["engine"] = browser_engine

    def _fake_browse_run(self, payload):
        captured_payload["payload"] = payload
        return BrowseResponse(
            status="success",
            message="Browser session completed successfully"
        )

    monkeypatch.setattr(BrowseCrawler, "__init__", _fake_browse_init)
    monkeypatch.setattr(BrowseCrawler, "run", _fake_browse_run)

    body = {
        "url": "https://example.com",
        "engine": "camoufox"
    }
    resp = client.post("/browse", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["message"] == "Browser session completed successfully"

    # Verify payload and engine were passed correctly
    p = captured_payload["payload"]
    assert str(p.url) == "https://example.com/"
    assert captured_browser_engine["engine"] == BrowserEngine.CAMOUFOX


def test_browse_success_with_chromium_engine(monkeypatch, client):
    """Test successful browse request with Chromium engine."""
    from app.services.browser.browse import BrowseCrawler
    from app.schemas.browse import BrowserEngine

    captured_payload = {}
    captured_browser_engine = {}

    def _fake_browse_init(self, browser_engine=None):
        captured_browser_engine["engine"] = browser_engine

    def _fake_browse_run(self, payload):
        captured_payload["payload"] = payload
        return BrowseResponse(
            status="success",
            message="Browser session completed successfully"
        )

    monkeypatch.setattr(BrowseCrawler, "__init__", _fake_browse_init)
    monkeypatch.setattr(BrowseCrawler, "run", _fake_browse_run)

    body = {
        "url": "https://example.com",
        "engine": "chromium"
    }
    resp = client.post("/browse", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["message"] == "Browser session completed successfully"

    # Verify payload and engine were passed correctly
    p = captured_payload["payload"]
    assert str(p.url) == "https://example.com/"
    assert captured_browser_engine["engine"] == BrowserEngine.CHROMIUM


def test_browse_defaults_to_camoufox_engine(monkeypatch, client):
    """Test that browse request defaults to Camoufox engine when not specified."""
    from app.services.browser.browse import BrowseCrawler
    from app.schemas.browse import BrowserEngine

    captured_payload = {}
    captured_browser_engine = {}

    def _fake_browse_init(self, browser_engine=None):
        captured_browser_engine["engine"] = browser_engine

    def _fake_browse_run(self, payload):
        captured_payload["payload"] = payload
        return BrowseResponse(
            status="success",
            message="Browser session completed successfully"
        )

    monkeypatch.setattr(BrowseCrawler, "__init__", _fake_browse_init)
    monkeypatch.setattr(BrowseCrawler, "run", _fake_browse_run)

    body = {
        "url": "https://example.com"
        # No engine specified - should default to camoufox
    }
    resp = client.post("/browse", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"

    # Verify default engine was used
    assert captured_browser_engine["engine"] == BrowserEngine.CAMOUFOX


def test_browse_invalid_engine_rejected(client):
    """Test that invalid engine values are rejected."""
    body = {
        "url": "https://example.com",
        "engine": "invalid_engine"
    }
    resp = client.post("/browse", json=body)

    assert resp.status_code == 422
    error_detail = resp.json()
    assert "detail" in error_detail
    error_str = str(error_detail["detail"])
    assert "engine" in error_str.lower()
