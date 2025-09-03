import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Integration tests use the real endpoint and fetcher
from app.main import app

pytestmark = pytest.mark.integration

# Ensure scrapling is available; if not, fail loudly to surface missing dependency
try:
    import scrapling.fetchers  # noqa: F401
except Exception as exc:  # pragma: no cover
    pytest.fail(f"scrapling is required for integration tests: {exc}")


@pytest.mark.parametrize(
    "url,selector,expect_text",
    [
        ("https://example.com", "h1", "Example Domain"),
        ("https://httpbin.org/html", "h1", "Herman Melville - Moby-Dick"),
    ],
)
def test_crawl_real_sites(url, selector, expect_text):
    client = TestClient(app)
    body = {
        "url": url,
        "wait_selector": selector,
        "wait_selector_state": "visible",
        "timeout_ms": 30000,
        "headless": True,  # force headless mode
        "network_idle": True,
    }
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success", data.get("message")
    html = data.get("html") or ""
    assert expect_text in html
