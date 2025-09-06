import pytest
from pydantic import ValidationError

from app.schemas.dpd import DPDCrawlRequest, DPDCrawlResponse


class TestDPDCrawlRequest:
    """Test DPD crawl request schema validation."""

    def test_valid_basic_request(self):
        """Test valid basic request with just tracking code."""
        request = DPDCrawlRequest(tracking_code="12345678901234")
        assert request.tracking_code == "12345678901234"
        assert request.force_user_data is False
        assert request.force_headful is False

    def test_valid_request_with_all_fields(self):
        """Test valid request with all optional fields."""
        request = DPDCrawlRequest(
            tracking_code="12345678901234",
            force_user_data=True,
            force_headful=True
        )
        assert request.tracking_code == "12345678901234"
        assert request.force_user_data is True
        assert request.force_headful is True

    def test_tracking_code_trimmed(self):
        """Test that tracking code is trimmed of whitespace."""
        request = DPDCrawlRequest(tracking_code="  12345678901234  ")
        assert request.tracking_code == "12345678901234"

    def test_missing_tracking_code(self):
        """Test that missing tracking code raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            DPDCrawlRequest()
        assert "tracking_code" in str(exc_info.value)

    def test_empty_tracking_code(self):
        """Test that empty tracking code raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            DPDCrawlRequest(tracking_code="")
        assert "tracking_code must be a non-empty string" in str(exc_info.value)

    def test_whitespace_only_tracking_code(self):
        """Test that whitespace-only tracking code raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            DPDCrawlRequest(tracking_code="   ")
        assert "tracking_code must be a non-empty string" in str(exc_info.value)

    def test_defaults_when_not_provided(self):
        """Test that boolean fields default to False when not provided."""
        request = DPDCrawlRequest(tracking_code="12345678901234")
        assert request.force_user_data is False
        assert request.force_headful is False

    def test_explicit_false_values(self):
        """Test that explicitly setting False values works."""
        request = DPDCrawlRequest(
            tracking_code="12345678901234",
            force_user_data=False,
            force_headful=False
        )
        assert request.force_user_data is False
        assert request.force_headful is False


class TestDPDCrawlResponse:
    """Test DPD crawl response schema."""

    def test_success_response(self):
        """Test successful response creation."""
        response = DPDCrawlResponse(
            status="success",
            tracking_code="12345678901234",
            html="<html>tracking info</html>"
        )
        assert response.status == "success"
        assert response.tracking_code == "12345678901234"
        assert response.html == "<html>tracking info</html>"
        assert response.message is None

    def test_failure_response(self):
        """Test failure response creation."""
        response = DPDCrawlResponse(
            status="failure",
            tracking_code="12345678901234",
            message="HTTP status: 404"
        )
        assert response.status == "failure"
        assert response.tracking_code == "12345678901234"
        assert response.html is None
        assert response.message == "HTTP status: 404"

    def test_response_with_all_fields(self):
        """Test response with all fields populated."""
        response = DPDCrawlResponse(
            status="success",
            tracking_code="12345678901234",
            html="<html>tracking info</html>",
            message="Success message"
        )
        assert response.status == "success"
        assert response.tracking_code == "12345678901234"
        assert response.html == "<html>tracking info</html>"
        assert response.message == "Success message"

    def test_required_fields(self):
        """Test that status and tracking_code are required."""
        with pytest.raises(ValidationError) as exc_info:
            DPDCrawlResponse()
        error_msg = str(exc_info.value)
        assert "status" in error_msg
        assert "tracking_code" in error_msg

    def test_missing_status(self):
        """Test that missing status raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            DPDCrawlResponse(tracking_code="12345678901234")
        assert "status" in str(exc_info.value)

    def test_missing_tracking_code(self):
        """Test that missing tracking_code raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            DPDCrawlResponse(status="success")
        assert "tracking_code" in str(exc_info.value)