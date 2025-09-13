import pytest
from app.core.config import get_settings

pytestmark = pytest.mark.integration


# Disable proxies and keep retries minimal within this module to reduce flakiness/hangs
@pytest.fixture(autouse=True)
def _disable_proxies_and_reduce_retries(monkeypatch):
    from app.core import config as app_config

    real_get_settings = app_config.get_settings

    def _wrapped():
        s = real_get_settings()
        # Create a shallow proxy to override selected fields without mutating cached settings
        class S:
            pass

        x = S()
        for k, v in s.__dict__.items():
            setattr(x, k, v)
        # Disable proxies and reduce retries to single attempt
        x.proxy_list_file_path = None
        x.private_proxy_url = None
        x.max_retries = 1
        # Enable lightweight HTTP fallback to improve resiliency for public sites
        # HTTP fallback removed from service; rely on Scrapling only
        return x

    monkeypatch.setattr(app_config, "get_settings", _wrapped)


def _make_body(url: str) -> dict:
    return {
        "url": url,
        "wait_for_selector": "body",
        "wait_for_selector_state": "visible",
        # Avoid network_idle to prevent hangs on long-polling pages
        "network_idle": False,
        "timeout_seconds": 60,
    }


def _min_len() -> int:
    """Return the service's minimum acceptable HTML length.

    Uses configured `min_html_content_length` when available, with a sane
    default of 500 to avoid trivially short pages passing.
    """
    try:
        s = get_settings()
        v = getattr(s, "min_html_content_length", None)
        return int(v) if v is not None else 500
    except Exception:
        return 500


def test_crawl_17track(client):
    body = _make_body("https://t.17track.net/en#nums=1ZXH95910326694965")
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= _min_len()


def test_crawl_ups(client):
    body = _make_body(
        "https://www.ups.com/track?tracknum=1ZXH95910305309465&loc=vi_VN&requester=QUIC/trackdetails"
    )
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= _min_len()


def test_crawl_fedex(client):
    body = _make_body(
        "https://www.fedex.com/fedextrack/?trknbr=883561067070&trkqual=2460902000~883561067070~FX"
    )
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= _min_len()


def test_crawl_usps(client):
    body = _make_body(
        "https://tools.usps.com/go/TrackConfirmAction?tRef=fullpage&tLc=2&text28777=&tLabels=9200190381836321489085%2C&tABt=false"
    )
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= _min_len()


def test_crawl_dpex(client):
    body = _make_body("https://dpexonline.com/trace-and-track/index?id=226006280426")
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= _min_len()


def test_crawl_parcelsapp(client):
    body = _make_body("https://parcelsapp.com/en/tracking/9200190381599918197427")
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= _min_len()


def test_crawl_laposte(client):
    body = _make_body("https://www.laposte.fr/outils/suivre-vos-envois?code=LA866151484GB")
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    html = data.get("html") or ""
    assert "<html" in html.lower()
    assert len(html) >= _min_len()

