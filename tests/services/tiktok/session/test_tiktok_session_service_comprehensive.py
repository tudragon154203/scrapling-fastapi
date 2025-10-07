"""
Comprehensive tests for TikTok session service to achieve 80%+ coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.tiktok.session import (
    TikTokLoginState,
    TikTokSessionConfig,
    TikTokSessionRequest,
    TikTokSessionResponse,
)
from app.services.tiktok.session.registry import SessionRecord, SessionRegistry
from app.services.tiktok.session.service import TiktokService
from app.services.tiktok.tiktok_executor import TiktokExecutor
from app.services.tiktok.utils.login_detection import LoginDetector


@pytest.fixture
def mock_settings():
    """Mock settings fixture."""
    settings = MagicMock()
    settings.tiktok_write_mode_enabled = False
    settings.tiktok_login_detection_timeout = 30
    settings.tiktok_max_session_duration = 3600
    settings.tiktok_url = "https://www.tiktok.com"
    settings.default_headless = True
    settings.camoufox_user_data_dir = "./user_data"
    settings.camoufox_runtime_force_mute_audio = False
    return settings


@pytest.fixture
def mock_session_registry():
    """Mock session registry."""
    return SessionRegistry()


@pytest.fixture
def tiktok_service(mock_session_registry, mock_settings):
    """TikTok service fixture."""
    with patch("app.services.tiktok.session.service.get_settings", return_value=mock_settings):
        return TiktokService(session_registry=mock_session_registry)


@pytest.fixture
def mock_executor():
    """Mock TikTok executor."""
    executor = AsyncMock(spec=TiktokExecutor)
    executor.user_data_dir = "/tmp/test_user_data"
    executor.browser = AsyncMock()
    executor.is_still_active.return_value = True
    executor.get_session_info.return_value = {"test": "info"}
    return executor


@pytest.fixture
def mock_login_detector():
    """Mock login detector."""
    detector = AsyncMock(spec=LoginDetector)
    return detector


class TestTiktokServiceCreation:
    """Test TikTok service creation and session management."""

    @patch("app.services.tiktok.session.service.TiktokExecutor")
    @patch("app.services.tiktok.session.service.LoginDetector")
    @pytest.mark.asyncio
    async def test_create_session_success_logged_in(self, mock_detector_class, mock_executor_class, tiktok_service, mock_executor):
        """Test successful session creation when logged in."""
        # Setup mocks
        mock_executor_instance = AsyncMock(spec=TiktokExecutor)
        mock_executor_instance.user_data_dir = "/tmp/test_user_data"
        mock_executor_instance.browser = AsyncMock()
        mock_executor_class.return_value = mock_executor_instance

        mock_detector_instance = AsyncMock(spec=LoginDetector)
        mock_detector_instance.detect_login_state.return_value = TikTokLoginState.LOGGED_IN
        mock_detector_class.return_value = mock_detector_instance

        request = TikTokSessionRequest()

        # Execute
        result = await tiktok_service.create_session(request)

        # Assertions
        assert result.status == "success"
        assert "successfully" in result.message
        assert len(tiktok_service.sessions) == 1
        mock_executor_instance.start_session.assert_called_once()
        mock_detector_instance.detect_login_state.assert_called_once()

    @patch("app.services.tiktok.session.service.TiktokExecutor")
    @patch("app.services.tiktok.session.service.LoginDetector")
    @pytest.mark.asyncio
    async def test_create_session_not_logged_in(self, mock_detector_class, mock_executor_class, tiktok_service):
        """Test session creation when not logged in."""
        # Setup mocks
        mock_executor_instance = AsyncMock(spec=TiktokExecutor)
        mock_executor_instance.user_data_dir = "/tmp/test_user_data"
        mock_executor_instance.browser = AsyncMock()
        mock_executor_class.return_value = mock_executor_instance

        mock_detector_instance = AsyncMock(spec=LoginDetector)
        mock_detector_instance.detect_login_state.return_value = TikTokLoginState.LOGGED_OUT
        mock_detector_class.return_value = mock_detector_instance

        request = TikTokSessionRequest()

        # Execute
        result = await tiktok_service.create_session(request)

        # Assertions
        assert result.status == "error"
        assert "Not logged in" in result.message
        assert result.error_details["code"] == "NOT_LOGGED_IN"
        assert len(tiktok_service.sessions) == 0

    @patch("app.services.tiktok.session.service.TiktokExecutor")
    @pytest.mark.asyncio
    async def test_create_session_exception(self, mock_executor_class, tiktok_service):
        """Test session creation with exception."""
        # Setup mock to raise exception
        mock_executor_class.side_effect = Exception("Browser failed to start")

        request = TikTokSessionRequest()

        # Execute
        result = await tiktok_service.create_session(request)

        # Assertions
        assert result.status == "error"
        assert "Failed to create TikTok session" in result.message
        assert result.error_details["code"] == "SESSION_CREATION_FAILED"

    @patch("app.services.tiktok.session.service.TiktokExecutor")
    @patch("app.services.tiktok.session.service.LoginDetector")
    @pytest.mark.asyncio
    async def test_create_session_immediate_cleanup(self, mock_detector_class, mock_executor_class, tiktok_service):
        """Test session creation with immediate cleanup."""
        # Setup mocks
        mock_executor_instance = AsyncMock(spec=TiktokExecutor)
        mock_executor_instance.user_data_dir = "/tmp/test_user_data"
        mock_executor_instance.browser = AsyncMock()
        mock_executor_class.return_value = mock_executor_instance

        mock_detector_instance = AsyncMock(spec=LoginDetector)
        mock_detector_instance.detect_login_state.return_value = TikTokLoginState.LOGGED_IN
        mock_detector_class.return_value = mock_detector_instance

        request = TikTokSessionRequest()

        # Execute
        result = await tiktok_service.create_session(request, immediate_cleanup=True)

        # Assertions
        assert result.status == "success"
        assert len(tiktok_service.sessions) == 0
        mock_executor_instance.cleanup.assert_called_once()

    @patch("app.services.tiktok.session.service.TiktokExecutor")
    @patch("app.services.tiktok.session.service.LoginDetector")
    @pytest.mark.asyncio
    async def test_create_session_uncertain_state(self, mock_detector_class, mock_executor_class, tiktok_service):
        """Test session creation with uncertain login state."""
        # Setup mocks
        mock_executor_instance = AsyncMock(spec=TiktokExecutor)
        mock_executor_instance.user_data_dir = "/tmp/test_user_data"
        mock_executor_instance.browser = None  # No browser
        mock_executor_class.return_value = mock_executor_instance

        request = TikTokSessionRequest()

        # Execute
        result = await tiktok_service.create_session(request)

        # Assertions
        assert result.status == "error"
        assert "Not logged in" in result.message


class TestTiktokServiceSessionManagement:
    """Test session management methods."""

    @pytest.mark.asyncio
    async def test_has_active_session_true(self, tiktok_service, mock_executor):
        """Test has_active_session when session exists."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.has_active_session()
        assert result is True

    @pytest.mark.asyncio
    async def test_has_active_session_false(self, tiktok_service):
        """Test has_active_session when no sessions."""
        result = await tiktok_service.has_active_session()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_active_session_exists(self, tiktok_service, mock_executor):
        """Test get_active_session when session exists."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.get_active_session()
        assert result is mock_executor

    @pytest.mark.asyncio
    async def test_get_active_session_none(self, tiktok_service):
        """Test get_active_session when no sessions."""
        result = await tiktok_service.get_active_session()
        assert result is None

    @pytest.mark.asyncio
    async def test_close_session_exists(self, tiktok_service, mock_executor):
        """Test close_session when session exists."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.close_session("test-session")
        assert result is True
        assert len(tiktok_service.sessions) == 0
        mock_executor.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_session_not_found(self, tiktok_service):
        """Test close_session when session doesn't exist."""
        result = await tiktok_service.close_session("non-existent")
        assert result is False

    @pytest.mark.asyncio
    async def test_keep_alive_success(self, tiktok_service, mock_executor):
        """Test keep_alive successful."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.keep_alive("test-session")
        assert result is True

    @pytest.mark.asyncio
    async def test_keep_alive_not_found(self, tiktok_service):
        """Test keep_alive when session not found."""
        result = await tiktok_service.keep_alive("non-existent")
        assert result is False

    @pytest.mark.asyncio
    async def test_keep_alive_inactive(self, tiktok_service, mock_executor):
        """Test keep_alive when session is inactive."""
        mock_executor.is_still_active.return_value = False

        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.keep_alive("test-session")
        assert result is False
        assert len(tiktok_service.sessions) == 0

    @pytest.mark.asyncio
    async def test_get_session_info_success(self, tiktok_service, mock_executor):
        """Test get_session_info successful."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.get_session_info("test-session")
        assert result is not None
        assert "test" in result
        assert "timeout_remaining" in result

    @pytest.mark.asyncio
    async def test_get_session_info_not_found(self, tiktok_service):
        """Test get_session_info when session not found."""
        result = await tiktok_service.get_session_info("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_info_exception(self, tiktok_service, mock_executor):
        """Test get_session_info with exception."""
        mock_executor.get_session_info.side_effect = Exception("Failed to get info")

        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.get_session_info("test-session")
        assert result is None

    @pytest.mark.asyncio
    async def test_perform_action_success(self, tiktok_service, mock_executor):
        """Test perform_action successful."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        # Setup mock method
        mock_executor.test_action.return_value = "action_result"

        result = await tiktok_service.perform_action("test-session", "test_action", arg1="value1")
        assert result["success"] is True
        assert result["result"] == "action_result"

    @pytest.mark.asyncio
    async def test_perform_action_not_found(self, tiktok_service):
        """Test perform_action when session not found."""
        result = await tiktok_service.perform_action("non-existent", "test_action")
        assert result["error"] == "Session not found"

    @pytest.mark.asyncio
    async def test_perform_action_unknown_action(self, tiktok_service, mock_executor):
        """Test perform_action with unknown action."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.perform_action("test-session", "unknown_action")
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_perform_action_exception(self, tiktok_service, mock_executor):
        """Test perform_action with exception."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        # Setup mock to raise exception
        mock_executor.test_action.side_effect = Exception("Action failed")

        result = await tiktok_service.perform_action("test-session", "test_action")
        assert "error" in result
        assert "Action failed" in result["error"]

    @pytest.mark.asyncio
    async def test_check_session_timeout_exists(self, tiktok_service, mock_executor):
        """Test check_session_timeout when session exists."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.check_session_timeout("test-session")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_session_timeout_not_found(self, tiktok_service):
        """Test check_session_timeout when session not found."""
        result = await tiktok_service.check_session_timeout("non-existent")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, tiktok_service, mock_executor):
        """Test get_active_sessions."""
        # Add a session
        record = SessionRecord(
            id="test-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.get_active_sessions()
        assert "test-session" in result
        assert result["test-session"]["test"] == "info"

    @pytest.mark.asyncio
    async def test_cleanup_all_sessions(self, tiktok_service, mock_executor):
        """Test cleanup_all_sessions."""
        # Add multiple sessions
        for i in range(3):
            record = SessionRecord(
                id=f"test-session-{i}",
                executor=mock_executor,
                config=MagicMock(),
                login_state=TikTokLoginState.LOGGED_IN,
                user_data_dir="/tmp/test"
            )
            tiktok_service.sessions.register(record)

        await tiktok_service.cleanup_all_sessions()
        assert len(tiktok_service.sessions) == 0
        assert mock_executor.cleanup.call_count == 3


class TestTiktokServiceConfiguration:
    """Test configuration loading methods."""

    @pytest.mark.asyncio
    async def test_load_tiktok_config_default(self, tiktok_service, mock_settings):
        """Test loading TikTok config with defaults."""
        result = await tiktok_service._load_tiktok_config()

        assert isinstance(result, TikTokSessionConfig)
        assert result.write_mode_enabled == mock_settings.tiktok_write_mode_enabled
        assert result.login_detection_timeout == mock_settings.tiktok_login_detection_timeout
        assert result.max_session_duration == mock_settings.tiktok_max_session_duration
        assert result.tiktok_url == mock_settings.tiktok_url
        assert result.headless is True

    @pytest.mark.asyncio
    async def test_load_tiktok_config_master_dir(self, tiktok_service, tmp_path):
        """Test loading config with master directory."""
        master_dir = tmp_path / "master"
        master_dir.mkdir()

        result = await tiktok_service._load_tiktok_config(str(master_dir))

        assert result.user_data_master_dir == str(master_dir)
        assert "clones" in result.user_data_clones_dir

    @pytest.mark.asyncio
    async def test_load_tiktok_config_clones_dir(self, tiktok_service, tmp_path):
        """Test loading config with clones directory."""
        clones_dir = tmp_path / "clones"
        clones_dir.mkdir()

        result = await tiktok_service._load_tiktok_config(str(clones_dir))

        assert result.user_data_clones_dir == str(clones_dir)
        assert "master" in result.user_data_master_dir

    @patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "tests/unit/test_something.py"})
    @pytest.mark.asyncio
    async def test_load_tiktok_config_unit_test(self, tiktok_service):
        """Test loading config in unit test environment."""
        result = await tiktok_service._load_tiktok_config()
        assert result.headless is True

    @patch("app.services.tiktok.session.service.LoginDetector")
    @pytest.mark.asyncio
    async def test_detect_login_state_no_browser(self, mock_detector_class, tiktok_service, mock_executor):
        """Test login detection with no browser."""
        mock_executor.browser = None
        config = MagicMock()

        result = await tiktok_service._detect_login_state(mock_executor, config, 30)

        assert result == TikTokLoginState.UNCERTAIN
        mock_detector_class.assert_not_called()

    @patch("app.services.tiktok.session.service.LoginDetector")
    @pytest.mark.asyncio
    async def test_detect_login_state_with_browser(self, mock_detector_class, tiktok_service, mock_executor):
        """Test login detection with browser."""
        mock_detector_instance = AsyncMock(spec=LoginDetector)
        mock_detector_instance.detect_login_state.return_value = TikTokLoginState.LOGGED_IN
        mock_detector_class.return_value = mock_detector_instance

        config = MagicMock()

        result = await tiktok_service._detect_login_state(mock_executor, config, 30)

        assert result == TikTokLoginState.LOGGED_IN
        mock_detector_instance.detect_login_state.assert_called_once_with(timeout=30)

    @pytest.mark.asyncio
    async def test_safe_cleanup_executor_success(self, tiktok_service, mock_executor):
        """Test successful executor cleanup."""
        await tiktok_service._safe_cleanup_executor(mock_executor)
        mock_executor.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_cleanup_executor_exception(self, tiktok_service, mock_executor):
        """Test executor cleanup with exception."""
        mock_executor.cleanup.side_effect = Exception("Cleanup failed")

        # Should not raise exception
        await tiktok_service._safe_cleanup_executor(mock_executor)
        mock_executor.cleanup.assert_called_once()

    def test_error_response_without_details(self, tiktok_service):
        """Test error response without details."""
        result = tiktok_service._error_response(
            message="Test error",
            code="TEST_ERROR"
        )

        assert isinstance(result, TikTokSessionResponse)
        assert result.status == "error"
        assert result.message == "Test error"
        assert result.error_details["code"] == "TEST_ERROR"

    def test_error_response_with_details(self, tiktok_service):
        """Test error response with details."""
        details = {"method": "test", "timeout": 30}
        result = tiktok_service._error_response(
            message="Test error",
            code="TEST_ERROR",
            details=details
        )

        assert isinstance(result, TikTokSessionResponse)
        assert result.error_details["code"] == "TEST_ERROR"
        assert result.error_details["method"] == "test"
        assert result.error_details["timeout"] == 30


class TestTiktokServiceAudioMuteHandling:
    """Test audio mute handling during session creation."""

    @patch("app.services.tiktok.session.service.TiktokExecutor")
    @patch("app.services.tiktok.session.service.LoginDetector")
    @pytest.mark.asyncio
    async def test_mute_audio_enabled(self, mock_detector_class, mock_executor_class, tiktok_service, mock_settings):
        """Test audio mute when enabled in settings."""
        mock_settings.camoufox_runtime_force_mute_audio = True

        mock_executor_instance = AsyncMock(spec=TiktokExecutor)
        mock_executor_instance.user_data_dir = "/tmp/test_user_data"
        mock_executor_instance.browser = AsyncMock()
        mock_executor_class.return_value = mock_executor_instance

        mock_detector_instance = AsyncMock(spec=LoginDetector)
        mock_detector_instance.detect_login_state.return_value = TikTokLoginState.LOGGED_IN
        mock_detector_class.return_value = mock_detector_instance

        request = TikTokSessionRequest()

        # Execute
        await tiktok_service.create_session(request)

        # Verify mute was handled (should remain True since it was already True)
        assert tiktok_service.settings.camoufox_runtime_force_mute_audio is True

    @patch("app.services.tiktok.session.service.TiktokExecutor")
    @patch("app.services.tiktok.session.service.LoginDetector")
    @pytest.mark.asyncio
    async def test_mute_audio_disabled(self, mock_detector_class, mock_executor_class, tiktok_service, mock_settings):
        """Test audio mute handling when disabled."""
        mock_settings.camoufox_runtime_force_mute_audio = False

        mock_executor_instance = AsyncMock(spec=TiktokExecutor)
        mock_executor_instance.user_data_dir = "/tmp/test_user_data"
        mock_executor_instance.browser = AsyncMock()
        mock_executor_class.return_value = mock_executor_instance

        mock_detector_instance = AsyncMock(spec=LoginDetector)
        mock_detector_instance.detect_login_state.return_value = TikTokLoginState.LOGGED_IN
        mock_detector_class.return_value = mock_detector_instance

        request = TikTokSessionRequest()

        # Execute
        await tiktok_service.create_session(request)

        # Verify mute was restored to False
        assert tiktok_service.settings.camoufox_runtime_force_mute_audio is False


class TestTiktokServiceEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_cleanup_session_not_found(self, tiktok_service):
        """Test cleanup session when not found."""
        # Should not raise exception
        await tiktok_service._cleanup_session("non-existent")

    @patch("app.services.tiktok.session.service.TiktokExecutor")
    @patch("app.services.tiktok.session.service.LoginDetector")
    @pytest.mark.asyncio
    async def test_create_session_with_user_data_dir(self, mock_detector_class, mock_executor_class, tiktok_service):
        """Test session creation with custom user data dir."""
        mock_executor_instance = AsyncMock(spec=TiktokExecutor)
        mock_executor_instance.user_data_dir = "/tmp/custom_user_data"
        mock_executor_instance.browser = AsyncMock()
        mock_executor_class.return_value = mock_executor_instance

        mock_detector_instance = AsyncMock(spec=LoginDetector)
        mock_detector_instance.detect_login_state.return_value = TikTokLoginState.LOGGED_IN
        mock_detector_class.return_value = mock_detector_instance

        request = TikTokSessionRequest()
        custom_dir = "/custom/user/data"

        result = await tiktok_service.create_session(request, user_data_dir=custom_dir)

        assert result.status == "success"
        assert len(tiktok_service.sessions) == 1

    @patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "tests/integration/test_integration.py"})
    @pytest.mark.asyncio
    async def test_load_tiktok_config_integration_test(self, tiktok_service):
        """Test loading config in integration test environment."""
        result = await tiktok_service._load_tiktok_config()
        # Should respect default headless setting for integration tests
        assert isinstance(result, TikTokSessionConfig)

    @pytest.mark.asyncio
    async def test_get_active_sessions_with_cleanup(self, tiktok_service, mock_executor):
        """Test get_active_sessions cleans up invalid sessions."""
        # Add a session that will fail to get info
        mock_executor.get_session_info.side_effect = Exception("Session dead")

        record = SessionRecord(
            id="dead-session",
            executor=mock_executor,
            config=MagicMock(),
            login_state=TikTokLoginState.LOGGED_IN,
            user_data_dir="/tmp/test"
        )
        tiktok_service.sessions.register(record)

        result = await tiktok_service.get_active_sessions()

        # Should clean up dead session
        assert len(result) == 0
        assert len(tiktok_service.sessions) == 0
