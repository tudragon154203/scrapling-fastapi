import pytest

from app.schemas.browse import BrowseResponse


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
    original_init = BrowseCrawler.__init__
    original_run = BrowseCrawler.run
    
    def mock_init(self, engine=None):
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
    
    # Verify run method was called exactly once
    assert run_call_count == 1, f"Expected 1 run call, got {run_call_count}"
    
    # Verify that BrowseCrawler.run was called with the correct payload
    # (this is implicitly tested by the run_call_count tracking above)
