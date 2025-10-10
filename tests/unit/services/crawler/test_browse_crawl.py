from app.schemas.crawl import CrawlRequest
from app.schemas.browse import BrowseRequest, BrowseResponse
from app.services.browser.browse import BrowseCrawler
import pytest
from unittest.mock import patch, MagicMock

pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_engine():
    """Mock CrawlerEngine for testing."""
    engine = MagicMock()
    engine.run.return_value = None  # Will be configured per test
    return engine


@pytest.fixture
def browse_crawler(mock_engine):
    """Fixture for BrowseCrawler with mocked engine."""
    return BrowseCrawler(engine=mock_engine)


def test_browse_request_conversion_with_url(browse_crawler):
    """Test conversion of browse request to crawl request with URL."""
    request = BrowseRequest(url="https://example.com")

    crawl_request = browse_crawler._convert_browse_to_crawl_request(request)

    assert isinstance(crawl_request, CrawlRequest)
    assert str(crawl_request.url) == "https://example.com/"
    assert crawl_request.force_headful is True
    assert crawl_request.force_user_data is True
    # Note: user_data_mode is not set on CrawlRequest - it's handled by user_data_context
    assert crawl_request.timeout_seconds is None


def test_browse_request_conversion_without_url(browse_crawler):
    """Test conversion of browse request to crawl request without URL."""
    request = BrowseRequest(url=None)

    crawl_request = browse_crawler._convert_browse_to_crawl_request(request)

    assert isinstance(crawl_request, CrawlRequest)
    assert str(crawl_request.url) == "about:blank"
    assert crawl_request.force_headful is True
    assert crawl_request.force_user_data is True
    # Note: user_data_mode is not set on CrawlRequest - it's handled by user_data_context
    assert crawl_request.timeout_seconds is None


def test_browse_success_path(browse_crawler, mock_engine):
    """Test successful browse session."""
    request = BrowseRequest(url="https://example.com")

    # Mock successful crawl response
    mock_crawl_response = MagicMock()
    mock_crawl_response.status = "success"
    mock_engine.run.return_value = mock_crawl_response

    with patch('app.services.browser.browse.user_data_context') as mock_context:
        mock_context.return_value.__enter__.return_value = ('/tmp/test_dir', lambda: None)

        result = browse_crawler.run(request)

        assert isinstance(result, BrowseResponse)
        assert result.status == "success"
        assert result.message == "Browser session completed successfully"

        # Verify engine was called with correct parameters
        mock_engine.run.assert_called_once()
        call_args = mock_engine.run.call_args
        crawl_req = call_args[0][0]  # First positional argument
        page_action = call_args[0][1]  # Second positional argument

        assert str(crawl_req.url) == "https://example.com/"
        assert crawl_req.force_headful is True
        assert crawl_req.force_user_data is True
        # Note: user_data_mode is not set on CrawlRequest - it's handled by user_data_context

        # Verify page action is WaitForUserCloseAction
        from app.services.browser.actions.wait_for_close import WaitForUserCloseAction
        assert isinstance(page_action, WaitForUserCloseAction)


def test_browse_engine_failure(browse_crawler, mock_engine):
    """Test browse session when engine fails."""
    request = BrowseRequest(url="https://example.com")

    # Mock engine to raise exception
    mock_engine.run.side_effect = Exception("Browser launch failed")

    with patch('app.services.browser.browse.user_data_context') as mock_context:
        mock_context.return_value.__enter__.return_value = ('/tmp/test_dir', lambda: None)

        result = browse_crawler.run(request)

        assert isinstance(result, BrowseResponse)
        assert result.status == "failure"
        assert "Browser launch failed" in result.message


def test_browse_user_data_context_failure(browse_crawler, mock_engine):
    """Test browse session when user data context fails."""
    request = BrowseRequest(url="https://example.com")

    with patch('app.services.browser.browse.user_data_context') as mock_context:
        mock_context.side_effect = RuntimeError("Lock acquisition failed")

        result = browse_crawler.run(request)

        assert isinstance(result, BrowseResponse)
        assert result.status == "failure"
        assert "Lock acquisition failed" in result.message

        # Engine should not be called if context fails
        mock_engine.run.assert_not_called()


def test_browse_cleanup_called(browse_crawler, mock_engine):
    """Test that cleanup function is called after browse session."""
    request = BrowseRequest(url="https://example.com")

    cleanup_called = False

    def mock_cleanup():
        nonlocal cleanup_called
        cleanup_called = True

    # Mock successful crawl response
    mock_crawl_response = MagicMock()
    mock_crawl_response.status = "success"
    mock_engine.run.return_value = mock_crawl_response

    with patch('app.services.browser.browse.user_data_context') as mock_context:
        mock_context.return_value.__enter__.return_value = ('/tmp/test_dir', mock_cleanup)

        result = browse_crawler.run(request)

        assert result.status == "success"
        assert cleanup_called is True
