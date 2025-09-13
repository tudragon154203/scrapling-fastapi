import pytest
from unittest.mock import MagicMock

from app.services.crawler.dpd import DPDCrawler
from app.schemas.dpd import DPDCrawlRequest


@pytest.fixture
def mock_engine():
    """Mock CrawlerEngine for testing."""
    engine = MagicMock()
    engine.run.return_value = None  # Will be configured per test
    return engine


@pytest.fixture
def dpd_crawler(mock_engine):
    """Fixture for DPDCrawler with mocked engine."""
    return DPDCrawler(engine=mock_engine)


def test_dpd_url_construction_correct_domain(dpd_crawler):
    """Verify the URL builder targets tracking.dpd.de and not any DHL domain."""
    request = DPDCrawlRequest(tracking_code="12345678901234")

    crawl_request = dpd_crawler._convert_dpd_to_crawl_request(request)

    # Check domain is correct
    assert "tracking.dpd.de" in str(crawl_request.url)
    assert "dhlparcel.nl" not in str(crawl_request.url)
    assert "status/en_US/parcel" in str(crawl_request.url)


def test_dpd_url_normalization_removes_spaces(dpd_crawler):
    """Confirm normalization removes spaces from tracking code."""
    request = DPDCrawlRequest(tracking_code="01126819 7878 09")

    crawl_request = dpd_crawler._convert_dpd_to_crawl_request(request)

    # Should be "01126819787809" without spaces
    expected_url = "https://tracking.dpd.de/status/en_US/parcel/01126819787809"
    assert str(crawl_request.url) == expected_url


def test_dpd_url_normalization_removes_hyphens(dpd_crawler):
    """Confirm normalization removes hyphens from tracking code."""
    request = DPDCrawlRequest(tracking_code="ABC-123-DEF-456")

    crawl_request = dpd_crawler._convert_dpd_to_crawl_request(request)

    # Should be "ABC123DEF456" without hyphens
    expected_url = "https://tracking.dpd.de/status/en_US/parcel/ABC123DEF456"
    assert str(crawl_request.url) == expected_url


def test_dpd_url_normalization_strips_whitespace(dpd_crawler):
    """Confirm normalization strips leading/trailing whitespace."""
    request = DPDCrawlRequest(tracking_code="  12345678901234  ")

    crawl_request = dpd_crawler._convert_dpd_to_crawl_request(request)

    # Should be trimmed to "12345678901234"
    expected_url = "https://tracking.dpd.de/status/en_US/parcel/12345678901234"
    assert str(crawl_request.url) == expected_url


def test_dpd_url_normalization_combines_all(dpd_crawler):
    """Test combined normalization: strip, remove spaces and hyphens."""
    request = DPDCrawlRequest(tracking_code="  ABC-123 DEF-456  ")

    crawl_request = dpd_crawler._convert_dpd_to_crawl_request(request)

    # Should be "ABC123DEF456" - stripped, spaces removed, hyphens removed
    expected_url = "https://tracking.dpd.de/status/en_US/parcel/ABC123DEF456"
    assert str(crawl_request.url) == expected_url


def test_dpd_url_normalization_url_encoding(dpd_crawler):
    """Test URL encoding for non-alphanumeric characters."""
    request = DPDCrawlRequest(tracking_code="ABC#123@DEF$456")

    crawl_request = dpd_crawler._convert_dpd_to_crawl_request(request)

    # Special chars should be URL-encoded: # -> %23, @ -> %40, $ -> %24
    expected_url = "https://tracking.dpd.de/status/en_US/parcel/ABC%23123%40DEF%24456"
    assert str(crawl_request.url) == expected_url


def test_dpd_success_path_returns_html(dpd_crawler, mock_engine):
    """Success path: mocked 200 + sufficient HTML length => status=success with html."""
    request = DPDCrawlRequest(tracking_code="12345678901234")

    # Mock engine to return success with HTML
    mock_response = MagicMock()
    mock_response.status = "success"
    mock_response.html = "<html>tracking results</html>"
    mock_response.message = None
    mock_engine.run.return_value = mock_response

    result = dpd_crawler.run(request)

    assert result.status == "success"
    assert result.tracking_code == "12345678901234"
    assert result.html == "<html>tracking results</html>"
    assert result.message is None


def test_dpd_failure_path_non_200(dpd_crawler, mock_engine):
    """Failure path: non-200 status => status=failure with message."""
    request = DPDCrawlRequest(tracking_code="12345678901234")

    # Mock engine to return failure with message
    mock_response = MagicMock()
    mock_response.status = "failure"
    mock_response.html = None
    mock_response.message = "HTTP status: 404"
    mock_engine.run.return_value = mock_response

    result = dpd_crawler.run(request)

    assert result.status == "failure"
    assert result.tracking_code == "12345678901234"
    assert result.html is None
    assert result.message == "HTTP status: 404"


def test_dpd_failure_path_short_html(dpd_crawler, mock_engine):
    """Failure path: short HTML content => status=failure with message.

    The short-HTML validation is enforced by the executor. Simulate that behavior by
    returning a failure response from the engine with the appropriate message.
    """
    request = DPDCrawlRequest(tracking_code="12345678901234")

    # Engine returns failure due to short HTML (as enforced in executors)
    mock_response = MagicMock()
    mock_response.status = "failure"
    mock_response.html = None
    mock_response.message = "HTML too short (<500 chars); suspected bot detection"
    mock_engine.run.return_value = mock_response

    result = dpd_crawler.run(request)

    assert result.status == "failure"
    assert result.message is not None
    assert ("short" in result.message.lower()) or ("insufficient" in result.message.lower())
