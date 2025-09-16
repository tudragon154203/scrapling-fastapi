"""
TikTok search service extracted from TiktokService for clarity and reuse.
OOP interface: TikTokSearchService(service).search(...)
The 'service' parameter is the TiktokService instance providing settings and session helpers.
"""
from __future__ import annotations
import os
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast
import asyncio
import sys
from urllib.parse import quote_plus

# Project-internal imports are intentionally lazy-loaded in methods to
# avoid circular imports and heavy dependencies at module import time.


class TikTokSearchService:
    def __init__(self, service: Any):
        self.service = service
        self.settings = service.settings
        self.logger = logging.getLogger(__name__)

    async def search(
        self,
        query: Union[str, List[str]],
        num_videos: int = 50,
        sort_type: str = "RELEVANCE",
        recency_days: str = "ALL",
    ) -> Dict[str, Any]:
        self.logger.debug(
            f"[TikTokSearchService] Starting search - query: {query}, "
            f"num_videos: {num_videos}, sort_type: {sort_type}, recency_days: {recency_days}"
        )
        queries_or_error = self._validate_request(query=query, sort_type=sort_type)
        if isinstance(queries_or_error, dict):
            return queries_or_error
        queries: List[str] = queries_or_error

        in_tests = self._is_tests_env()
        self.logger.debug(f"[TikTokSearchService] Test environment: {in_tests}")
        context = self._prepare_context(in_tests=in_tests)

        # Defer parser import to avoid circular imports at module load
        from app.services.tiktok.parser.orchestrator import TikTokSearchParser  # no-hoist

        parser = TikTokSearchParser()
        aggregated: List[Dict[str, Any]] = []
        seen_ids: set = set()
        seen_urls: set = set()
        base_url = str(self.settings.tiktok_url or "https://www.tiktok.com/").rstrip("/")
        self.logger.debug(f"[TikTokSearchService] Base URL: {base_url}")
        self.logger.debug(f"[TikTokSearchService] Starting fetch loop for {len(queries)} queries")
        target_count = int(num_videos)
        for index, normalized_query in enumerate(queries):
            should_stop = self._process_query(
                query=normalized_query,
                index=index,
                total_queries=len(queries),
                base_url=base_url,
                parser=parser,
                aggregated=aggregated,
                seen_ids=seen_ids,
                seen_urls=seen_urls,
                target_count=target_count,
                context=context,
            )
            if should_stop:
                break

        # Skip detail-page enrichment; rely solely on search-page HTML like demo
        await self._cleanup_user_data(context.get("user_data_cleanup"))
        limit = max(0, min(int(num_videos), 50))
        final_results = aggregated[:limit]
        normalized_query = " ".join(queries)
        self.logger.debug(
            f"[TikTokSearchService] Final results - total_aggregated: {len(aggregated)}, "
            f"limit: {limit}, final_results: {len(final_results)}"
        )
        self.logger.debug(f"[TikTokSearchService] Normalized query: '{normalized_query}'")
        result = {"results": final_results, "totalResults": len(final_results), "query": normalized_query}
        self.logger.debug(f"[TikTokSearchService] Returning search result with {len(final_results)} videos")
        return result
    # Helpers

    def _is_tests_env(self) -> bool:
        return bool(os.environ.get("PYTEST_CURRENT_TEST"))

    def _enforce_sort_type(self, sort_type: Optional[str]) -> Optional[Dict[str, Any]]:
        self.logger.debug(f"[TikTokSearchService] Enforcing sort_type: {sort_type}")
        if str(sort_type or "").upper() == "RELEVANCE":
            self.logger.debug("[TikTokSearchService] Sort type validated: RELEVANCE")
            return None
        self.logger.warning(f"[TikTokSearchService] Sort type validation failed for: {sort_type}")
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Unsupported sortType; only RELEVANCE is supported",
                "fields": {"sortType": "Must be 'RELEVANCE'"},
            }
        }

    def _normalize_queries(self, query: Union[str, List[str]]) -> Tuple[bool, Union[List[str], Dict[str, Any]]]:
        self.logger.debug(f"[TikTokSearchService] Normalizing query type: {type(query)}")
        if isinstance(query, list):
            queries = [str(x).strip() for x in query if str(x or "").strip()]
            self.logger.debug(f"[TikTokSearchService] Filtered query list from {len(query)} to {len(queries)} items")
            if not queries:
                self.logger.warning("[TikTokSearchService] Empty query list after filtering")
                return False, {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Query array cannot be empty",
                        "fields": {"query": "Provide at least one non-empty string"},
                    }
                }
            return True, queries
        self.logger.debug(f"[TikTokSearchService] Processing single query: {query}")
        q = str(query or "").strip()
        if not q:
            self.logger.warning(f"[TikTokSearchService] Empty query after normalization: '{query}'")
            return False, {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters",
                    "fields": {"query": "Query cannot be empty"},
                }
            }
        return True, [q]

    def _validate_request(
        self,
        query: Union[str, List[str]],
        sort_type: Optional[str],
    ) -> Union[List[str], Dict[str, Any]]:
        self.logger.debug(f"[TikTokSearchService] Checking sort_type: {sort_type}")
        err = self._enforce_sort_type(sort_type)
        if err is not None:
            self.logger.warning(f"[TikTokSearchService] Sort type validation failed: {err}")
            return err
        self.logger.debug(f"[TikTokSearchService] Normalizing query: {query}")
        ok, queries_or_err = self._normalize_queries(query)
        if not ok:
            self.logger.warning(f"[TikTokSearchService] Query normalization failed: {queries_or_err}")
            return queries_or_err
        queries = cast(List[str], queries_or_err)
        self.logger.debug(f"[TikTokSearchService] Normalized queries: {queries}")
        return queries

    def _prepare_context(self, in_tests: bool) -> Dict[str, Any]:
        from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter, FetchArgComposer
        from app.services.common.browser.camoufox import CamoufoxArgsBuilder
        self.logger.debug(
            f"[TikTokSearchService] Preparing fetch context for independent search - in_tests: {in_tests}")
        # Ensure proper event loop policy on Windows for Playwright/Scrapling
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                self.logger.debug(
                    "[TikTokSearchService] Set WindowsProactorEventLoopPolicy for Scrapling compatibility")
            except Exception as e:
                self.logger.warning(f"[TikTokSearchService] Failed to set Windows event loop policy: {e}")
        settings = self.settings
        fetcher = ScraplingFetcherAdapter()
        composer = FetchArgComposer()
        camoufox_builder = CamoufoxArgsBuilder()
        caps = fetcher.detect_capabilities()
        self.logger.debug(f"[TikTokSearchService] Detected capabilities: {caps}")
        try:
            _, extra_headers = camoufox_builder.build(type("Mock", (), {"force_user_data": False})(), settings, caps)
            self.logger.debug("[TikTokSearchService] Built base headers for non-force_user_data")
        except Exception as e:
            self.logger.warning(f"[TikTokSearchService] Failed to build base headers: {e}")
            extra_headers = None
        user_data_cleanup = None
        additional_args = {}
        try:
            payload = type("Mock", (), {"force_user_data": True})()
            additional_args, extra_headers2 = camoufox_builder.build(payload, settings, caps)
            self.logger.debug(
                f"[TikTokSearchService] Built additional args for forced user data: {len(additional_args)} args")
            if extra_headers is None and extra_headers2 is not None:
                extra_headers = extra_headers2
                self.logger.debug("[TikTokSearchService] Updated extra headers from camoufox build")
            user_data_cleanup = additional_args.get("_user_data_cleanup")
            if user_data_cleanup:
                self.logger.debug("[TikTokSearchService] Set up user_data_cleanup function")
        except Exception as e:
            self.logger.error(f"[TikTokSearchService] Failed to build additional args: {e}", exc_info=True)
            additional_args = {}
        # headless_opt = False
        headless_opt = True if in_tests else False
        self.logger.debug(f"[TikTokSearchService] Headless mode set to: {headless_opt}")
        # Wait for richer signals so parser can extract full info
        # - Prefer script#SIGI_STATE (structured JSON)
        # - Fallback to visible search items with links
        options = {
            "headless": headless_opt,
            "network_idle": True,
            # Focus on visible link targets on search page; script capture handled on detail pages
            "wait_for_selector": (
                "[data-e2e='search_video-item'] a[href*='/video/'], "
                "[data-e2e='search_top-item'] a[href*='/video/'], "
                "[data-e2e='search-card-video-caption'], "
                "[data-e2e='search-card-desc']"
            ),
            "wait_for_selector_state": "visible",
            "timeout_seconds": 45,
        }
        self.logger.debug(f"[TikTokSearchService] Fetch options: {options}")
        self.logger.debug(
            f"[TikTokSearchService] Extra headers: {extra_headers is not None}, "
            f"User data cleanup: {user_data_cleanup is not None}"
        )
        return {
            "fetcher": fetcher,
            "composer": composer,
            "caps": caps,
            "additional_args": additional_args,
            "extra_headers": extra_headers,
            "user_data_cleanup": user_data_cleanup,
            "options": options,
        }

    def _process_query(
        self,
        *,
        query: str,
        index: int,
        total_queries: int,
        base_url: str,
        parser: Any,
        aggregated: List[Dict[str, Any]],
        seen_ids: set,
        seen_urls: set,
        target_count: int,
        context: Dict[str, Any],
    ) -> bool:
        self.logger.debug(
            f"[TikTokSearchService] Processing query {index + 1}/{total_queries}: '{query}'"
        )
        try:
            fetcher = context["fetcher"]
            composer = context["composer"]
            caps = context["caps"]
            additional_args = context["additional_args"]
            extra_headers = context["extra_headers"]
            options = context["options"]
            search_url = f"{base_url}/search/video?q={quote_plus(query)}"
            self.logger.debug(f"[TikTokSearchService] Search URL: {search_url}")
            fetch_kwargs = composer.compose(
                options=options,
                caps=caps,
                selected_proxy=getattr(self.settings, "private_proxy_url", None) or None,
                additional_args=additional_args,
                extra_headers=extra_headers,
                settings=self.settings,
                page_action=None,
            )
            self.logger.debug(f"[TikTokSearchService] Fetch kwargs prepared with options: {options}")
            page = fetcher.fetch(search_url, fetch_kwargs)
            status_code = int(getattr(page, "status", 0) or 0)
            html = getattr(page, "html_content", "") or ""
            if self.logger.level <= logging.DEBUG:
                try:
                    self.logger.debug("[TikTokSearchService] Exporting HTML to tiktok_search.html")
                    file_path = os.path.join(os.getcwd(), "tiktok_search.html")
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    self.logger.debug("[TikTokSearchService] Raw HTML exported to tiktok_search.html")
                except Exception as e:
                    self.logger.warning(f"[TikTokSearchService] Failed to export raw HTML: {e}")
            self.logger.debug(
                f"[TikTokSearchService] Fetch result - status_code: {status_code}, "
                f"html_length: {len(html)}"
            )
            if status_code < 200 or status_code >= 300 or not html:
                self.logger.warning(
                    f"[TikTokSearchService] Invalid response for query '{query}': "
                    f"status={status_code}, html_length={len(html)}"
                )
                return False
            items = parser.parse(html) or []
            self.logger.debug(
                f"[TikTokSearchService] Extracted {len(items)} video items from HTML for query '{query}'"
            )
            if items:
                self.logger.debug(f"[TikTokSearchService] First item sample: {items[0]}")
            else:
                self.logger.debug(
                    f"[TikTokSearchService] No items extracted from HTML, HTML length: {len(html)}"
                )
                if len(html) > 1000:
                    self.logger.debug(f"[TikTokSearchService] HTML sample: {html[:1000]}...")
                else:
                    self.logger.debug(f"[TikTokSearchService] HTML content: {html}")
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
                f"[TikTokSearchService] After processing query '{query}': {len(aggregated)} total videos, "
                f"{len(seen_ids)} unique IDs, {len(seen_urls)} unique URLs"
            )
            should_stop = len(aggregated) >= target_count
            if should_stop:
                self.logger.debug(
                    f"[TikTokSearchService] Reached target video count ({target_count}), breaking from search loop"
                )
            return should_stop
        except Exception as e:
            self.logger.error(
                f"[TikTokSearchService] Exception processing query '{query}': {e}",
                exc_info=True,
            )
            return False

    async def _cleanup_user_data(self, cleanup_callable: Optional[Callable[[], None]]) -> None:
        if not callable(cleanup_callable):
            return
        self.logger.debug("[TikTokSearchService] Calling user_data_cleanup function")
        try:
            await asyncio.sleep(3)
            cleanup_callable()
            self.logger.debug("[TikTokSearchService] User data cleanup completed successfully")
        except Exception as e:
            self.logger.error(
                f"[TikTokSearchService] User data cleanup failed: {e}",
                exc_info=True,
            )
    # No detail enrichment or page_action injection; operate like demo on search page only
