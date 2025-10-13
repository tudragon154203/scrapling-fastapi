import pytest

from tests.integration.crawl._real_url_test_utils import make_body, min_html_length

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


def test_crawl_ups(client):
    body = make_body(
        "https://www.ups.com/track?tracknum=1ZXH95910305309465&loc=vi_VN&requester=QUIC/trackdetails"
    )
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= min_html_length()


def test_crawl_fedex(client):
    body = make_body(
        "https://www.fedex.com/fedextrack/?trknbr=883561067070&trkqual=2460902000~883561067070~FX"
    )
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= min_html_length()


def test_crawl_usps(client):
    body = make_body(
        "https://tools.usps.com/go/TrackConfirmAction?tRef=fullpage&tLc=2&text28777=&tLabels=9200190381836321489085%2C&tABt=false"
    )
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= min_html_length()
