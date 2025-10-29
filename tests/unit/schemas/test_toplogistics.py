from app.schemas.toplogistics import TopLogisticsCrawlRequest, TopLogisticsCrawlResponse
import pytest
from pydantic import ValidationError

pytestmark = [pytest.mark.unit]


class TestTopLogisticsCrawlRequest:
    """Test TopLogistics crawl request schema validation."""

    def test_valid_bare_tracking_code(self):
        """Test valid request with bare tracking code."""
        request = TopLogisticsCrawlRequest(tracking_code="33EVH0319358")
        assert request.tracking_code == "33EVH0319358"
        assert request.force_user_data is False
        assert request.force_headful is False

    def test_valid_search_url(self):
        """Test valid request with search URL containing s parameter."""
        request = TopLogisticsCrawlRequest(
            tracking_code="https://toplogistics.com.au/?s=33EVH0319358"
        )
        assert request.tracking_code == "33EVH0319358"
        assert request.force_user_data is False
        assert request.force_headful is False

    def test_valid_search_url_with_other_params(self):
        """Test valid request with search URL containing multiple parameters."""
        request = TopLogisticsCrawlRequest(
            tracking_code="https://toplogistics.com.au/?s=33EVH0319358&other=value"
        )
        assert request.tracking_code == "33EVH0319358"

    def test_valid_search_url_https(self):
        """Test valid request with HTTPS search URL."""
        request = TopLogisticsCrawlRequest(
            tracking_code="https://toplogistics.com.au/?s=33EVH0319358"
        )
        assert request.tracking_code == "33EVH0319358"

    def test_valid_search_url_http(self):
        """Test valid request with HTTP search URL."""
        request = TopLogisticsCrawlRequest(
            tracking_code="http://toplogistics.com.au/?s=33EVH0319358"
        )
        assert request.tracking_code == "33EVH0319358"

    def test_valid_request_with_all_fields(self):
        """Test valid request with all optional fields."""
        request = TopLogisticsCrawlRequest(
            tracking_code="33EVH0319358",
            force_user_data=True,
            force_headful=True
        )
        assert request.tracking_code == "33EVH0319358"
        assert request.force_user_data is True
        assert request.force_headful is True

    def test_tracking_code_trimmed(self):
        """Test that tracking code is trimmed of whitespace."""
        request = TopLogisticsCrawlRequest(tracking_code="  33EVH0319358  ")
        assert request.tracking_code == "33EVH0319358"

    def test_search_url_with_trimmed_s_parameter(self):
        """Test that s parameter is trimmed from search URL."""
        request = TopLogisticsCrawlRequest(
            tracking_code="https://toplogistics.com.au/?s=  33EVH0319358  "
        )
        assert request.tracking_code == "33EVH0319358"

    def test_missing_tracking_code(self):
        """Test that missing tracking code raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlRequest()
        assert "tracking_code" in str(exc_info.value)

    def test_empty_tracking_code(self):
        """Test that empty tracking code raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlRequest(tracking_code="")
        assert "tracking_code must be a non-empty string" in str(exc_info.value)

    def test_whitespace_only_tracking_code(self):
        """Test that whitespace-only tracking code raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlRequest(tracking_code="   ")
        assert "tracking_code must be a non-empty string" in str(exc_info.value)

    def test_url_without_s_parameter(self):
        """Test that URL without s parameter raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlRequest(tracking_code="https://toplogistics.com.au/")
        assert "could not extract 's' parameter" in str(exc_info.value)

    def test_url_with_empty_s_parameter(self):
        """Test that URL with empty s parameter raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlRequest(tracking_code="https://toplogistics.com.au/?s=")
        assert "could not extract 's' parameter" in str(exc_info.value)

    def test_url_with_whitespace_only_s_parameter(self):
        """Test that URL with whitespace-only s parameter raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlRequest(tracking_code="https://toplogistics.com.au/?s=   ")
        assert "could not extract 's' parameter" in str(exc_info.value)

    def test_defaults_when_not_provided(self):
        """Test that boolean fields default to False when not provided."""
        request = TopLogisticsCrawlRequest(tracking_code="33EVH0319358")
        assert request.force_user_data is False
        assert request.force_headful is False

    def test_explicit_false_values(self):
        """Test that explicitly setting False values works."""
        request = TopLogisticsCrawlRequest(
            tracking_code="33EVH0319358",
            force_user_data=False,
            force_headful=False
        )
        assert request.force_user_data is False
        assert request.force_headful is False

    def test_non_string_tracking_code(self):
        """Test that non-string tracking code raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlRequest(tracking_code=123456)
        error_str = str(exc_info.value)
        # Pydantic v2 gives different error message for non-string input
        assert ("tracking_code must be a non-empty string" in error_str or
                "Input should be a valid string" in error_str)

    def test_url_case_insensitive_s_parameter(self):
        """Test that s parameter extraction is case-sensitive (as per URL spec)."""
        # URL parameters are case-sensitive, so 'S' should not match 's'
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlRequest(tracking_code="https://toplogistics.com.au/?S=33EVH0319358")
        assert "could not extract 's' parameter" in str(exc_info.value)


class TestTopLogisticsCrawlResponse:
    """Test TopLogistics crawl response schema."""

    def test_success_response(self):
        """Test successful response creation."""
        response = TopLogisticsCrawlResponse(
            status="success",
            tracking_code="33EVH0319358",
            html="<html>TopLogistics tracking info</html>"
        )
        assert response.status == "success"
        assert response.tracking_code == "33EVH0319358"
        assert response.html == "<html>TopLogistics tracking info</html>"
        assert response.message is None

    def test_failure_response(self):
        """Test failure response creation."""
        response = TopLogisticsCrawlResponse(
            status="failure",
            tracking_code="33EVH0319358",
            message="HTTP status: 404"
        )
        assert response.status == "failure"
        assert response.tracking_code == "33EVH0319358"
        assert response.html is None
        assert response.message == "HTTP status: 404"

    def test_response_with_all_fields(self):
        """Test response with all fields populated."""
        response = TopLogisticsCrawlResponse(
            status="success",
            tracking_code="33EVH0319358",
            html="<html>TopLogistics tracking info</html>",
            message="Success message"
        )
        assert response.status == "success"
        assert response.tracking_code == "33EVH0319358"
        assert response.html == "<html>TopLogistics tracking info</html>"
        assert response.message == "Success message"

    def test_required_fields(self):
        """Test that status and tracking_code are required."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlResponse()
        error_msg = str(exc_info.value)
        assert "status" in error_msg
        assert "tracking_code" in error_msg

    def test_missing_status(self):
        """Test that missing status raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlResponse(tracking_code="33EVH0319358")
        assert "status" in str(exc_info.value)

    def test_missing_tracking_code(self):
        """Test that missing tracking_code raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TopLogisticsCrawlResponse(status="success")
        assert "tracking_code" in str(exc_info.value)
