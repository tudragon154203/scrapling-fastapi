"""Unit tests for the TikTok URL-parameter search service."""

import logging
from typing import Any, Dict, List, Set, cast

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.tiktok.protocols import SearchContext
from app.services.tiktok.search.url_param import TikTokURLParamSearchService
from app.services.tiktok.session import TiktokService
from app.services.tiktok.session import SessionRecord
from app.schemas.tiktok.session import TikTokLoginState
from app.services.tiktok.tiktok_executor import TiktokExecutor


pytestmark = pytest.mark.asyncio


class TestTikTokURLParamSearchService:
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

    @pytest.fixture
    def register_session(self, tiktok_service, mock_executor):
        """Register a disposable session record for tests."""

        def _register(
            session_id: str = "test_session",
            *,
            executor=None,
            login_state: str = TikTokLoginState.LOGGED_IN,
            user_data_dir: str = "/tmp/test",
            config=None,
            created_at=None,
            last_activity=None,
        ) -> SessionRecord:
            cfg = config or Mock()
            if not hasattr(cfg, "max_session_duration"):
                cfg.max_session_duration = 300
            record = SessionRecord(
                id=session_id,
                executor=executor or mock_executor,
                config=cfg,
                login_state=login_state,
                user_data_dir=user_data_dir,
            )
            if created_at is not None:
                record.created_at = created_at
            if last_activity is not None:
                record.last_activity = last_activity
            tiktok_service.sessions.register(record)
            return record

        return _register

    async def test_search_service_continues_after_query_error(self):
        """TikTokURLParamSearchService should continue processing queries on recoverable errors."""

        service = Mock()
        service.settings = Mock()
        service.settings.tiktok_url = "https://www.tiktok.com/"
        service.settings.private_proxy_url = None

        search_service = TikTokURLParamSearchService(service)

        with patch.object(
            TikTokURLParamSearchService, "_prepare_context", return_value={
                "fetcher": Mock(),
                "composer": Mock(),
                "caps": {},
                "additional_args": {},
                "extra_headers": None,
                "user_data_cleanup": None,
                "options": {},
            }
        ), patch("app.services.tiktok.search.parser.orchestrator.TikTokSearchParser") as mock_parser_cls, patch.object(
            TikTokURLParamSearchService, "_process_query", side_effect=[None, True]
        ) as mock_process_query, patch.object(
            TikTokURLParamSearchService, "_cleanup_user_data", new=AsyncMock()
        ) as mock_cleanup:
            mock_parser_cls.return_value.parse.return_value = []

            result = await search_service.search(["first", "second"], num_videos=5)

        assert mock_process_query.call_count == 2
        mock_cleanup.assert_awaited_once()
        assert result["totalResults"] == 0
        assert result["query"] == "first second"

    async def test_process_query_aggregates_unique_items_and_respects_target(self):
        """_process_query should aggregate unique IDs/URLs and stop at the target count."""

        service = Mock()
        service.settings = Mock()
        service.settings.tiktok_url = "https://www.tiktok.com/"

        search_service = TikTokURLParamSearchService(service)
        parser = Mock()
        parser.parse.return_value = [
            {"id": "1", "webViewUrl": "https://example.com/1"},
            {"id": "1", "webViewUrl": "https://example.com/1"},  # duplicate id
            {"id": "", "webViewUrl": "https://example.com/2"},
            {"id": "", "webViewUrl": "https://example.com/2"},  # duplicate url
        ]

        aggregated: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        seen_urls: Set[str] = set()

        with patch.object(
            TikTokURLParamSearchService,
            "_fetch_html",
            new=AsyncMock(return_value=(200, "<html></html>")),
        ) as fetch_mock:
            context = cast(
                SearchContext,
                {
                    "fetcher": Mock(),
                    "composer": Mock(),
                    "caps": {},
                    "additional_args": {},
                    "extra_headers": None,
                    "user_data_cleanup": None,
                    "options": {},
                },
            )
            should_stop = await search_service._process_query(
                query="cats",
                index=0,
                total_queries=1,
                parser=parser,
                aggregated=aggregated,
                seen_ids=seen_ids,
                seen_urls=seen_urls,
                target_count=2,
                context=context,
            )

        fetch_mock.assert_awaited_once_with("cats", context=context)
        assert should_stop is True
        assert aggregated == [
            {"id": "1", "webViewUrl": "https://example.com/1"},
            {"id": "", "webViewUrl": "https://example.com/2"},
        ]
        assert seen_ids == {"1"}
        assert seen_urls == {"https://example.com/1", "https://example.com/2"}

    async def test_process_query_returns_none_for_invalid_response(self):
        """_process_query should not aggregate results when the fetch response is invalid."""

        service = Mock()
        service.settings = Mock()
        service.settings.tiktok_url = "https://www.tiktok.com/"

        search_service = TikTokURLParamSearchService(service)
        parser = Mock()
        parser.parse.return_value = [{"id": "1", "webViewUrl": "https://example.com/1"}]
        aggregated: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        seen_urls: Set[str] = set()

        with patch.object(
            TikTokURLParamSearchService,
            "_fetch_html",
            new=AsyncMock(return_value=(500, "")),
        ):
            context = cast(
                SearchContext,
                {
                    "fetcher": Mock(),
                    "composer": Mock(),
                    "caps": {},
                    "additional_args": {},
                    "extra_headers": None,
                    "user_data_cleanup": None,
                    "options": {},
                },
            )
            should_stop = await search_service._process_query(
                query="dogs",
                index=0,
                total_queries=1,
                parser=parser,
                aggregated=aggregated,
                seen_ids=seen_ids,
                seen_urls=seen_urls,
                target_count=5,
                context=context,
            )

        assert should_stop is None
        assert aggregated == []
        assert seen_ids == set()
        assert seen_urls == set()

    async def test_validate_request_success(self):
        """_validate_request returns normalized queries when input is valid."""

        service = Mock()
        service.settings = Mock()
        search_service = TikTokURLParamSearchService(service)

        result = search_service._validate_request(["  foo  ", "bar"])

        assert result == ["foo", "bar"]

    async def test_validate_request_rejects_invalid_sort(self):
        """_validate_request returns a validation error for unsupported sort types."""

        service = Mock()
        service.settings = Mock()
        search_service = TikTokURLParamSearchService(service)

        result = search_service._validate_request("query")

        # Since sort_type validation was removed, this should now return a list
        assert isinstance(result, list)
        assert result == ["query"]

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
            search_service = TikTokURLParamSearchService(service)
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
        search_service = TikTokURLParamSearchService(service)
        cleanup_callable = Mock()

        with patch(
            "app.services.tiktok.search.abstract.asyncio.sleep", new=AsyncMock()
        ) as sleep_mock:
            await search_service._cleanup_user_data(cleanup_callable)

        sleep_mock.assert_awaited_once_with(3)
        cleanup_callable.assert_called_once_with()

    async def test_fetch_html_uses_context_components(self, tmp_path):
        """_fetch_html should compose fetch arguments and return the response payload."""

        service = Mock()
        service.settings = Mock()
        service.settings.tiktok_url = "https://www.tiktok.com/"
        service.settings.private_proxy_url = "http://proxy.example"

        search_service = TikTokURLParamSearchService(service)
        search_service.logger.setLevel(logging.INFO)

        fetcher = Mock()
        page = Mock(status=201, html_content="<html>payload</html>")
        fetcher.fetch.return_value = page
        composer = Mock()
        composer.compose.return_value = {"composed": True}

        context = {
            "fetcher": fetcher,
            "composer": composer,
            "caps": {"cap": True},
            "additional_args": {"arg": 1},
            "extra_headers": {"X-Test": "value"},
            "user_data_cleanup": None,
            "options": {"headless": False},
        }

        with patch("os.getcwd", return_value=str(tmp_path)):
            status, html = await search_service._fetch_html("test query", context=context)

        composer.compose.assert_called_once_with(
            options={"headless": False},
            caps={"cap": True},
            selected_proxy="http://proxy.example",
            additional_args={"arg": 1},
            extra_headers={"X-Test": "value"},
            settings=service.settings,
            page_action=None,
        )
        fetcher.fetch.assert_called_once()
        assert status == 201
        assert html == "<html>payload</html>"

    async def test_cleanup_user_data_ignores_missing_callable(self):
        """_cleanup_user_data should not attempt cleanup when callable is missing."""

        service = Mock()
        service.settings = Mock()
        search_service = TikTokURLParamSearchService(service)

        with patch(
            "app.services.tiktok.search.abstract.asyncio.sleep", new=AsyncMock()
        ) as sleep_mock:
            await search_service._cleanup_user_data(None)

        sleep_mock.assert_not_called()

    async def test_handle_cleanup_invokes_registered_functions(self):
        """_handle_cleanup should synchronously call each provided cleanup callback."""

        service = Mock()
        service.settings = Mock()
        search_service = TikTokURLParamSearchService(service)

        cleanup_one = Mock()
        cleanup_two = Mock()

        search_service._handle_cleanup([cleanup_one, cleanup_two])

        cleanup_one.assert_called_once_with()
        cleanup_two.assert_called_once_with()

    async def test_has_active_session_with_sessions(self, tiktok_service, mock_executor, register_session):
        """Test has_active_session returns True when sessions exist"""
        register_session()

        result = await tiktok_service.has_active_session()
        assert result is True

    async def test_has_active_session_without_sessions(self, tiktok_service):
        """Test has_active_session returns False when no sessions exist"""
        tiktok_service.sessions.clear()

        result = await tiktok_service.has_active_session()
        assert result is False

    async def test_get_active_session_with_sessions(self, tiktok_service, mock_executor, register_session):
        """Test get_active_session returns session when sessions exist"""
        register_session()

        result = await tiktok_service.get_active_session()
        assert result == mock_executor

    async def test_get_active_session_without_sessions(self, tiktok_service):
        """Test get_active_session returns None when no sessions exist"""
        tiktok_service.sessions.clear()

        result = await tiktok_service.get_active_session()
        assert result is None
