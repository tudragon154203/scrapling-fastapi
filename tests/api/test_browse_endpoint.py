import pytest

from app.schemas.browse import BrowseResponse


def test_browse_success_with_url(monkeypatch, client):
    """Test successful browse request with URL."""
    from app.services.crawler.browse import BrowseCrawler

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
    from app.services.crawler.browse import BrowseCrawler

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
    from app.services.crawler.browse import BrowseCrawler

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
    from app.services.crawler.browse import BrowseCrawler
    from app.schemas.browse import BrowseResponse

    def _fake_browse_run(self, payload):
        return BrowseResponse(status="failure", message="Lock acquisition failed: already locked")

    monkeypatch.setattr(BrowseCrawler, "run", _fake_browse_run)

    body = {
        "url": "https://example.com"
    }
    resp = client.post("/browse", json=body)

    assert resp.status_code == 409
