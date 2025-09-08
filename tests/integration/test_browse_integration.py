import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient
import time

from app.main import app
from app.core.config import Settings


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def temp_user_data_dir():
    """Create a temporary user data directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_browse_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def existing_user_data_dir(temp_user_data_dir):
    """Create a temporary user data directory with existing data."""
    # Create some fake user data files
    profiles_dir = Path(temp_user_data_dir) / "default"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    
    # Create some fake user data files to simulate existing profile
    (profiles_dir / "places.sqlite").touch()
    (profiles_dir / "cookies.sqlite").touch()
    (profiles_dir / "webappsstore.sqlite").touch()
    
    return temp_user_data_dir


class TestBrowseE2E:
    """End-to-end tests for browse endpoint with user data directory loading and saving."""

    def test_browse_with_existing_user_data_loading(self, monkeypatch, client, existing_user_data_dir):
        """Test that user data directory is loaded successfully on browser open.
        
        This test verifies that when a browse session starts with existing user data,
        the user data context is properly loaded and the directory is accessible.
        """
        from app.schemas.browse import BrowseResponse
        from app.services.crawler.browse import BrowseCrawler
        
        captured_load_calls = []
        captured_directories = []
        
        # Mock user data context to capture loading behavior
        def mock_user_data_context(user_data_dir, mode):
            captured_load_calls.append(mode)
            captured_directories.append(user_data_dir)
            
            # Create the context manager that returns our existing user data dir
            class MockContext:
                def __enter__(self):
                    return (str(Path(user_data_dir) / 'master'), lambda: None)
                def __exit__(self, *args):
                    pass
            
            return MockContext()
        
        # Mock settings to use our temp directory
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = existing_user_data_dir
        
        # Mock browser engine to simulate successful execution
        mock_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.status = "success"
        mock_engine.run.return_value = mock_response
        
        # Patch imports
        with patch('app.services.crawler.browse.CrawlerEngine') as mock_engine_class, \
             patch('app.services.crawler.browse.app_config.get_settings', return_value=mock_settings):
            mock_engine_class.from_settings.return_value = mock_engine
            with patch('app.services.crawler.browse.user_data_context', side_effect=mock_user_data_context):
                
                # Test the browse endpoint
                body = {"url": "https://example.com"}
                resp = client.post("/browse", json=body)
                
                # Verify response
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert data["message"] == "Browser session completed successfully"
                
                # Verify user data context was called with write mode
                assert len(captured_load_calls) == 1
                assert captured_load_calls[0] == "write"
                
                # Verify correct user data directory was used
                assert len(captured_directories) == 1
                assert captured_directories[0] == existing_user_data_dir
                
                # Verify engine was called with correct parameters
                mock_engine.run.assert_called_once()
                call_args = mock_engine.run.call_args
                crawl_req = call_args[0][0]  # First positional argument
                
                # Verify crawl request has user data settings
                assert crawl_req.force_user_data is True
                assert crawl_req.user_data_mode == "write"

    def test_browse_user_data_directory_creation(self, monkeypatch, client, temp_user_data_dir):
        """Test that user data directory is properly created if it doesn't exist.
        
        This test verifies that even with a non-existent user data directory,
        the browse session can create and use it.
        """
        # Capture directory operations
        created_directories = []
        
        def mock_user_data_context(user_data_dir, mode):
            # Capture the directory being used
            created_directories.append(user_data_dir)
            
            # The actual user_data_context will create the master directory
            master_dir = Path(user_data_dir) / 'master'
            master_dir.mkdir(parents=True, exist_ok=True)
            
            class MockContext:
                def __enter__(self):
                    return (str(master_dir), lambda: None)
                def __exit__(self, *args):
                    pass
            return MockContext()
        
        # Mock settings to use our temp directory
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = temp_user_data_dir
        
        # Mock browser engine
        mock_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.status = "success"
        mock_engine.run.return_value = mock_response
        
        with patch('app.services.crawler.browse.CrawlerEngine') as mock_engine_class, \
             patch('app.services.crawler.browse.app_config.get_settings', return_value=mock_settings):
            mock_engine_class.from_settings.return_value = mock_engine
            with patch('app.services.crawler.browse.user_data_context', side_effect=mock_user_data_context):
                
                # Test browse endpoint
                body = {"url": "https://example.com"}
                resp = client.post("/browse", json=body)
                
                # Verify success
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                
                # Verify directory was created and used
                assert len(created_directories) == 1
                assert created_directories[0] == temp_user_data_dir
                
                # Verify the master directory was created
                master_dir = Path(temp_user_data_dir) / 'master'
                assert master_dir.exists()
                assert master_dir.is_dir()

    def test_browse_user_data_cleanup_on_close(self, monkeypatch, client, temp_user_data_dir):
        """Test that user data cleanup is properly executed after browser close.
        
        This test verifies that the cleanup function is called when the browser session ends,
        ensuring proper resource cleanup.
        """
        cleanup_calls = []
        
        def mock_cleanup():
            cleanup_calls.append("cleanup_called")
        
        def mock_user_data_context(user_data_dir, mode):
            class MockContext:
                def __enter__(self):
                    master_dir = Path(user_data_dir) / 'master'
                    return (str(master_dir), mock_cleanup)
                def __exit__(self, *args):
                    pass
            return MockContext()
        
        # Mock browser engine
        mock_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.status = "success"
        mock_engine.run.return_value = mock_response
        
        with patch('app.services.crawler.browse.CrawlerEngine') as mock_engine_class, \
             patch('app.services.crawler.browse.app_config.get_settings', return_value=Settings()):
            mock_engine_class.from_settings.return_value = mock_engine
            with patch('app.services.crawler.browse.user_data_context', side_effect=mock_user_data_context):
                
                # Test browse endpoint
                body = {"url": "https://example.com"}
                resp = client.post("/browse", json=body)
                
                # Verify success
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                
                # Verify cleanup was called
                assert len(cleanup_calls) == 1
                assert cleanup_calls[0] == "cleanup_called"

    def test_browse_user_data_write_mode_enforcement(self, monkeypatch, client, existing_user_data_dir):
        """Test that browse endpoint always enforces write mode for user data.
        
        This test verifies that regardless of the browse session details,
        the user data mode is always set to 'write' to allow data persistence.
        """
        captured_requests = []
        
        def mock_user_data_context(user_data_dir, mode):
            class MockContext:
                def __enter__(self):
                    master_dir = Path(user_data_dir) / 'master'
                    return (str(master_dir), lambda: None)
                def __exit__(self, *args):
                    pass
            return MockContext()
        
        # Mock settings
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = existing_user_data_dir
        
        # Mock engine to capture crawl request
        mock_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.status = "success"
        mock_engine.run.return_value = mock_response
        
        def capture_engine_run(crawl_request, page_action):
            captured_requests.append(crawl_request)
            return mock_response
        
        with patch('app.services.crawler.browse.CrawlerEngine') as mock_engine_class, \
             patch('app.services.crawler.browse.app_config.get_settings', return_value=mock_settings):
            mock_engine_class.from_settings.return_value = mock_engine
            mock_engine.run.side_effect = capture_engine_run
            with patch('app.services.crawler.browse.user_data_context', side_effect=mock_user_data_context):
                
                # Test with different URLs to ensure consistent behavior
                test_urls = [None, "https://example.com", "https://google.com"]
                
                for url in test_urls:
                    captured_requests.clear()
                    
                    if url:
                        body = {"url": url}
                    else:
                        body = {}
                    
                    resp = client.post("/browse", json=body)
                    assert resp.status_code == 200
                    
                    # Verify all captured requests have correct user data settings
                    for request in captured_requests:
                        assert request.force_user_data is True
                        assert request.user_data_mode == "write"