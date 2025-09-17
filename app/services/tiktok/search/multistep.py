"""TikTok multi-step search service with browser automation."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

from app.services.tiktok.search.abstract import AbstractTikTokSearchService
from app.services.tiktok.parser.orchestrator import TikTokSearchParser
from app.schemas.crawl import CrawlRequest
from app.services.common.engine import CrawlerEngine
from app.services.browser.executors.browse_executor import BrowseExecutor
from app.services.tiktok.search.actions.auto_search import TikTokAutoSearchAction
from app.services.tiktok.protocols import SearchContext


class TikTokMultiStepSearchService(AbstractTikTokSearchService):
    """Multi-step TikTok search service using browser automation for search interaction."""

    def __init__(self) -> None:
        super().__init__()
        self._cleanup_functions: List[Callable] = []

    async def search(
        self,
        query: Union[str, List[str]],
        num_videos: int = 50,
        sort_type: str = "RELEVANCE",
        recency_days: str = "ALL",
    ) -> Dict[str, Any]:
        """Execute a TikTok search using browser automation and return structured results."""
        try:
            self.logger.debug(
                f"[TikTokMultiStepSearchService] Starting search - query: {query}, "
                f"num_videos: {num_videos}, sort_type: {sort_type}, recency_days: {recency_days}"
            )

            # Validate request parameters
            queries_or_error = self._validate_request(query=query, sort_type=sort_type)
            if isinstance(queries_or_error, dict):
                return queries_or_error
            queries: List[str] = list(queries_or_error)

            in_tests = self._is_tests_env()
            self.logger.debug(f"[TikTokMultiStepSearchService] Test environment: {in_tests}")
            context = self._prepare_context(in_tests=in_tests)
            user_data_cleanup = context["user_data_cleanup"]

            # Register cleanup function
            if user_data_cleanup:
                self._cleanup_functions.append(user_data_cleanup)

            from app.services.tiktok.parser.orchestrator import TikTokSearchParser  # no-hoist
            parser = TikTokSearchParser()

            aggregated: List[Dict[str, Any]] = []
            seen_ids: Set[str] = set()
            seen_urls: Set[str] = set()

            self.logger.debug(f"[TikTokMultiStepSearchService] Starting browser automation for {len(queries)} queries")
            target_count = int(num_videos)

            for index, normalized_query in enumerate(queries):
                maybe_stop = await self._process_query_with_browser(
                    query=normalized_query,
                    index=index,
                    total_queries=len(queries),
                    parser=parser,
                    aggregated=aggregated,
                    seen_ids=seen_ids,
                    seen_urls=seen_urls,
                    target_count=target_count,
                    context=context,
                )
                should_stop = await maybe_stop if inspect.isawaitable(maybe_stop) else maybe_stop
                if should_stop is True:
                    break

            limit = max(0, min(int(num_videos), 50))
            final_results = aggregated[:limit]
            normalized_query = " ".join(queries)

            self.logger.debug(
                f"[TikTokMultiStepSearchService] Final results - total_aggregated: {len(aggregated)}, "
                f"limit: {limit}, final_results: {len(final_results)}"
            )
            self.logger.debug(f"[TikTokMultiStepSearchService] Normalized query: '{normalized_query}'")

            result = {"results": final_results, "totalResults": len(final_results), "query": normalized_query}
            self.logger.debug(f"[TikTokMultiStepSearchService] Returning search result with {len(final_results)} videos")
            return result

        except Exception as e:
            self.logger.error(
                f"[TikTokMultiStepSearchService] Search operation failed: {e}",
                exc_info=True,
            )
            # Return error response that matches the expected format
            return {
                "error": {
                    "code": "BROWSER_AUTOMATION_ERROR",
                    "message": f"Browser automation failed: {str(e)}",
                    "details": {"query": query if isinstance(query, str) else " ".join(query)}
                }
            }
        finally:
            # Always execute cleanup
            await self._cleanup()

    async def _process_query_with_browser(
        self,
        *,
        query: str,
        index: int,
        total_queries: int,
        parser: Any,
        aggregated: List[Dict[str, Any]],
        seen_ids: Set[str],
        seen_urls: Set[str],
        target_count: int,
        context: SearchContext,
    ) -> Optional[bool]:
        """Process a single query using browser automation."""
        self.logger.debug(
            f"[TikTokMultiStepSearchService] Processing query {index + 1}/{total_queries}: '{query}'"
        )

        try:
            # Use browser automation to perform the search
            search_action = TikTokAutoSearchAction(query)

            # Execute the search using browser automation
            html_content = await self._execute_browser_search(search_action, context)

            if not html_content:
                self.logger.warning(
                    f"[TikTokMultiStepSearchService] No HTML content captured for query '{query}'"
                )
                return None

            # Parse the HTML content
            items = parser.parse(html_content) or []
            self.logger.debug(
                f"[TikTokMultiStepSearchService] Extracted {len(items)} video items from HTML for query '{query}'"
            )

            # Deduplicate and aggregate results
            for item in items:
                vid = str(item.get("id", "") or "")
                url = str(item.get("webViewUrl", "") or "")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    if url:
                        seen_urls.add(url)
                    aggregated.append(item)
                elif (not vid) and url and (url not in seen_urls):
                    seen_urls.add(url)
                    aggregated.append(item)

            self.logger.debug(
                f"[TikTokMultiStepSearchService] After processing query '{query}': {len(aggregated)} total videos, "
                f"{len(seen_ids)} unique IDs, {len(seen_urls)} unique URLs"
            )

            should_stop = len(aggregated) >= target_count
            if should_stop:
                self.logger.debug(
                    f"[TikTokMultiStepSearchService] Reached target video count ({target_count}), breaking from search loop"
                )
            return True if should_stop else None

        except Exception as e:
            self.logger.error(
                f"[TikTokMultiStepSearchService] Exception processing query '{query}': {e}",
                exc_info=True,
            )
            # Continue processing other queries even if one fails
            return None

    async def _execute_browser_search(self, search_action: TikTokAutoSearchAction, context: SearchContext) -> str:
        """Execute browser search and return HTML content."""
        try:
            # Use the existing browser infrastructure
            from app.services.browser.executors.browse_executor import BrowseExecutor

            browse_executor = BrowseExecutor()
            engine = CrawlerEngine(
                executor=browse_executor,
                fetch_client=browse_executor.fetch_client,
                options_resolver=browse_executor.options_resolver,
                camoufox_builder=browse_executor.camoufox_builder
            )

            # Create crawl request with appropriate settings
            crawl_request = CrawlRequest(
                url="https://www.tiktok.com/",
                force_headful=False,  # Headless mode for automation
                force_user_data=True,
                timeout_seconds=120,  # Longer timeout for browser automation
                wait_for_network_idle=True,
            )

            # Execute the search with timeout protection
            try:
                result = await asyncio.wait_for(
                    engine.run(crawl_request, search_action),
                    timeout=180  # 3 minute timeout for browser automation
                )
            except asyncio.TimeoutError:
                self.logger.warning("Browser search timed out after 3 minutes")
                return ""

            # Return the captured HTML content
            return search_action.html_content

        except Exception as e:
            self.logger.error(f"[TikTokMultiStepSearchService] Browser search execution failed: {e}", exc_info=True)
            return ""

    async def _cleanup(self):
        """Execute all registered cleanup functions."""
        for cleanup_func in self._cleanup_functions:
            try:
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                elif callable(cleanup_func):
                    cleanup_func()
            except Exception as e:
                self.logger.warning(f"Cleanup function failed: {e}")
        self._cleanup_functions.clear()

    async def _fetch_html(self, query: str, *, context: SearchContext) -> Tuple[int, str]:
        """Fetch HTML for a search query - not used in multi-step approach."""
        # Multi-step search uses browser automation instead of direct HTML fetching
        raise NotImplementedError("Multi-step search uses browser automation, not direct HTML fetching")
