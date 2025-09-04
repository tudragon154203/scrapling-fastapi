import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Ensure project root on sys.path for imports like app.*
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app


pytestmark = pytest.mark.integration


# Ensure scrapling is available; if not, fail loudly to surface missing dependency
try:  # pragma: no cover
    import scrapling.fetchers  # noqa: F401
except Exception as exc:  # pragma: no cover
    pytest.fail(f"scrapling is required for integration tests: {exc}")


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
        # HTML should be non-empty
        assert isinstance(html, str) and len(html) > 0
        # Optional soft assertion: the domain name should appear somewhere
        assert "dpd" in html.lower()
    else:
        # When failure, a message should be present for diagnostics
        assert isinstance(data.get("message"), str) and len(data.get("message")) > 0

