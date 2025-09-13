import os
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


@pytest.mark.integration
def test_auspost_real_flow_status_and_shape_with_humanization():
    """Real end-to-end test hitting /crawl/auspost with humanization enabled.

    Asserts API returns 200 and a well-formed response. Accepts success or failure
    due to inherent variability of live sites and anti-bot checks.
    """
    # Ensure humanization is enabled
    original_value = os.environ.get("AUSPOST_HUMANIZE_ENABLED")
    os.environ["AUSPOST_HUMANIZE_ENABLED"] = "true"

    try:
        client = TestClient(app)

        tracking_code = "36LB4503170001000930309"
        body = {"tracking_code": tracking_code}

        resp = client.post("/crawl/auspost", json=body)
        assert resp.status_code == 200
        data = resp.json()

        assert data.get("tracking_code") == tracking_code
        assert data.get("status") in {"success", "failure"}

        if data.get("status") == "success":
            html = data.get("html") or ""
            # HTML should meet the service's minimum content length
            def _min_len():
                from app.core.config import get_settings
                try:
                    return int(get_settings().min_html_content_length)
                except Exception:
                    return 500
            assert isinstance(html, str) and len(html) >= _min_len()
            lowered = html.lower()
            assert (
                ("trackingpanelheading" in lowered)
                or ("<iframe" in lowered)
                or ("auspost.com" in lowered)
            )
            assert data.get("message") in {None, ""}
        else:
            # When failure, provide diagnostic message
            msg = data.get("message")
            assert isinstance(msg, str) and len(msg) > 0
    finally:
        # Restore original environment variable
        if original_value is not None:
            os.environ["AUSPOST_HUMANIZE_ENABLED"] = original_value
        else:
            os.environ.pop("AUSPOST_HUMANIZE_ENABLED", None)


@pytest.mark.integration
def test_auspost_real_flow_status_and_shape_without_humanization():
    """Real end-to-end test hitting /crawl/auspost with humanization disabled.

    Verifies that the flow still works correctly in deterministic mode.
    """
    # Ensure humanization is disabled
    original_value = os.environ.get("AUSPOST_HUMANIZE_ENABLED")
    os.environ["AUSPOST_HUMANIZE_ENABLED"] = "false"

    try:
        client = TestClient(app)

        tracking_code = "36LB4503170001000930309"
        body = {"tracking_code": tracking_code}

        resp = client.post("/crawl/auspost", json=body)
        assert resp.status_code == 200
        data = resp.json()

        assert data.get("tracking_code") == tracking_code
        assert data.get("status") in {"success", "failure"}

        if data.get("status") == "success":
            html = data.get("html") or ""
            # HTML should meet the service's minimum content length
            def _min_len():
                from app.core.config import get_settings
                try:
                    return int(get_settings().min_html_content_length)
                except Exception:
                    return 500
            assert isinstance(html, str) and len(html) >= _min_len()
            lowered = html.lower()
            assert (
                ("trackingpanelheading" in lowered)
                or ("<iframe" in lowered)
                or ("auspost.com" in lowered)
            )
            assert data.get("message") in {None, ""}
        else:
            # When failure, provide diagnostic message
            msg = data.get("message")
            assert isinstance(msg, str) and len(msg) > 0
    finally:
        # Restore original environment variable
        if original_value is not None:
            os.environ["AUSPOST_HUMANIZE_ENABLED"] = original_value
        else:
            os.environ.pop("AUSPOST_HUMANIZE_ENABLED", None)
