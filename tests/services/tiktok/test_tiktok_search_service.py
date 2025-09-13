"""
Unit tests for TikTok Search Service
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.tiktok.service import TiktokService
from app.services.tiktok.tiktok_executor import TiktokExecutor


class TestTikTokSearchService:
    """Unit tests for TikTok search service functionality"""

    @pytest.fixture
    def tiktok_service(self):
        """Create a TikTok service instance for testing"""
        return TiktokService()

    @pytest.fixture
    def mock_executor(self):
        """Create a mock TikTok executor for testing"""
        executor = Mock(spec=TiktokExecutor)
        executor.browser = Mock()
        return executor

    @pytest.mark.asyncio
    async def test_search_tiktok_with_active_session(self, tiktok_service, mock_executor):
        """Test TikTok search with active session"""
        # Set up mock session
        tiktok_service.active_sessions["test_session"] = mock_executor
        tiktok_service.session_metadata["test_session"] = {
            "created_at": Mock(),
            "last_activity": Mock(),
            "user_data_dir": "/tmp/test",
            "config": Mock(),
            "login_state": "logged_in"
        }

        # Mock the search_tiktok method to return test data
        with patch.object(tiktok_service, 'get_active_session', new=AsyncMock(return_value=mock_executor)):
            result = await tiktok_service.search_tiktok("test query")

            # Verify the result structure
            assert "results" in result
            assert "totalResults" in result
            assert "query" in result
            assert result["query"] == "test query"

    @pytest.mark.asyncio
    async def test_search_tiktok_with_multiple_queries(self, tiktok_service, mock_executor):
        """Test TikTok search with multiple queries"""
        # Set up mock session
        tiktok_service.active_sessions["test_session"] = mock_executor
        tiktok_service.session_metadata["test_session"] = {
            "created_at": Mock(),
            "last_activity": Mock(),
            "user_data_dir": "/tmp/test",
            "config": Mock(),
            "login_state": "logged_in"
        }

        # Mock the search_tiktok method to return test data
        with patch.object(tiktok_service, 'get_active_session', new=AsyncMock(return_value=mock_executor)):
            result = await tiktok_service.search_tiktok(["test", "query"])

            # Verify the result structure
            assert "results" in result
            assert "totalResults" in result
            assert "query" in result
            assert result["query"] == "test query"

    @pytest.mark.asyncio
    async def test_search_tiktok_without_active_session(self, tiktok_service):
        """Test TikTok search without active session returns error"""
        result = await tiktok_service.search_tiktok("test query")

        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "NOT_LOGGED_IN"
        assert result["error"]["message"] == "TikTok session is not logged in"

    @pytest.mark.asyncio
    async def test_search_tiktok_with_empty_session(self, tiktok_service):
        """Test TikTok search with empty session returns error"""
        # Set up empty session state
        tiktok_service.active_sessions = {}

        result = await tiktok_service.search_tiktok("test query")

        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "NOT_LOGGED_IN"
        assert result["error"]["message"] == "TikTok session is not logged in"

    @pytest.mark.asyncio
    async def test_has_active_session_with_sessions(self, tiktok_service, mock_executor):
        """Test has_active_session returns True when sessions exist"""
        tiktok_service.active_sessions["test_session"] = mock_executor

        result = await tiktok_service.has_active_session()
        assert result is True

    @pytest.mark.asyncio
    async def test_has_active_session_without_sessions(self, tiktok_service):
        """Test has_active_session returns False when no sessions exist"""
        tiktok_service.active_sessions = {}

        result = await tiktok_service.has_active_session()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_active_session_with_sessions(self, tiktok_service, mock_executor):
        """Test get_active_session returns session when sessions exist"""
        tiktok_service.active_sessions["test_session"] = mock_executor

        result = await tiktok_service.get_active_session()
        assert result == mock_executor

    @pytest.mark.asyncio
    async def test_get_active_session_without_sessions(self, tiktok_service):
        """Test get_active_session returns None when no sessions exist"""
        tiktok_service.active_sessions = {}

        result = await tiktok_service.get_active_session()
        assert result is None
