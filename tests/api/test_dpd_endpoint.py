import json

import pytest


def test_dpd_crawl_success_with_stub(monkeypatch, client):
    """Test successful DPD crawl via API endpoint."""
    from app.services.crawler.dpd import DPDCrawler
    from app.schemas.dpd import DPDCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        # capture for assertions
        captured_payload["payload"] = payload
        return DPDCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>DPD tracking results</html>"
        )

    # monkeypatch the service function used by the route
    monkeypatch.setattr(DPDCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "12345678901234"
    }
    resp = client.post("/crawl/dpd", json=body)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tracking_code"] == "12345678901234"
    assert data["html"] == "<html>DPD tracking results</html>"
    assert data["message"] is None

    # ensure payload mapping worked
    p = captured_payload["payload"]
    assert p.tracking_code == body["tracking_code"]
    assert p.force_user_data is False
    assert p.force_headful is False


def test_dpd_crawl_with_all_flags(monkeypatch, client):
    """Test DPD crawl with all optional flags set."""
    from app.services.crawler.dpd import DPDCrawler
    from app.schemas.dpd import DPDCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return DPDCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>DPD tracking with flags</html>"
        )

    monkeypatch.setattr(DPDCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "12345678901234",
        "force_user_data": True,
        "force_headful": True
    }
    resp = client.post("/crawl/dpd", json=body)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tracking_code"] == "12345678901234"

    # Check that flags were passed correctly
    p = captured_payload["payload"]
    assert p.tracking_code == "12345678901234"
    assert p.force_user_data is True
    assert p.force_headful is True


def test_dpd_crawl_failure_with_stub(monkeypatch, client):
    """Test DPD crawl failure via API endpoint."""
    from app.services.crawler.dpd import DPDCrawler
    from app.schemas.dpd import DPDCrawlResponse

    def _fake_crawl_run(self, payload):
        return DPDCrawlResponse(
            status="failure",
            tracking_code=payload.tracking_code,
            message="HTTP status: 404"
        )

    monkeypatch.setattr(DPDCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "12345678901234"
    }
    resp = client.post("/crawl/dpd", json=body)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failure"
    assert data["tracking_code"] == "12345678901234"
    assert data["html"] is None
    assert data["message"] == "HTTP status: 404"


def test_dpd_crawl_requires_tracking_code(client):
    """Test that tracking_code is required."""
    resp = client.post("/crawl/dpd", json={})
    assert resp.status_code == 422
    
    error_detail = resp.json()
    assert "detail" in error_detail
    # Check that the error mentions tracking_code
    error_str = str(error_detail["detail"])
    assert "tracking_code" in error_str


def test_dpd_crawl_empty_tracking_code(client):
    """Test that empty tracking_code is rejected."""
    body = {
        "tracking_code": ""
    }
    resp = client.post("/crawl/dpd", json=body)
    assert resp.status_code == 422
    
    error_detail = resp.json()
    error_str = str(error_detail["detail"])
    assert "tracking_code must be a non-empty string" in error_str


def test_dpd_crawl_whitespace_tracking_code(client):
    """Test that whitespace-only tracking_code is rejected."""
    body = {
        "tracking_code": "   "
    }
    resp = client.post("/crawl/dpd", json=body)
    assert resp.status_code == 422
    
    error_detail = resp.json()
    error_str = str(error_detail["detail"])
    assert "tracking_code must be a non-empty string" in error_str


def test_dpd_crawl_trimmed_tracking_code(monkeypatch, client):
    """Test that tracking_code is trimmed of whitespace."""
    from app.services.crawler.dpd import DPDCrawler
    from app.schemas.dpd import DPDCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return DPDCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>DPD tracking</html>"
        )

    monkeypatch.setattr(DPDCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "  12345678901234  "
    }
    resp = client.post("/crawl/dpd", json=body)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracking_code"] == "12345678901234"
    
    # Check that the service received the trimmed code
    p = captured_payload["payload"]
    assert p.tracking_code == "12345678901234"


def test_dpd_crawl_default_values(monkeypatch, client):
    """Test that optional flags default to False."""
    from app.services.crawler.dpd import DPDCrawler
    from app.schemas.dpd import DPDCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return DPDCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>DPD tracking</html>"
        )

    monkeypatch.setattr(DPDCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "12345678901234"
    }
    resp = client.post("/crawl/dpd", json=body)
    
    assert resp.status_code == 200
    
    # Check defaults
    p = captured_payload["payload"]
    assert p.force_user_data is False
    assert p.force_headful is False


def test_dpd_crawl_explicit_false_values(monkeypatch, client):
    """Test that explicitly setting False values works."""
    from app.services.crawler.dpd import DPDCrawler
    from app.schemas.dpd import DPDCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return DPDCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>DPD tracking</html>"
        )

    monkeypatch.setattr(DPDCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "12345678901234",
        "force_user_data": False,
        "force_headful": False
    }
    resp = client.post("/crawl/dpd", json=body)
    
    assert resp.status_code == 200
    
    # Check explicit False values
    p = captured_payload["payload"]
    assert p.force_user_data is False
    assert p.force_headful is False


def test_dpd_crawl_invalid_json(client):
    """Test that invalid JSON is handled properly."""
    resp = client.post(
        "/crawl/dpd", 
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422


def test_dpd_crawl_additional_fields_ignored(monkeypatch, client):
    """Test that additional fields in request are ignored gracefully."""
    from app.services.crawler.dpd import DPDCrawler
    from app.schemas.dpd import DPDCrawlResponse

    captured_payload = {}

    def _fake_crawl_run(self, payload):
        captured_payload["payload"] = payload
        return DPDCrawlResponse(
            status="success",
            tracking_code=payload.tracking_code,
            html="<html>DPD tracking</html>"
        )

    monkeypatch.setattr(DPDCrawler, "run", _fake_crawl_run)

    body = {
        "tracking_code": "12345678901234",
        "extra_field": "should be ignored",
        "another_field": 123
    }
    resp = client.post("/crawl/dpd", json=body)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tracking_code"] == "12345678901234"