import pytest

from tests.integration.crawl._real_url_test_utils import make_body, min_html_length

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


def test_crawl_17track(client):
    body = make_body("https://t.17track.net/en#nums=1ZXH95910326694965")
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= min_html_length()


def test_crawl_dpex(client):
    body = make_body("https://dpexonline.com/trace-and-track/index?id=226006280426")
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= min_html_length()


def test_crawl_parcelsapp(client):
    body = make_body("https://parcelsapp.com/en/tracking/9200190381599918197427")
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= min_html_length()


def test_crawl_laposte(client):
    body = make_body("https://www.laposte.fr/outils/suivre-vos-envois?code=LA866151484GB")
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= min_html_length()
