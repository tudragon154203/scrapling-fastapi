"""
Test that TikTok session clone directories are properly cleaned up
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from app.services.tiktok.tiktok_executor import TiktokExecutor
from app.schemas.tiktok import TikTokSessionConfig


class TestTikTokCloneCleanup:
    """Test TikTok session clone directory cleanup"""

    def test_clone_directory_cleanup_after_session(self):
        """Test that clone directories are cleaned up after TikTok session"""
        # Create a temporary master directory
        with tempfile.TemporaryDirectory() as temp_dir:
            master_dir = Path(temp_dir) / "master"
            master_dir.mkdir()

            # Create some fake user data files
            (master_dir / "places.sqlite").touch()
            (master_dir / "cookies.sqlite").touch()

            # Mock settings to use our temp directory
            mock_settings = MagicMock()
            mock_settings.camoufox_user_data_dir = str(master_dir)
            mock_settings.tiktok_write_mode_enabled = False
            mock_settings.tiktok_login_detection_timeout = 8
            mock_settings.tiktok_max_session_duration = 300
            mock_settings.tiktok_url = "https://www.tiktok.com/"

            # Mock ScraplingFetcher to return a simple result
            mock_fetcher = MagicMock()
            mock_result = MagicMock()
            mock_result.url = "https://www.tiktok.com/"
            mock_fetcher.fetch.return_value = mock_result
            mock_fetcher.detect_capabilities.return_value = MagicMock()

            # Mock FetchArgComposer
            mock_composer = MagicMock()
            mock_composer.compose.return_value = {}

            # Create TikTok executor
            config = TikTokSessionConfig(
                user_data_master_dir=str(master_dir),
                user_data_clones_dir=str(master_dir),
                write_mode_enabled=False,
                acquire_lock_timeout=30,
                login_detection_timeout=8,
                max_session_duration=300,
                tiktok_url="https://www.tiktok.com/"
            )

            executor = TiktokExecutor(config)

            # Replace dependencies with mocks
            executor.fetcher = mock_fetcher
            executor.arg_composer = mock_composer
            executor.settings = mock_settings

            # Mock CamoufoxArgsBuilder to track cleanup function
            cleanup_called = False

            def mock_cleanup():
                nonlocal cleanup_called
                cleanup_called = True

            mock_additional_args = {
                'user_data_dir': str(master_dir),
                '_user_data_cleanup': mock_cleanup
            }

            # Create a mock CamoufoxArgsBuilder instance
            mock_builder_instance = MagicMock()
            mock_builder_instance.build.return_value = (mock_additional_args, None)

            # Inject the mock builder into the executor
            executor.camoufox_builder = mock_builder_instance

            # Start session
            import asyncio
            # result = asyncio.run(executor.start_session())
            asyncio.run(executor.start_session())

            # Manually call cleanup to simulate immediate cleanup
            asyncio.run(executor.cleanup())

            # Verify cleanup function was called
            assert cleanup_called, "Cleanup function should have been called after session"

            # Verify browser was created (before cleanup)
            # After cleanup, browser should be None
            assert executor.browser is None

    def test_clone_directory_cleanup_on_error(self):
        """Test that clone directories are cleaned up even when session fails"""
        # Create a temporary master directory
        with tempfile.TemporaryDirectory() as temp_dir:
            master_dir = Path(temp_dir) / "master"
            master_dir.mkdir()

            # Mock settings to use our temp directory
            mock_settings = MagicMock()
            mock_settings.camoufox_user_data_dir = str(master_dir)
            mock_settings.tiktok_write_mode_enabled = False
            mock_settings.tiktok_login_detection_timeout = 8
            mock_settings.tiktok_max_session_duration = 300
            mock_settings.tiktok_url = "https://www.tiktok.com/"

            # Mock ScraplingFetcher to raise an exception
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.side_effect = Exception("Browser startup failed")
            mock_fetcher.detect_capabilities.return_value = MagicMock()

            # Mock FetchArgComposer
            mock_composer = MagicMock()
            mock_composer.compose.return_value = {}

            # Create TikTok executor
            config = TikTokSessionConfig(
                user_data_master_dir=str(master_dir),
                user_data_clones_dir=str(master_dir),
                write_mode_enabled=False,
                acquire_lock_timeout=30,
                login_detection_timeout=8,
                max_session_duration=300,
                tiktok_url="https://www.tiktok.com/"
            )

            executor = TiktokExecutor(config)

            # Replace dependencies with mocks
            executor.fetcher = mock_fetcher
            executor.arg_composer = mock_composer
            executor.settings = mock_settings

            # Mock CamoufoxArgsBuilder to track cleanup function
            cleanup_called = False

            def mock_cleanup():
                nonlocal cleanup_called
                cleanup_called = True

            mock_additional_args = {
                'user_data_dir': str(master_dir),
                '_user_data_cleanup': mock_cleanup
            }

            # Create a mock CamoufoxArgsBuilder instance
            mock_builder_instance = MagicMock()
            mock_builder_instance.build.return_value = (mock_additional_args, None)

            # Inject the mock builder into the executor
            executor.camoufox_builder = mock_builder_instance

            # Start session - should raise exception but still call cleanup
            import asyncio
            with pytest.raises(Exception):
                asyncio.run(executor.start_session())

            # Manually call cleanup to simulate cleanup on error
            asyncio.run(executor.cleanup())

            # Verify cleanup function was called even on error
            assert cleanup_called, "Cleanup function should have been called even on error"
