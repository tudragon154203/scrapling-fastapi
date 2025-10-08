import pytest

import pytest

pytestmark = [pytest.mark.unit]


from app.schemas.auspost import AuspostCrawlRequest


def test_auspost_request_requires_tracking_code():
    with pytest.raises(Exception):
        AuspostCrawlRequest()  # type: ignore[arg-type]


def test_auspost_request_rejects_empty_code():
    with pytest.raises(Exception) as ei:
        AuspostCrawlRequest(tracking_code="")
    assert "tracking_code must be a non-empty string" in str(ei.value)


def test_auspost_request_trims_tracking_code():
    req = AuspostCrawlRequest(tracking_code="  ABC123  ")
    assert req.tracking_code == "ABC123"


def test_auspost_request_defaults():
    req = AuspostCrawlRequest(tracking_code="ABC123")
    assert req.force_headful is False
    assert req.force_user_data is False
