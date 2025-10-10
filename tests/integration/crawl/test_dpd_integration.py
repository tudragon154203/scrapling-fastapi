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


def test_dpd_real_tracking_number():
    """End-to-end test hitting /crawl/dpd with a real tracking number.

    Uses the provided tracking code. This asserts we get a 200 response from the API
    and that the body indicates success or failure with an HTML payload when successful.
    """
    client = TestClient(app)

    tracking_code = "01126819 7878 09"  # provided real tracking number (keeps spaces)
    body = {
        "tracking_code": tracking_code,
        # Use defaults for headless/user data; keep it minimal for reliability
    }

    resp = client.post("/crawl/dpd", json=body)
    assert resp.status_code == 200
    data = resp.json()

    # Status should be success or failure depending on remote availability
    assert data.get("status") in {"success", "failure"}

    if data.get("status") == "success":
        html = data.get("html") or ""
        # HTML should meet the same minimum length threshold as the service

        def _min_len():
            from app.core.config import get_settings
            try:
                return int(get_settings().min_html_content_length)
            except Exception:
                return 500
        assert isinstance(html, str) and len(html) >= _min_len()
        # Optional soft assertion: the domain name should appear somewhere
        assert "dpd" in html.lower()
    else:
        # When failure, a message should be present for diagnostics
        assert isinstance(data.get("message"), str) and len(data.get("message")) > 0
