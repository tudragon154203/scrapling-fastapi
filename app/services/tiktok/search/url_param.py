"""URL-parameter based TikTok search service implementation."""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import quote_plus

from app.services.tiktok.search.abstract import AbstractTikTokSearchService
from app.services.tiktok.protocols import SearchContext


class TikTokURLParamSearchService(AbstractTikTokSearchService):
    """Search service that builds TikTok queries using URL parameters."""

    def __init__(self):
        super().__init__()

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
        queries: List[str] = list(queries_or_error)

        in_tests = self._is_tests_env()
        self.logger.debug(f"[TikTokSearchService] Test environment: {in_tests}")
        context = self._prepare_context(in_tests=in_tests)
        user_data_cleanup = context["user_data_cleanup"]

        from app.services.tiktok.parser.orchestrator import TikTokSearchParser  # no-hoist

        parser = TikTokSearchParser()
        aggregated: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        seen_urls: Set[str] = set()
        base_url = str(self.settings.tiktok_url or "https://www.tiktok.com/").rstrip("/")
        self.logger.debug(f"[TikTokSearchService] Base URL: {base_url}")
        self.logger.debug(f"[TikTokSearchService] Starting fetch loop for {len(queries)} queries")
        target_count = int(num_videos)
        for index, normalized_query in enumerate(queries):
            maybe_stop = self._process_query(
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

        await self._cleanup_user_data(user_data_cleanup)
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

    async def _process_query(
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
        self.logger.debug(
            f"[TikTokSearchService] Processing query {index + 1}/{total_queries}: '{query}'"
        )
        try:
            status_code, html = await self._fetch_html(query, context=context)
            if status_code < 200 or status_code >= 300 or not html:
                self.logger.warning(
                    f"[TikTokSearchService] Invalid response for query '{query}': "
                    f"status={status_code}, html_length={len(html)}"
                )
                return None
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
            return True if should_stop else None
        except Exception as e:
            self.logger.error(
                f"[TikTokSearchService] Exception processing query '{query}': {e}",
                exc_info=True,
            )
            return None

    async def _fetch_html(self, query: str, *, context: SearchContext) -> Tuple[int, str]:
        fetcher = context["fetcher"]
        composer = context["composer"]
        caps = context["caps"]
        additional_args = context["additional_args"]
        extra_headers = context["extra_headers"]
        options = context["options"]

        base_url = str(self.settings.tiktok_url or "https://www.tiktok.com/").rstrip("/")
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
        return status_code, html
