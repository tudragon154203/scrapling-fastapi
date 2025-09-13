


def test_auspost_crawl_success_with_stub(monkeypatch, client):
    from app.services.crawler.auspost import AuspostCrawler
    from app.schemas.auspost import AuspostCrawlResponse

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
    resp = client.post("/crawl/auspost", json=body)

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
        "force_headful": True,
    }
    resp = client.post("/crawl/auspost", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tracking_code"] == "ABC123"

    p = captured_payload["payload"]
    assert p.force_user_data is True
    assert p.force_headful is True


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
    resp = client.post("/crawl/auspost", json={"tracking_code": url})

    assert resp.status_code == 200
    data = resp.json()
    # Validator should extract the code from the URL
    assert data["tracking_code"] == "36LB45032230"

    # Payload passed to crawler should be normalized as well
    p = captured_payload["payload"]
    assert p.tracking_code == "36LB45032230"
