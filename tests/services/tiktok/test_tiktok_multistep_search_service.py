"""Unit tests for TikTok MultiStepSearchService functionality"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.tiktok.search.multistep import (
    TikTokAutoSearchAction,
    TikTokMultiStepSearchService,
)


class TestTikTokMultiStepSearchService:
    """Test TikTok MultiStepSearchService implementation"""

    @pytest.fixture
    def search_service(self):
        """Create a TikTokMultiStepSearchService instance"""
        return TikTokMultiStepSearchService()

    @pytest.fixture
    def mock_context(self):
        """Create a mock search context"""
        return {
            "fetcher": Mock(),
            "composer": Mock(),
            "caps": Mock(),
            "additional_args": {},
            "extra_headers": None,
            "user_data_cleanup": Mock(),
            "options": {}
        }

    def test_service_initialization(self, search_service):
        """Test that service initializes properly"""
        assert search_service.settings is not None
        assert hasattr(search_service, 'logger')

    def test_prepare_context_warns_without_user_data_dir(self, search_service, monkeypatch, caplog):
        """_prepare_context should warn and proceed when camoufox_user_data_dir is missing."""
        settings = search_service.settings
        original_dir = getattr(settings, "camoufox_user_data_dir", None)
        settings.camoufox_user_data_dir = None

        captured_dirs = []

        class DummyBuilder:
            def __init__(self):
                pass

            def build(self, payload, cfg, caps):
                captured_dirs.append(getattr(cfg, "camoufox_user_data_dir", None))
                return {}, None

        monkeypatch.setattr(
            "app.services.common.browser.camoufox.CamoufoxArgsBuilder",
            DummyBuilder,
        )

        with caplog.at_level("WARNING"):
            search_service._prepare_context(in_tests=True)

        settings.camoufox_user_data_dir = original_dir

        assert captured_dirs, "Expected Camoufox builder to run at least once"
        assert all(dir_value is None for dir_value in captured_dirs)
        assert any("camoufox_user_data_dir not configured" in message for message in caplog.messages)

    def test_auto_search_action_initialization(self):
        """Test TikTokAutoSearchAction initialization"""
        action = TikTokAutoSearchAction("test query")
        assert action.search_query == "test query"
        assert action.html_content == ""
        assert action.page is None

    @pytest.mark.asyncio
    async def test_search_validation_error(self, search_service):
        """Test search method returns validation error for invalid input"""
        # Test empty query validation
        result = await search_service.search("", 10, "RELEVANCE", "ALL")
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"

        # Test invalid sort type validation
        result = await search_service.search("test", 10, "INVALID", "ALL")
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_search_success_response_format(self, search_service, mock_context):
        """Test that successful search returns correct response format"""
        # Mock the internal methods to avoid actual browser automation
        with patch.object(search_service, '_prepare_context', return_value=mock_context), \
                patch.object(search_service, '_process_query_with_browser', AsyncMock(return_value=None)), \
                patch.object(search_service, '_cleanup_user_data', AsyncMock()):

            result = await search_service.search("test query", 10, "RELEVANCE", "ALL")

            # Validate response format matches expected schema
            assert "results" in result
            assert "totalResults" in result
            assert "query" in result
            assert isinstance(result["results"], list)
            assert isinstance(result["totalResults"], int)
            assert isinstance(result["query"], str)

    @pytest.mark.asyncio
    async def test_search_error_response_format(self, search_service, mock_context):
        """Test that error responses have correct format"""
        # Mock browser automation to fail
        with patch.object(search_service, '_prepare_context', return_value=mock_context), \
                patch.object(search_service, '_process_query_with_browser', AsyncMock(side_effect=Exception("Browser failed"))), \
                patch.object(search_service, '_cleanup_user_data', AsyncMock()):

            result = await search_service.search("test query", 10, "RELEVANCE", "ALL")

            # Validate error response format
            assert "error" in result
            assert "code" in result["error"]
            assert "message" in result["error"]
            assert "details" in result["error"]
            assert result["error"]["code"] == "BROWSER_AUTOMATION_ERROR"

    @pytest.mark.asyncio
    async def test_multi_query_processing(self, search_service, mock_context):
        """Test processing of multiple queries"""
        with patch.object(search_service, '_prepare_context', return_value=mock_context), \
                patch.object(search_service, '_process_query_with_browser', AsyncMock(return_value=None)), \
                patch.object(search_service, '_cleanup_user_data', AsyncMock()):

            result = await search_service.search(["query1", "query2"], 10, "RELEVANCE", "ALL")

            # Should normalize multiple queries into single string
            assert result["query"] == "query1 query2"

    @pytest.mark.asyncio
    async def test_search_returns_results_from_html(self, search_service, mock_context):
        """Ensure parsed HTML content populates search results."""
        sample_html = (
            "<html><body>"
            "<script id=\"EXTRACTED_SEARCH_ITEMS\">"
            "[{"
            "\"id\": \"1234567890\","
            "\"caption\": \"Sample caption\","
            "\"authorHandle\": \"sample_author\","
            "\"likeCount\": 42,"
            "\"uploadTime\": \"2024-01-01\","
            "\"webViewUrl\": \"https://www.tiktok.com/@sample_author/video/1234567890\""
            "}]"
            "</script>"
            "</body></html>"
        )

        with patch.object(search_service, '_prepare_context', return_value=mock_context), \
                patch.object(search_service, '_execute_browser_search', AsyncMock(return_value=sample_html)), \
                patch.object(search_service, '_cleanup_user_data', AsyncMock()):

            result = await search_service.search("sample query", 5, "RELEVANCE", "ALL")

        assert result["results"], "Expected parsed results from sample HTML"
        assert result["totalResults"] == len(result["results"])
        first_result = result["results"][0]
        assert first_result["id"] == "1234567890"
        assert first_result["webViewUrl"].endswith("/1234567890")

    @pytest.mark.asyncio
    async def test_process_query_uses_remaining_target(self, search_service, mock_context):
        """Search action should request only the remaining videos needed."""
        aggregated = [
            {
                "id": f"existing-{index}",
                "webViewUrl": f"https://www.tiktok.com/@user/video/{index}",
            }
            for index in range(6)
        ]
        seen_ids = {item["id"] for item in aggregated}
        seen_urls = {item["webViewUrl"] for item in aggregated}

        parser = SimpleNamespace(
            parse=Mock(
                return_value=[
                    {
                        "id": f"new-{i}",
                        "webViewUrl": f"https://www.tiktok.com/@user/video/new-{i}",
                    }
                    for i in range(5)
                ]
            )
        )

        with patch.object(
            search_service,
            "_execute_browser_search",
            AsyncMock(return_value="<html></html>"),
        ), patch(
            "app.services.tiktok.search.multistep.TikTokAutoSearchAction"
        ) as mock_action_cls:
            mock_action_instance = Mock()
            mock_action_cls.return_value = mock_action_instance

            result = await search_service._process_query_with_browser(
                query="another",
                index=1,
                total_queries=2,
                parser=parser,
                aggregated=aggregated,
                seen_ids=seen_ids,
                seen_urls=seen_urls,
                target_count=10,
                context=mock_context,
            )

        mock_action_instance.set_target_videos.assert_called_once_with(4)
        assert len(aggregated) == 11, "Expected new results to be appended"
        assert result is True, "Should stop further processing once target reached"

    def test_auto_search_action_cleanup(self):
        """Test TikTokAutoSearchAction cleanup functionality"""
        action = TikTokAutoSearchAction("test query")

        # Mock page object
        mock_page = Mock()
        mock_page.is_closed.return_value = False

        action.page = mock_page
        action._cleanup_browser_resources()

        # Should attempt to close the page
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_cleanup(self, search_service):
        """Test service cleanup functionality"""
        # Add a mock cleanup function
        mock_cleanup = Mock()
        search_service._cleanup_functions.append(mock_cleanup)

        await search_service._cleanup()

        # Cleanup function should be called
        mock_cleanup.assert_called_once()
        # Cleanup functions list should be cleared
        assert len(search_service._cleanup_functions) == 0

    @pytest.mark.asyncio
    async def test_execute_browser_search_mutes_audio(self, search_service, tmp_path, monkeypatch):
        """_execute_browser_search should mute audio via settings during browser launch."""

        settings = search_service.settings
        settings.camoufox_runtime_force_mute_audio = False

        seen_mute_flag = False

        class DummyEngine:
            def __init__(self, *args, **kwargs):
                pass

            def run(self, crawl_request, page_action):
                nonlocal seen_mute_flag
                seen_mute_flag = settings.camoufox_runtime_force_mute_audio
                return SimpleNamespace(html="<html>muted</html>")

        class DummyBrowseExecutor:
            def __init__(self):
                self.fetch_client = Mock()
                self.options_resolver = Mock()
                self.camoufox_builder = Mock()

        @contextmanager
        def fake_user_data_context(*args, **kwargs):
            yield (str(tmp_path), lambda: None)

        monkeypatch.setattr(
            "app.services.tiktok.search.multistep.CrawlerEngine",
            lambda *args, **kwargs: DummyEngine(),
        )
        monkeypatch.setattr(
            "app.services.browser.executors.browse_executor.BrowseExecutor",
            lambda: DummyBrowseExecutor(),
        )
        monkeypatch.setattr(
            "app.services.tiktok.search.multistep.user_data_context",
            fake_user_data_context,
        )

        search_action = SimpleNamespace(html_content="fallback")
        html = await search_service._execute_browser_search(search_action, context={"options": {}})

        assert html == "<html>muted</html>"
        assert seen_mute_flag is True
        assert settings.camoufox_runtime_force_mute_audio is False

    @pytest.mark.asyncio
    async def test_fetch_html_not_implemented(self, search_service, mock_context):
        """Test that _fetch_html raises NotImplementedError"""
        with pytest.raises(NotImplementedError):
            await search_service._fetch_html("test", context=mock_context)

    def test_response_schema_compatibility(self):
        """Test that response format is compatible with TikTokSearchResponse schema"""
        # This test ensures our service returns data that matches the expected schema
        from app.schemas.tiktok.search import TikTokSearchResponse

        # Create a sample response that matches our service's format
        sample_response = {
            "results": [],
            "totalResults": 0,
            "query": "test query"
        }

        # Should validate successfully against the schema
        validated = TikTokSearchResponse(**sample_response)
        assert validated.results == []
        assert validated.totalResults == 0
        assert validated.query == "test query"
