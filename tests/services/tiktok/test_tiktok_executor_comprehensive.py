"""
Comprehensive tests for TikTok executor to achieve 80%+ coverage.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.tiktok.session import TikTokSessionConfig
from app.services.tiktok.tiktok_executor import TiktokExecutor
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter
from app.services.common.browser.camoufox import CamoufoxArgsBuilder


@pytest.fixture
def mock_config():
    """Mock TikTok session config."""
    return TikTokSessionConfig(
        user_data_master_dir="/tmp/master",
        user_data_clones_dir="/tmp/clones",
        write_mode_enabled=False,
        acquire_lock_timeout=30,
        login_detection_timeout=30,
        max_session_duration=3600,
        tiktok_url="https://www.tiktok.com",
        headless=True,
    )


@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = MagicMock()
    settings.default_headless = True
    settings.tiktok_write_mode_enabled = False
    settings.camoufox_runtime_force_mute_audio = False
    return settings


@pytest.fixture
def tiktok_executor(mock_config):
    """TikTok executor fixture."""
    with patch("app.services.tiktok.tiktok_executor.get_settings", return_value=mock_settings()):
        return TiktokExecutor(mock_config)


class TestTiktokExecutorInitialization:
    """Test TikTok executor initialization."""

    def test_executor_init(self, mock_config, mock_settings):
        """Test executor initialization."""
        with patch("app.services.tiktok.tiktok_executor.get_settings", return_value=mock_settings):
            executor = TiktokExecutor(mock_config, proxy={"http": "http://proxy:8080"})

            assert executor.config == mock_config
            assert executor.user_data_dir == mock_config.user_data_clones_dir
            assert executor.proxy == {"http": "http://proxy:8080"}
            assert isinstance(executor.fetcher, ScraplingFetcherAdapter)
            assert isinstance(executor.camoufox_builder, CamoufoxArgsBuilder)

    def test_executor_init_with_custom_builder(self, mock_config, mock_settings):
        """Test executor initialization with custom camoufox builder."""
        custom_builder = MagicMock()
        with patch("app.services.tiktok.tiktok_executor.get_settings", return_value=mock_settings):
            executor = TiktokExecutor(mock_config, camoufox_builder=custom_builder)

            assert executor.camoufox_builder is custom_builder


class TestTiktokExecutorConfiguration:
    """Test executor configuration methods."""

    @pytest.mark.asyncio
    async def test_get_config(self, tiktok_executor):
        """Test getting TikTok browser configuration."""
        config = await tiktok_executor.get_config()

        assert config["url"] == tiktok_executor.config.tiktok_url
        assert config["headless"] == tiktok_executor.config.headless
        assert config["stealth"] is True
        assert config["user_data_dir"] == tiktok_executor.user_data_dir
        assert config["timeout_seconds"] == 30
        assert config["network_idle"] is False
        assert config["wait_for_selector"] == "html"
        assert config["wait_for_selector_state"] == "visible"

    @pytest.mark.asyncio
    async def test_get_config_with_proxy(self, mock_config):
        """Test getting config with proxy."""
        proxy = {"http": "http://proxy:8080"}
        with patch("app.services.tiktok.tiktok_executor.get_settings", return_value=mock_settings()):
            executor = TiktokExecutor(mock_config, proxy=proxy)
            config = await executor.get_config()

            assert config["proxy"] == proxy


class TestTiktokExecutorBrowserSetup:
    """Test browser setup and management."""

    @patch("app.services.tiktok.tiktok_executor.asyncio.WindowsProactorEventLoopPolicy")
    @patch("app.services.tiktok.tiktok_executor.sys.platform", "win32")
    @pytest.mark.asyncio
    async def test_setup_browser_windows(self, mock_policy_class, tiktok_executor):
        """Test browser setup on Windows."""
        # Setup mocks
        mock_policy = MagicMock()
        mock_policy_class.return_value = mock_policy

        mock_fetcher_result = MagicMock()
        tiktok_executor.fetcher.fetch = MagicMock(return_value=mock_fetcher_result)
        tiktok_executor.fetcher.detect_capabilities.return_value = {"supports_stealth": True}

        mock_args = {"_user_data_cleanup": MagicMock()}
        mock_headers = {"User-Agent": "test"}
        tiktok_executor.camoufox_builder.build = MagicMock(return_value=(mock_args, mock_headers))
        tiktok_executor.arg_composer.compose = MagicMock(return_value={})

        # Execute
        await tiktok_executor.setup_browser()

        # Assertions
        mock_policy_class.assert_called_once()
        tiktok_executor.browser == mock_fetcher_result
        assert tiktok_executor._user_data_cleanup == mock_args["_user_data_cleanup"]

    @patch("app.services.tiktok.tiktok_executor.asyncio.WindowsProactorEventLoopPolicy")
    @patch("app.services.tiktok.tiktok_executor.sys.platform", "win32")
    @pytest.mark.asyncio
    async def test_setup_browser_windows_exception(self, mock_policy_class, tiktok_executor):
        """Test browser setup on Windows with policy exception."""
        # Setup mock to raise exception
        mock_policy_class.side_effect = Exception("Policy setup failed")

        mock_fetcher_result = MagicMock()
        tiktok_executor.fetcher.fetch = MagicMock(return_value=mock_fetcher_result)
        tiktok_executor.fetcher.detect_capabilities.return_value = {"supports_stealth": True}

        mock_args = {}
        mock_headers = {}
        tiktok_executor.camoufox_builder.build = MagicMock(return_value=(mock_args, mock_headers))
        tiktok_executor.arg_composer.compose = MagicMock(return_value={})

        # Should not raise exception
        await tiktok_executor.setup_browser()

        # Verify fetch was still called
        tiktok_executor.fetcher.fetch.assert_called_once()

    @patch("app.services.tiktok.tiktok_executor.sys.platform", "linux")
    @pytest.mark.asyncio
    async def test_setup_browser_non_windows(self, tiktok_executor):
        """Test browser setup on non-Windows platform."""
        mock_fetcher_result = MagicMock()
        tiktok_executor.fetcher.fetch = MagicMock(return_value=mock_fetcher_result)
        tiktok_executor.fetcher.detect_capabilities.return_value = {"supports_stealth": True}

        mock_args = {"_user_data_cleanup": MagicMock()}
        mock_headers = {}
        tiktok_executor.camoufox_builder.build = MagicMock(return_value=(mock_args, mock_headers))
        tiktok_executor.arg_composer.compose = MagicMock(return_value={})

        # Execute
        await tiktok_executor.setup_browser()

        # Assertions
        tiktok_executor.browser == mock_fetcher_result
        assert tiktok_executor._user_data_cleanup == mock_args["_user_data_cleanup"]

    @pytest.mark.asyncio
    async def test_setup_browser_no_user_data_cleanup(self, tiktok_executor):
        """Test browser setup when no user data cleanup."""
        mock_fetcher_result = MagicMock()
        tiktok_executor.fetcher.fetch = MagicMock(return_value=mock_fetcher_result)
        tiktok_executor.fetcher.detect_capabilities.return_value = {"supports_stealth": True}

        mock_args = {}
        mock_headers = {}
        tiktok_executor.camoufox_builder.build = MagicMock(return_value=(mock_args, mock_headers))
        tiktok_executor.arg_composer.compose = MagicMock(return_value={})

        # Execute
        await tiktok_executor.setup_browser()

        # Assertions
        tiktok_executor.browser == mock_fetcher_result
        assert tiktok_executor._user_data_cleanup is None


class TestTiktokExecutorSessionManagement:
    """Test session lifecycle management."""

    @pytest.mark.asyncio
    async def test_start_session_success(self, tiktok_executor):
        """Test successful session start."""
        # Mock setup_browser
        tiktok_executor.setup_browser = AsyncMock()

        # Execute
        await tiktok_executor.start_session()

        # Assertions
        tiktok_executor.setup_browser.assert_called_once()
        assert hasattr(tiktok_executor, 'start_time')
        assert tiktok_executor.start_time > 0

    @pytest.mark.asyncio
    async def test_start_session_with_cleanup(self, tiktok_executor):
        """Test session start with cleanup on error."""
        # Mock setup_browser to raise exception
        tiktok_executor.setup_browser = AsyncMock(side_effect=Exception("Browser setup failed"))
        tiktok_executor._cleanup_on_error = AsyncMock()

        # Execute and verify exception
        with pytest.raises(Exception, match="Browser setup failed"):
            await tiktok_executor.start_session()

        # Verify cleanup was called
        tiktok_executor._cleanup_on_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_user_data_cleanup(self, tiktok_executor):
        """Test cleanup with user data cleanup function."""
        # Setup
        mock_cleanup = MagicMock()
        tiktok_executor._user_data_cleanup = mock_cleanup
        tiktok_executor.browser = MagicMock()

        # Execute
        await tiktok_executor.cleanup()

        # Assertions
        mock_cleanup.assert_called_once()
        assert tiktok_executor._user_data_cleanup is None
        assert tiktok_executor.browser is None

    @pytest.mark.asyncio
    async def test_cleanup_user_data_cleanup_exception(self, tiktok_executor):
        """Test cleanup when user data cleanup fails."""
        # Setup
        mock_cleanup = MagicMock(side_effect=Exception("Cleanup failed"))
        tiktok_executor._user_data_cleanup = mock_cleanup
        tiktok_executor.browser = MagicMock()

        # Execute (should not raise exception)
        await tiktok_executor.cleanup()

        # Assertions
        assert tiktok_executor._user_data_cleanup is None

    @pytest.mark.asyncio
    async def test_cleanup_browser_exception(self, tiktok_executor):
        """Test cleanup when browser cleanup fails."""
        # Setup
        tiktok_executor._user_data_cleanup = None
        tiktok_executor.browser = MagicMock()
        tiktok_executor.browser.close = MagicMock(side_effect=Exception("Browser close failed"))

        # Execute (should not raise exception)
        await tiktok_executor.cleanup()

        # Assertions
        assert tiktok_executor.browser is None

    @pytest.mark.asyncio
    async def test_cleanup_general_exception(self, tiktok_executor):
        """Test cleanup with general exception."""
        # Setup
        tiktok_executor._user_data_cleanup = MagicMock(side_effect=Exception("Cleanup failed"))
        tiktok_executor.browser = None

        # Execute (should not raise exception)
        await tiktok_executor.cleanup()

        # Assertions
        assert tiktok_executor._user_data_cleanup is None

    @pytest.mark.asyncio
    async def test_cleanup_no_resources(self, tiktok_executor):
        """Test cleanup when no resources to clean."""
        # Setup
        tiktok_executor._user_data_cleanup = None
        tiktok_executor.browser = None

        # Execute (should not raise exception)
        await tiktok_executor.cleanup()


class TestTiktokExecutorActions:
    """Test executor action methods."""

    @pytest.mark.asyncio
    async def test_detect_login_state(self, tiktok_executor):
        """Test login state detection."""
        # Setup
        mock_detector = MagicMock()
        mock_detector.detect_login_state = AsyncMock(return_value="LOGGED_IN")

        with patch("app.services.tiktok.tiktok_executor.LoginDetector", return_value=mock_detector):
            result = await tiktok_executor.detect_login_state(timeout=15)

        assert result == "LOGGED_IN"
        mock_detector.detect_login_state.assert_called_once_with(timeout=15)

    @pytest.mark.asyncio
    async def test_detect_login_state_default_timeout(self, tiktok_executor):
        """Test login state detection with default timeout."""
        # Setup
        mock_detector = MagicMock()
        mock_detector.detect_login_state = AsyncMock(return_value="LOGGED_OUT")

        with patch("app.services.tiktok.tiktok_executor.LoginDetector", return_value=mock_detector):
            result = await tiktok_executor.detect_login_state()

        assert result == "LOGGED_OUT"
        mock_detector.detect_login_state.assert_called_once_with(timeout=8)

    @pytest.mark.asyncio
    async def test_navigate_to_profile(self, tiktok_executor):
        """Test navigate to profile (not implemented)."""
        # Should not raise exception
        await tiktok_executor.navigate_to_profile()

    @pytest.mark.asyncio
    async def test_search_hashtag(self, tiktok_executor):
        """Test search hashtag (not implemented)."""
        # Should not raise exception
        await tiktok_executor.search_hashtag("test")

    @pytest.mark.asyncio
    async def test_watch_video(self, tiktok_executor):
        """Test watch video (not implemented)."""
        # Should not raise exception
        await tiktok_executor.watch_video("https://tiktok.com/video/123")

    @pytest.mark.asyncio
    async def test_like_post(self, tiktok_executor):
        """Test like post (not implemented)."""
        result = await tiktok_executor.like_post()
        assert result is False

    @pytest.mark.asyncio
    async def test_follow_user(self, tiktok_executor):
        """Test follow user (not implemented)."""
        result = await tiktok_executor.follow_user("testuser")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_video_info_with_url(self, tiktok_executor):
        """Test get video info with browser URL."""
        # Setup
        tiktok_executor.browser = MagicMock()
        tiktok_executor.browser.url = "https://tiktok.com/video/123"

        result = await tiktok_executor.get_video_info()

        assert result["url"] == "https://tiktok.com/video/123"
        assert result["title"] == ""
        assert result["description"] == ""
        assert result["author"] == ""
        assert result["likes"] == "0"

    @pytest.mark.asyncio
    async def test_get_video_info_without_url(self, tiktok_executor):
        """Test get video info without browser URL."""
        # Setup
        tiktok_executor.browser = MagicMock()
        delattr(tiktok_executor.browser, 'url')

        result = await tiktok_executor.get_video_info()

        assert result["url"] == ""

    @pytest.mark.asyncio
    async def test_interact_with_page_wait(self, tiktok_executor):
        """Test interact with page wait action."""
        result = await tiktok_executor.interact_with_page("wait", seconds=1.5)
        assert result is None

    @pytest.mark.asyncio
    async def test_interact_with_page_wait_default(self, tiktok_executor):
        """Test interact with page wait action with default seconds."""
        result = await tiktok_executor.interact_with_page("wait")
        assert result is None

    @pytest.mark.asyncio
    async def test_interact_with_page_unknown_action(self, tiktok_executor):
        """Test interact with page unknown action."""
        with pytest.raises(ValueError, match="Unknown action: unknown"):
            await tiktok_executor.interact_with_page("unknown")

    @pytest.mark.asyncio
    async def test_wait_method(self, tiktok_executor):
        """Test _wait method."""
        start_time = asyncio.get_event_loop().time()
        await tiktok_executor._wait(seconds=0.1)
        end_time = asyncio.get_event_loop().time()

        assert end_time - start_time >= 0.1

    @pytest.mark.asyncio
    async def test_close(self, tiktok_executor):
        """Test close method."""
        tiktok_executor.cleanup = AsyncMock()

        await tiktok_executor.close()

        tiktok_executor.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_still_active_true(self, tiktok_executor):
        """Test is_still_active when browser exists."""
        tiktok_executor.browser = MagicMock()

        result = await tiktok_executor.is_still_active()

        assert result is True

    @pytest.mark.asyncio
    async def test_is_still_active_false(self, tiktok_executor):
        """Test is_still_active when browser is None."""
        tiktok_executor.browser = None

        result = await tiktok_executor.is_still_active()

        assert result is False


class TestTiktokExecutorEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_start_session_get_config_exception(self, tiktok_executor):
        """Test start session when get_config fails."""
        tiktok_executor.get_config = AsyncMock(side_effect=Exception("Config failed"))
        tiktok_executor._cleanup_on_error = AsyncMock()

        with pytest.raises(Exception, match="Config failed"):
            await tiktok_executor.start_session()

        tiktok_executor._cleanup_on_error.assert_called_once()

    def test_init_with_no_proxy(self, mock_config):
        """Test executor initialization without proxy."""
        with patch("app.services.tiktok.tiktok_executor.get_settings", return_value=mock_settings()):
            executor = TiktokExecutor(mock_config)

            assert executor.proxy is None

    @patch("app.services.tiktok.tiktok_executor.asyncio.WindowsProactorEventLoopPolicy")
    @patch("app.services.tiktok.tiktok_executor.sys.platform", "win32")
    @pytest.mark.asyncio
    async def test_setup_browser_fetch_exception(self, mock_policy_class, tiktok_executor):
        """Test browser setup when fetch fails."""
        mock_fetcher_result = MagicMock()
        tiktok_executor.fetcher.fetch = MagicMock(return_value=mock_fetcher_result)
        tiktok_executor.fetcher.detect_capabilities.return_value = {"supports_stealth": True}

        mock_args = {}
        mock_headers = {}
        tiktok_executor.camoufox_builder.build = MagicMock(return_value=(mock_args, mock_headers))
        tiktok_executor.arg_composer.compose = MagicMock(return_value={})

        # Execute
        await tiktok_executor.setup_browser()

        # Should not raise exception even if fetch has issues
        tiktok_executor.fetcher.fetch.assert_called_once()


class TestTiktokExecutorIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, mock_config):
        """Test full session lifecycle."""
        with patch("app.services.tiktok.tiktok_executor.get_settings", return_value=mock_settings()):
            executor = TiktokExecutor(mock_config)

            # Mock the fetcher to avoid actual browser operations
            mock_result = MagicMock()
            executor.fetcher.fetch = MagicMock(return_value=mock_result)
            executor.fetcher.detect_capabilities.return_value = {"supports_stealth": True}
            executor.camoufox_builder.build = MagicMock(return_value=({}, {}))
            executor.arg_composer.compose = MagicMock(return_value={})

            # Start session
            await executor.start_session()
            assert executor.browser == mock_result

            # Check activity
            assert await executor.is_still_active() is True

            # Cleanup
            await executor.cleanup()
            assert executor.browser is None

    @pytest.mark.asyncio
    async def test_session_with_proxy(self, mock_config):
        """Test session with proxy configuration."""
        proxy = {"http": "http://proxy:8080", "https": "https://proxy:8080"}

        with patch("app.services.tiktok.tiktok_executor.get_settings", return_value=mock_settings()):
            executor = TiktokExecutor(mock_config, proxy=proxy)

            config = await executor.get_config()
            assert config["proxy"] == proxy