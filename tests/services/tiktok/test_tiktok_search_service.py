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

    async def test_validate_request_success(self):
        """_validate_request returns normalized queries when input is valid."""

        service = Mock()
        service.settings = Mock()
        search_service = TikTokSearchService(service)

        result = search_service._validate_request(["  foo  ", "bar"], sort_type="RELEVANCE")

        assert result == ["foo", "bar"]

    async def test_validate_request_rejects_invalid_sort(self):
        """_validate_request returns a validation error for unsupported sort types."""

        service = Mock()
        service.settings = Mock()
        search_service = TikTokSearchService(service)

        result = search_service._validate_request("query", sort_type="TRENDING")

        assert isinstance(result, dict)
        assert result["error"]["code"] == "VALIDATION_ERROR"

    async def test_prepare_context_builds_expected_components(self):
        """_prepare_context should assemble the fetch context without invoking real network calls."""

        service = Mock()
        service.settings = Mock()
        cleanup_callable = Mock()
        fetcher = Mock()
        fetcher.detect_capabilities.return_value = {"supports": True}
        composer = Mock()
        camoufox = Mock()
        camoufox.build.side_effect = [
            ({}, {"X-Test": "base"}),
            ({"_user_data_cleanup": cleanup_callable, "other": "value"}, {"X-Test": "forced"}),
        ]

        with patch(
            "app.services.common.adapters.scrapling_fetcher.ScraplingFetcherAdapter",
            return_value=fetcher,
        ) as mock_fetcher_cls, patch(
            "app.services.common.adapters.scrapling_fetcher.FetchArgComposer",
            return_value=composer,
        ) as mock_composer_cls, patch(
            "app.services.common.browser.camoufox.CamoufoxArgsBuilder",
            return_value=camoufox,
        ) as mock_builder_cls:
            search_service = TikTokSearchService(service)
            context = search_service._prepare_context(in_tests=True)

        mock_fetcher_cls.assert_called_once_with()
        mock_composer_cls.assert_called_once_with()
        mock_builder_cls.assert_called_once_with()
        fetcher.detect_capabilities.assert_called_once_with()
        assert context["fetcher"] is fetcher
        assert context["composer"] is composer
        assert context["caps"] == {"supports": True}
        assert context["additional_args"] == {"_user_data_cleanup": cleanup_callable, "other": "value"}
        assert context["extra_headers"] == {"X-Test": "base"}
        assert context["user_data_cleanup"] is cleanup_callable
        assert context["options"]["headless"] is True

    async def test_cleanup_user_data_invokes_callable(self):
        """_cleanup_user_data waits before calling a provided cleanup function."""

        service = Mock()
        service.settings = Mock()
        search_service = TikTokSearchService(service)
        cleanup_callable = Mock()

        with patch(
            "app.services.tiktok.search_service.asyncio.sleep", new=AsyncMock()
        ) as sleep_mock:
            await search_service._cleanup_user_data(cleanup_callable)

        sleep_mock.assert_awaited_once_with(3)
        cleanup_callable.assert_called_once_with()

    async def test_cleanup_user_data_ignores_missing_callable(self):
        """_cleanup_user_data should not attempt cleanup when callable is missing."""

        service = Mock()
        service.settings = Mock()
        search_service = TikTokSearchService(service)

        with patch(
            "app.services.tiktok.search_service.asyncio.sleep", new=AsyncMock()
        ) as sleep_mock:
            await search_service._cleanup_user_data(None)

        sleep_mock.assert_not_called()

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
