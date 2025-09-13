from unittest.mock import MagicMock, patch

from app.services.browser.browse import BrowseCrawler
from app.services.browser.executors.browse_executor import BrowseExecutor


def test_browse_crawler_uses_browse_executor():
    """Test that BrowseCrawler uses BrowseExecutor instead of default retry executor."""
    # Mock dependencies
    with patch('app.services.browser.browse.BrowseExecutor') as mock_browse_executor, \
         patch('app.services.browser.browse.CrawlerEngine') as mock_engine_class:
        
        mock_browse_instance = MagicMock()
        mock_browse_executor.return_value = mock_browse_instance
        mock_engine_instance = MagicMock()
        mock_engine_class.return_value = mock_engine_instance
        
        # Create BrowseCrawler to trigger constructor wiring
        _ = BrowseCrawler()
        
        # Verify BrowseExecutor was created
        mock_browse_executor.assert_called_once()
        
        # Verify CrawlerEngine was created with BrowseExecutor
        mock_engine_class.assert_called_once_with(
            executor=mock_browse_instance,
            fetch_client=mock_browse_instance.fetch_client,
            options_resolver=mock_browse_instance.options_resolver,
            camoufox_builder=mock_browse_instance.camoufox_builder
        )


def test_browse_executor_never_retries():
    """Test that BrowseExecutor respects user close actions and never retries."""
    from app.schemas.crawl import CrawlRequest
    
    # Create browse executor
    executor = BrowseExecutor()
    
    # Test that should_retry returns False for any response
    test_request = CrawlRequest(url="https://example.com")
    
    # Create a mock response that would normally trigger retry
    mock_response = MagicMock()
    mock_response.status = "failure"
    mock_response.url = test_request.url
    
    # Browse executor should never retry
    assert executor.should_retry(mock_response) is False
    
    # Test retry delay is zero
    delay = executor.get_retry_delay(mock_response, 1)
    assert delay == 0.0


def test_browse_executor_handles_browser_close_as_success():
    """Test that BrowseExecutor treats user browser close as successful completion."""
    from app.schemas.crawl import CrawlRequest
    
    executor = BrowseExecutor()
    
    # Create a mock request
    request = CrawlRequest(url="https://example.com")
    
    # Mock the fetch client to simulate user closing browser
    with patch.object(executor.options_resolver, 'resolve') as mock_resolve, \
         patch.object(executor.camoufox_builder, 'build') as mock_build, \
         patch.object(executor.fetch_client, 'detect_capabilities') as mock_caps:
        
        mock_resolve.return_value = {}
        mock_build.return_value = {}, {}
        mock_caps.return_value = MagicMock()
        
        with patch.object(executor.arg_composer, 'compose') as mock_compose, \
             patch.object(executor.fetch_client, 'fetch') as mock_fetch:
            mock_compose.return_value = {}
            # Simulate TargetClosedError (common when user closes browser)
            mock_fetch.side_effect = Exception("TargetClosedError: Browser was closed by user")
            
            # Execute browse request
            result = executor.execute(request)
            
            # Should be considered success because user closed browser
            assert result.status == "success"
            assert result.url == request.url
            assert "user closed" in result.message.lower()


def test_browse_executor_handles_other_errors_as_failure():
    """Test that BrowseExecutor treats non-browser-close errors as failures."""
    from app.schemas.crawl import CrawlRequest
    
    executor = BrowseExecutor()
    
    # Create a mock request
    request = CrawlRequest(url="https://example.com")
    
    # Simulate a network error via fetch_client.fetch
    with patch.object(executor.options_resolver, 'resolve') as mock_resolve, \
         patch.object(executor.camoufox_builder, 'build') as mock_build, \
         patch.object(executor.fetch_client, 'detect_capabilities') as mock_caps, \
         patch.object(executor.arg_composer, 'compose') as mock_compose, \
         patch.object(executor.fetch_client, 'fetch') as mock_fetch:
        
        mock_resolve.return_value = {}
        mock_build.return_value = {}, {}
        mock_caps.return_value = MagicMock()
        mock_compose.return_value = {}
        # Simulate network error (not a browser close)
        mock_fetch.side_effect = Exception("NetworkError: Connection failed")
        
        # Execute browse request
        result = executor.execute(request)
        
        # Should be considered failure
        assert result.status == "failure"
        assert result.url == request.url
        assert "NetworkError" in result.message


def test_browse_executor_sets_long_timeout():
    """Test that BrowseExecutor sets appropriate timeout for interactive sessions."""
    from app.schemas.crawl import CrawlRequest
    
    executor = BrowseExecutor()
    request = CrawlRequest(url="https://example.com")
    
    with patch.object(executor.options_resolver, 'resolve') as mock_resolve, \
         patch.object(executor.camoufox_builder, 'build') as mock_build, \
         patch.object(executor.fetch_client, 'detect_capabilities') as mock_caps, \
         patch.object(executor.arg_composer, 'compose') as mock_compose, \
         patch.object(executor.fetch_client, 'fetch') as mock_fetch:
        
        mock_resolve.return_value = {}
        mock_build.return_value = {}, {}
        mock_caps.return_value = MagicMock()
        # Compose returns a base timeout
        mock_compose.return_value = {
            'timeout': 10000,  # Base timeout
            '_user_data_cleanup': lambda: None
        }
        mock_fetch.return_value = MagicMock()
        
        # Execute browse request
        _ = executor.execute(request)
        
        # Inspect the actual fetch kwargs sent to fetch_client.fetch
        assert mock_fetch.call_count == 1
        fetch_args, fetch_kwargs = mock_fetch.call_args
        # First positional arg is URL, second is kwargs dict
        assert isinstance(fetch_args[1], dict)
        effective_kwargs = fetch_args[1]
        
        # Should have longer timeout than base
        assert 'timeout' in effective_kwargs
        assert effective_kwargs['timeout'] > 10000


def test_browse_crawler_with_custom_engine():
    """Test that BrowseCrawler can accept a custom engine."""
    custom_engine = MagicMock()
    
    # Create BrowseCrawler with custom engine
    crawler = BrowseCrawler(engine=custom_engine)
    
    # Should use the provided custom engine
    assert crawler.engine is custom_engine
