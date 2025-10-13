import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# Integration tests use the real endpoint and fetcher

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


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
        "wait_for_selector": selector,
        "wait_for_selector_state": "visible",
        "timeout_seconds": 30,
        "network_idle": True,
    }
    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success", data.get("message")
    html = data.get("html") or ""
    assert expect_text in html
