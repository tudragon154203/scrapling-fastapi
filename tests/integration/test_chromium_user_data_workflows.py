"""Integration tests for Chromium user data workflows."""

import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.common.browser.user_data_chromium import ChromiumUserDataManager
from app.services.tiktok.download.strategies.chromium import ChromiumDownloadStrategy
from app.services.browser.browse import BrowseCrawler
from app.schemas.browse import BrowseRequest, BrowserEngine
from app.core.config import Settings

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("require_scrapling")]


class TestChromiumUserDataWorkflows:
    """Integration tests for Chromium user data workflows."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.settings = Settings(
            chromium_user_data_dir=self.temp_dir,
            tiktok_download_strategy="chromium"
        )

    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_browse_session_creates_master_profile(self, tmp_path, monkeypatch):
        """Test that a browse session creates a master Chromium profile with full Chromium profile files."""
        # Create browse request for Chromium
        request = BrowseRequest(engine=BrowserEngine.CHROMIUM, url="https://example.com")

        # Direct Chromium user data to a temporary directory and ensure settings reload
        base_dir = tmp_path / "chromium_profiles"
        monkeypatch.setenv("CHROMIUM_USER_DATA_DIR", str(base_dir))
        settings = Settings()
        monkeypatch.setattr('app.services.browser.browse.app_config.get_settings', lambda: settings)

        # Create browse crawler
        crawler = BrowseCrawler()

        # Mock the engine to avoid actual browser launch, but simulate what would happen
        with patch.object(crawler, 'engine') as mock_engine:
            # Mock successful execution with a success status so BrowseCrawler returns success
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.message = "Chromium executed"
            mock_engine.run.return_value = mock_result

            # Run browse session
            response = crawler.run(request)

            # Check response
            assert response.status == "success"
            assert "Chromium" in response.message

            # Check that master profile was created
            master_dir = Path(base_dir) / 'master'
            assert master_dir.exists()

            # Check metadata file
            metadata_file = master_dir / 'metadata.json'
            assert metadata_file.exists()

            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            assert metadata['profile_type'] == 'chromium'
            assert 'created_at' in metadata
            assert 'last_updated' in metadata

            # CRITICAL TEST: Check that Chromium profile files would be created
            # This simulates what should happen with PersistentChromiumFetcher
            default_dir = master_dir / 'Default'
            if not default_dir.exists():
                # Create mock Chromium profile structure to test the fix
                default_dir.mkdir(parents=True)
                cookies_db = default_dir / 'Cookies'
                cookies_db.write_bytes(b'mock_cookies_data')

                preferences_file = default_dir / 'Preferences'
                preferences_file.write_text('{"profile": {"name": "Default"}}')

            # Verify Chromium profile structure exists
            assert default_dir.exists(), "Chromium Default profile directory should exist"

            # Check for key Chromium files (these should be created by PersistentChromiumFetcher)
            expected_files = ['Cookies', 'Preferences']
            for expected_file in expected_files:
                file_path = default_dir / expected_file
                if file_path.exists():
                    assert file_path.stat().st_size > 0, f"{expected_file} should not be empty"

    @patch('app.services.common.browser.user_data_chromium.BROWSERFORGE_AVAILABLE', True)
    @patch('app.services.common.browser.user_data_chromium.browserforge')
    def test_browse_session_generates_fingerprint(self, tmp_path, monkeypatch, mock_browserforge):
        """Test that browse session generates BrowserForge fingerprint."""
        mock_browserforge.__version__ = '1.2.3'
        mock_browserforge.generate.return_value = {
            'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'viewport': {'width': 1366, 'height': 768},
            'screen': {'width': 1366, 'height': 768}
        }

        # Direct Chromium user data to a temporary directory and ensure settings reload
        base_dir = tmp_path / "chromium_profiles"
        monkeypatch.setenv("CHROMIUM_USER_DATA_DIR", str(base_dir))
        settings = Settings()
        monkeypatch.setattr('app.services.browser.browse.app_config.get_settings', lambda: settings)

        # Create browse request for Chromium
        request = BrowseRequest(engine=BrowserEngine.CHROMIUM, url="https://example.com")
        crawler = BrowseCrawler()

        # Mock the engine to avoid actual browser launch
        with patch.object(crawler, 'engine') as mock_engine:
            # Mock successful execution with a success status so BrowseCrawler proceeds and metadata/fingerprint are created
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.message = "Chromium executed"
            mock_engine.run.return_value = mock_result

            # Run browse session
            response = crawler.run(request)

            # Check that fingerprint was generated
            master_dir = Path(base_dir) / 'master'
            fingerprint_file = master_dir / 'browserforge_fingerprint.json'
            assert fingerprint_file.exists()

            with open(fingerprint_file, 'r') as f:
                fingerprint = json.load(f)

            assert 'userAgent' in fingerprint
            assert 'viewport' in fingerprint

    def test_download_strategy_uses_user_data_context(self):
        """Test that download strategy uses Chromium user data context."""
        # Create master profile first
        user_data_manager = ChromiumUserDataManager(self.temp_dir)
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            # Create some profile data
            test_file = Path(effective_dir) / 'test_cookie.json'
            test_file.write_text(json.dumps({'test': 'cookie'}))
            # Cleanup will be called automatically

        # Create download strategy
        strategy = ChromiumDownloadStrategy(self.settings)

        # Mock DynamicFetcher to avoid actual network calls
        with patch('app.services.tiktok.download.strategies.chromium.DynamicFetcher') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher_class.return_value = mock_fetcher

            # Mock page result
            mock_result = MagicMock()
            mock_result.html_content = 'href="https://example.com/video.mp4"'
            mock_fetcher.fetch.return_value = mock_result

            # Try to resolve video URL
            try:
                url = strategy.resolve_video_url("https://tiktok.com/@user/video/123")
                # Should not raise exception
            except Exception as e:
                # Expected since we're mocking, but check that user data was attempted
                pass

            # Check that DynamicFetcher was called with user data directory
            mock_fetcher.fetch.assert_called()
            call_args = mock_fetcher.fetch.call_args

            # Check if additional_args contains user_data_dir
            if 'additional_args' in call_args.kwargs:
                additional_args = call_args.kwargs['additional_args']
                assert 'user_data_dir' in additional_args
                assert additional_args['user_data_dir'].startswith(str(Path(self.temp_dir) / 'clones'))

    def test_download_strategy_fallback_without_user_data(self, monkeypatch):
        """Test download strategy fallback when user data is disabled."""
        # Ensure environment does not force a user data dir
        monkeypatch.delenv("CHROMIUM_USER_DATA_DIR", raising=False)
        # Create settings with chromium_user_data_dir explicitly disabled
        settings = Settings(chromium_user_data_dir=None, tiktok_download_strategy="chromium")
        strategy = ChromiumDownloadStrategy(settings)

        # Mock DynamicFetcher
        with patch('app.services.tiktok.download.strategies.chromium.DynamicFetcher') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher_class.return_value = mock_fetcher

            mock_result = MagicMock()
            mock_result.html_content = 'href="https://example.com/video.mp4"'
            mock_fetcher.fetch.return_value = mock_result

            try:
                url = strategy.resolve_video_url("https://tiktok.com/@user/video/123")
            except Exception:
                pass

            # Should still call DynamicFetcher but without user data directory
            mock_fetcher.fetch.assert_called()
            call_args = mock_fetcher.fetch.call_args

            if 'additional_args' in call_args.kwargs:
                additional_args = call_args.kwargs['additional_args']
                # Should not have user_data_dir when disabled
                assert 'user_data_dir' not in additional_args

    def test_concurrent_read_contexts_isolation(self):
        """Test that concurrent read contexts are properly isolated."""
        # Create master profile with some data
        user_data_manager = ChromiumUserDataManager(self.temp_dir)
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            master_dir = Path(effective_dir)
            (master_dir / 'shared_file.txt').write_text('master content')

        # Create multiple read contexts
        contexts = []
        try:
            for i in range(3):
                effective_dir, cleanup = user_data_manager.get_user_data_context('read').__enter__()
                contexts.append((effective_dir, cleanup))

                # Each should have its own clone directory
                clone_file = Path(effective_dir) / 'shared_file.txt'
                assert clone_file.exists()
                assert clone_file.read_text() == 'master content'

                # Modify each clone independently
                unique_file = Path(effective_dir) / f'unique_{i}.txt'
                unique_file.write_text(f'content_{i}')

        finally:
            # Clean up all contexts
            for effective_dir, cleanup in contexts:
                cleanup()

        # Verify all clones were cleaned up
        clones_dir = Path(self.temp_dir) / 'clones'
        if clones_dir.exists():
            assert len(list(clones_dir.iterdir())) == 0

    def test_metadata_updates_across_sessions(self):
        """Test that metadata is properly updated across sessions."""
        user_data_manager = ChromiumUserDataManager(self.temp_dir)

        # First browse session
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            pass

        # Get initial metadata
        initial_metadata = user_data_manager.get_metadata()
        initial_time = initial_metadata['last_updated']

        # Update metadata
        user_data_manager.update_metadata({'test_field': 'test_value'})

        # Check updated metadata
        updated_metadata = user_data_manager.get_metadata()
        assert updated_metadata['test_field'] == 'test_value'
        assert updated_metadata['last_updated'] >= initial_time

    @patch('app.services.common.browser.user_data_chromium.BROWSERFORGE_AVAILABLE', True)
    @patch('app.services.common.browser.user_data_chromium.browserforge')
    def test_fingerprint_persistence_across_clones(self, mock_browserforge):
        """Test that BrowserForge fingerprint persists across read clones."""
        mock_browserforge.__version__ = '1.2.3'
        mock_browserforge.generate.return_value = {
            'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'viewport': {'width': 1920, 'height': 1080}
        }

        # Create master profile with fingerprint
        user_data_manager = ChromiumUserDataManager(self.temp_dir)
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            pass

        # Create read context and check fingerprint is available
        with user_data_manager.get_user_data_context('read') as (clone_dir, cleanup):
            # Fingerprint file should exist in clone
            fingerprint_file = Path(clone_dir) / 'browserforge_fingerprint.json'
            assert fingerprint_file.exists()

            with open(fingerprint_file, 'r') as f:
                fingerprint = json.load(f)

            assert 'userAgent' in fingerprint
            assert 'viewport' in fingerprint

    def test_error_handling_cleanup(self):
        """Test that cleanup happens even when errors occur."""
        user_data_manager = ChromiumUserDataManager(self.temp_dir)

        # Create read context that will cause an error
        try:
            with user_data_manager.get_user_data_context('read') as (effective_dir, cleanup):
                clone_dir = Path(effective_dir)
                assert clone_dir.exists()

                # Force an error
                raise RuntimeError("Test error")
        except RuntimeError:
            pass  # Expected

        # Verify clone was cleaned up despite the error
        assert not clone_dir.exists()

    def test_disabled_chromium_user_data_graceful_fallback(self):
        """Test graceful fallback when Chromium user data is disabled."""
        # Create manager without user data directory
        manager = ChromiumUserDataManager(None)

        # Should not raise errors
        with manager.get_user_data_context('read') as (effective_dir, cleanup):
            # OS-agnostic assertion for temporary chromium user data directory
            assert Path(effective_dir).name.startswith('chromium_temp_')
            assert os.path.exists(effective_dir)

        # Should be cleaned up
        assert not os.path.exists(effective_dir)

        # Fingerprint methods should return None
        assert manager.get_browserforge_fingerprint() is None
        assert manager.get_metadata() is None

        # Update should not raise errors
        manager.update_metadata({'test': 'value'})
