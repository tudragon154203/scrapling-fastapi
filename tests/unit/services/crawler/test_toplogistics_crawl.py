from app.schemas.toplogistics import TopLogisticsCrawlRequest
from app.services.crawler.toplogistics import TopLogisticsCrawler, extract_tracking_code, build_tracking_url
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_engine():
    """Mock CrawlerEngine for testing."""
    engine = MagicMock()
    engine.run.return_value = None  # Will be configured per test
    return engine


@pytest.fixture
def toplogistics_crawler(mock_engine):
    """Fixture for TopLogisticsCrawler with mocked engine."""
    return TopLogisticsCrawler(engine=mock_engine)


class TestExtractTrackingCode:
    """Test extract_tracking_code helper function."""

    def test_bare_tracking_code(self):
        """Test extraction of bare tracking code."""
        result = extract_tracking_code("33EVH0319358")
        assert result == "33EVH0319358"

    def test_tracking_code_with_whitespace(self):
        """Test extraction with whitespace trimming."""
        result = extract_tracking_code("  33EVH0319358  ")
        assert result == "33EVH0319358"

    def test_search_url_https(self):
        """Test extraction from HTTPS search URL."""
        result = extract_tracking_code("https://toplogistics.com.au/?s=33EVH0319358")
        assert result == "33EVH0319358"

    def test_search_url_http(self):
        """Test extraction from HTTP search URL."""
        result = extract_tracking_code("http://toplogistics.com.au/?s=33EVH0319358")
        assert result == "33EVH0319358"

    def test_search_url_with_multiple_params(self):
        """Test extraction from URL with multiple parameters."""
        result = extract_tracking_code("https://toplogistics.com.au/?s=33EVH0319358&other=value&more=data")
        assert result == "33EVH0319358"

    def test_search_url_with_whitespace_in_s_param(self):
        """Test extraction with whitespace in s parameter."""
        result = extract_tracking_code("https://toplogistics.com.au/?s=  33EVH0319358  ")
        assert result == "33EVH0319358"

    def test_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_tracking_code("")
        assert "non-empty string" in str(exc_info.value)

    def test_whitespace_only_string(self):
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_tracking_code("   ")
        assert "non-empty string" in str(exc_info.value)

    def test_non_string_input(self):
        """Test that non-string input raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_tracking_code(123456)
        assert "non-empty string" in str(exc_info.value)

    def test_url_without_s_parameter(self):
        """Test that URL without s parameter raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_tracking_code("https://toplogistics.com.au/")
        assert "could not extract 's' parameter" in str(exc_info.value)

    def test_url_with_empty_s_parameter(self):
        """Test that URL with empty s parameter raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_tracking_code("https://toplogistics.com.au/?s=")
        assert "could not extract 's' parameter" in str(exc_info.value)


class TestBuildTrackingUrl:
    """Test build_tracking_url helper function."""

    def test_basic_tracking_url(self):
        """Test basic tracking URL construction."""
        url = build_tracking_url("33EVH0319358")
        assert url == "https://imshk.toplogistics.com.au/customerService/imparcelTracking?s=33EVH0319358"

    def test_tracking_url_with_whitespace(self):
        """Test URL construction with whitespace trimming."""
        url = build_tracking_url("  33EVH0319358  ")
        assert url == "https://imshk.toplogistics.com.au/customerService/imparcelTracking?s=33EVH0319358"

    def test_tracking_url_with_special_chars(self):
        """Test URL encoding for special characters."""
        url = build_tracking_url("ABC#123@DEF$456")
        assert url == "https://imshk.toplogistics.com.au/customerService/imparcelTracking?s=ABC%23123%40DEF%24456"

    def test_tracking_url_with_spaces(self):
        """Test URL encoding for spaces."""
        url = build_tracking_url("33EVH 0319 358")
        assert url == "https://imshk.toplogistics.com.au/customerService/imparcelTracking?s=33EVH%200319%20358"


class TestTopLogisticsCrawler:
    """Test TopLogisticsCrawler class."""

    def test_url_construction_correct_domain(self, toplogistics_crawler):
        """Verify URL builder targets imshk.toplogistics.com.au domain."""
        request = TopLogisticsCrawlRequest(tracking_code="33EVH0319358")

        crawl_request = toplogistics_crawler._convert_toplogistics_to_crawl_request(request)

        # Check domain is correct
        assert "imshk.toplogistics.com.au" in str(crawl_request.url)
        assert "customerService/imparcelTracking" in str(crawl_request.url)
        assert "s=33EVH0319358" in str(crawl_request.url)

    def test_request_configuration_defaults(self, toplogistics_crawler):
        """Test default request configuration."""
        request = TopLogisticsCrawlRequest(tracking_code="33EVH0319358")

        crawl_request = toplogistics_crawler._convert_toplogistics_to_crawl_request(request)

        assert crawl_request.network_idle is True
        assert crawl_request.timeout_seconds == 25
        assert crawl_request.force_headful is False
        assert crawl_request.force_user_data is False
        assert "User-Agent" in crawl_request.headers

    def test_request_configuration_with_flags(self, toplogistics_crawler):
        """Test request configuration with force flags."""
        request = TopLogisticsCrawlRequest(
            tracking_code="33EVH0319358",
            force_user_data=True,
            force_headful=True
        )

        crawl_request = toplogistics_crawler._convert_toplogistics_to_crawl_request(request)

        assert crawl_request.force_headful is True
        assert crawl_request.force_user_data is True
        assert crawl_request.network_idle is True
        assert crawl_request.timeout_seconds == 25

    def test_user_agent_header(self, toplogistics_crawler):
        """Test that User-Agent header is set correctly."""
        request = TopLogisticsCrawlRequest(tracking_code="33EVH0319358")

        crawl_request = toplogistics_crawler._convert_toplogistics_to_crawl_request(request)

        assert "User-Agent" in crawl_request.headers
        assert "Mozilla/5.0" in crawl_request.headers["User-Agent"]
        assert "Chrome/120.0.0.0" in crawl_request.headers["User-Agent"]

    def test_success_path_returns_html(self, toplogistics_crawler, mock_engine):
        """Success path: mocked 200 + sufficient HTML => status=success with html."""
        request = TopLogisticsCrawlRequest(tracking_code="33EVH0319358")

        # Mock engine to return success with HTML
        mock_response = MagicMock()
        mock_response.status = "success"
        mock_response.html = "<html>TopLogistics tracking results</html>"
        mock_response.message = None
        mock_engine.run.return_value = mock_response

        result = toplogistics_crawler.run(request)

        assert result.status == "success"
        assert result.tracking_code == "33EVH0319358"
        assert result.html == "<html>TopLogistics tracking results</html>"
        assert result.message is None

    def test_failure_path_non_200(self, toplogistics_crawler, mock_engine):
        """Failure path: non-200 status => status=failure with message."""
        request = TopLogisticsCrawlRequest(tracking_code="33EVH0319358")

        # Mock engine to return failure with message
        mock_response = MagicMock()
        mock_response.status = "failure"
        mock_response.html = None
        mock_response.message = "HTTP status: 404"
        mock_engine.run.return_value = mock_response

        result = toplogistics_crawler.run(request)

        assert result.status == "failure"
        assert result.tracking_code == "33EVH0319358"
        assert result.html is None
        assert result.message == "HTTP status: 404"

    def test_failure_path_short_html(self, toplogistics_crawler, mock_engine):
        """Failure path: short HTML content => status=failure with message."""
        request = TopLogisticsCrawlRequest(tracking_code="33EVH0319358")

        # Engine returns failure due to short HTML (as enforced in executors)
        mock_response = MagicMock()
        mock_response.status = "failure"
        mock_response.html = None
        mock_response.message = "HTML too short (<500 chars); suspected bot detection"
        mock_engine.run.return_value = mock_response

        result = toplogistics_crawler.run(request)

        assert result.status == "failure"
        assert result.tracking_code == "33EVH0319358"
        assert result.html is None
        assert result.message == "HTML too short (<500 chars); suspected bot detection"

    def test_error_status_normalized_to_failure(self, toplogistics_crawler, mock_engine):
        """Test that 'error' status from engine is normalized to 'failure'."""
        request = TopLogisticsCrawlRequest(tracking_code="33EVH0319358")

        # Mock engine to return 'error' status
        mock_response = MagicMock()
        mock_response.status = "error"
        mock_response.html = None
        mock_response.message = "Connection timeout"
        mock_engine.run.return_value = mock_response

        result = toplogistics_crawler.run(request)

        # Should normalize 'error' to 'failure'
        assert result.status == "failure"
        assert result.tracking_code == "33EVH0319358"
        assert result.message == "Connection timeout"

    def test_engine_called_with_correct_parameters(self, toplogistics_crawler, mock_engine):
        """Test that engine.run is called with correct CrawlRequest."""
        request = TopLogisticsCrawlRequest(
            tracking_code="33EVH0319358",
            force_user_data=True,
            force_headful=True
        )

        mock_response = MagicMock()
        mock_response.status = "success"
        mock_response.html = "<html>content</html>"
        mock_response.message = None
        mock_engine.run.return_value = mock_response

        toplogistics_crawler.run(request)

        # Verify engine.run was called once
        mock_engine.run.assert_called_once()

        # Get the CrawlRequest that was passed to engine.run
        call_args = mock_engine.run.call_args[0][0]
        assert "imshk.toplogistics.com.au" in str(call_args.url)
        assert "s=33EVH0319358" in str(call_args.url)
        assert call_args.network_idle is True
        assert call_args.timeout_seconds == 25
        assert call_args.force_headful is True
        assert call_args.force_user_data is True
        assert "User-Agent" in call_args.headers
