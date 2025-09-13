

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
        "wait_for_selector": "body",
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
    assert p.wait_for_selector == body["wait_for_selector"]
    assert p.timeout_seconds == body["timeout_seconds"]


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
