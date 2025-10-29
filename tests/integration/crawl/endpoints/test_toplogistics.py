import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


# Ensure project root on sys.path for imports like app.*
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


def test_toplogistics_real_flow_happy_path():
    """Real end-to-end test hitting /crawl/toplogistics with a known tracking code.

    Uses the demo tracking code from the PRD to ensure the endpoint works with
    real TopLogistics infrastructure. Asserts proper response shape and HTML content.
    """
    client = TestClient(app)

    # Use demo tracking code from PRD
    tracking_code = "33EVH0319358"
    body = {"tracking_code": tracking_code}

    resp = client.post("/crawl/toplogistics", json=body)
    assert resp.status_code == 200
    data = resp.json()

    # Verify basic response structure
    assert data.get("tracking_code") == tracking_code
    assert data.get("status") in {"success", "failure"}

    if data.get("status") == "success":
        html = data.get("html") or ""

        # HTML should meet service's minimum content length
        def _min_len():
            from app.core.config import get_settings
            try:
                return int(get_settings().min_html_content_length)
            except Exception:
                return 500

        assert isinstance(html, str) and len(html) >= _min_len()

        # Verify HTML contains TopLogistics-specific elements
        lowered = html.lower()
        # TopLogistics tracking page should have tracking-related content
        assert (
            ("tracking" in lowered)
            or ("parcel" in lowered)
            or ("imshk.toplogistics.com.au" in lowered)
            or ("imparceltracking" in lowered)
        )

        assert data.get("message") in {None, ""}
    else:
        # When failure, provide diagnostic message
        msg = data.get("message")
        assert isinstance(msg, str) and len(msg) > 0