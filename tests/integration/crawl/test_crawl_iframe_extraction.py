"""Integration test for /crawl endpoint iframe extraction from non-USA website."""

import re
import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_crawl_toplogistics_au_iframe_extraction(client):
    """Test iframe extraction from toplogistics.com.au tracking page.

    This test targets the Australian logistics website to verify that
    the /crawl endpoint can properly extract and return iframe content
    from tracking search results, specifically verifying that iframe
    content between tags is greater than 500 characters.
    """
    url = "https://toplogistics.com.au/?s=33EVH0316086"

    body = {
        "url": url,
        "wait_for_selector": "body",
        "wait_for_selector_state": "visible",
        "network_idle": True,
        "timeout_seconds": 60,
    }

    resp = client.post("/crawl", json=body)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "success", data.get("message")

    html = data.get("html") or ""
    assert len(html) > 500, "HTML content should be substantial"

    # Check that we got actual HTML content
    assert "<html" in html.lower()
    assert "</html>" in html.lower()

    # Specifically look for iframe tags in the content
    assert "<iframe" in html.lower(), f"Expected iframe tags in response from {url}"

    # Extract content between iframe tags using regex
    iframe_pattern = re.compile(r'<iframe[^>]*>(.*?)</iframe>', re.IGNORECASE | re.DOTALL)
    iframe_matches = iframe_pattern.findall(html)

    assert len(iframe_matches) > 0, "Expected at least one iframe with content"

    # Verify that the content between iframe tags is substantial (> 500 characters)
    total_iframe_content = ''.join(iframe_matches)
    assert len(total_iframe_content) > 500, f"Expected iframe content > 500 characters, got {len(total_iframe_content)}"

    # Also verify individual iframe content if there are multiple
    for i, content in enumerate(iframe_matches):
        print(f"Iframe {i+1} content length: {len(content)} characters")

    print(f"Successfully extracted iframe content from {url}")
    print(f"Response HTML length: {len(html)}")
    print(f"Found {len(iframe_matches)} iframe(s)")
    print(f"Total iframe content length: {len(total_iframe_content)} characters")
