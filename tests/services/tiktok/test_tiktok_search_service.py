"""Unit tests for TikTok Search Service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.tiktok.search_service import TikTokSearchService
from app.services.tiktok.service import TiktokService
from app.services.tiktok.tiktok_executor import TiktokExecutor


pytestmark = pytest.mark.asyncio


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

        # Mock the independent search service to avoid network calls
        with patch.object(
            tiktok_service, 'get_active_session', new=AsyncMock(return_value=mock_executor)
        ), patch("app.services.tiktok.service.TikTokSearchService") as mock_search_service:
            mock_instance = mock_search_service.return_value
            mock_instance.search = AsyncMock(
                return_value={"results": [{"id": "123"}], "totalResults": 1, "query": "test query"}
            )

            result = await tiktok_service.search_tiktok("test query")

            mock_search_service.assert_called_once_with(tiktok_service)
            mock_instance.search.assert_awaited_once_with(
                "test query", num_videos=50, sort_type="RELEVANCE", recency_days="ALL"
            )

            # Verify the result structure
            assert "results" in result
            assert "totalResults" in result
            assert "query" in result
            assert result["query"] == "test query"

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

        # Mock the independent search service to avoid network calls
        with patch.object(
            tiktok_service, 'get_active_session', new=AsyncMock(return_value=mock_executor)
        ), patch("app.services.tiktok.service.TikTokSearchService") as mock_search_service:
            mock_instance = mock_search_service.return_value
            mock_instance.search = AsyncMock(
                return_value={"results": [{"id": "456"}], "totalResults": 1, "query": "test query"}
            )

            result = await tiktok_service.search_tiktok(["test", "query"])

            mock_search_service.assert_called_once_with(tiktok_service)
            mock_instance.search.assert_awaited_once_with(
                ["test", "query"],
                num_videos=50,
                sort_type="RELEVANCE",
                recency_days="ALL",
            )

            # Verify the result structure
            assert "results" in result
            assert "totalResults" in result
            assert "query" in result
            assert result["query"] == "test query"

    async def test_search_service_continues_after_query_error(self):
        """TikTokSearchService should continue processing queries on recoverable errors."""

        service = Mock()
        service.settings = Mock()
        service.settings.tiktok_url = "https://www.tiktok.com/"
        service.settings.private_proxy_url = None

        search_service = TikTokSearchService(service)

        with patch.object(
            TikTokSearchService, "_prepare_context", return_value={
                "fetcher": Mock(),
                "composer": Mock(),
                "caps": {},
                "additional_args": {},
                "extra_headers": None,
                "user_data_cleanup": None,
                "options": {},
            }
        ), patch("app.services.tiktok.parser.orchestrator.TikTokSearchParser") as mock_parser_cls, patch.object(
            TikTokSearchService, "_process_query", side_effect=[None, True]
        ) as mock_process_query, patch.object(
            TikTokSearchService, "_cleanup_user_data", new=AsyncMock()
        ) as mock_cleanup:
            mock_parser_cls.return_value.parse.return_value = []

            result = await search_service.search(["first", "second"], num_videos=5)

        assert mock_process_query.call_count == 2
        mock_cleanup.assert_awaited_once()
        assert result["totalResults"] == 0
        assert result["query"] == "first second"

    async def test_search_tiktok_without_active_session(self, tiktok_service):
        """Test TikTok search without active session returns error"""
        result = await tiktok_service.search_tiktok("test query")

        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "NOT_LOGGED_IN"
        assert result["error"]["message"] == "TikTok session is not logged in"

    async def test_search_tiktok_with_empty_session(self, tiktok_service):
        """Test TikTok search with empty session returns error"""
        # Set up empty session state
        tiktok_service.active_sessions = {}

        result = await tiktok_service.search_tiktok("test query")

        # Verify error response
        assert "error" in result
        assert result["error"]["code"] == "NOT_LOGGED_IN"
        assert result["error"]["message"] == "TikTok session is not logged in"

    async def test_has_active_session_with_sessions(self, tiktok_service, mock_executor):
        """Test has_active_session returns True when sessions exist"""
        tiktok_service.active_sessions["test_session"] = mock_executor

        result = await tiktok_service.has_active_session()
        assert result is True

    async def test_has_active_session_without_sessions(self, tiktok_service):
        """Test has_active_session returns False when no sessions exist"""
        tiktok_service.active_sessions = {}

        result = await tiktok_service.has_active_session()
        assert result is False

    async def test_get_active_session_with_sessions(self, tiktok_service, mock_executor):
        """Test get_active_session returns session when sessions exist"""
        tiktok_service.active_sessions["test_session"] = mock_executor

        result = await tiktok_service.get_active_session()
        assert result == mock_executor

    async def test_get_active_session_without_sessions(self, tiktok_service):
        """Test get_active_session returns None when no sessions exist"""
        tiktok_service.active_sessions = {}

        result = await tiktok_service.get_active_session()
        assert result is None
