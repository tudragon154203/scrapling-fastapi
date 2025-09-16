"""Abstract helpers for TikTok search services."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from app.services.tiktok.interfaces import TikTokSearchStrategy
from app.services.tiktok.protocols import CleanupCallable, SearchContext


class AbstractTikTokSearchService(ABC, TikTokSearchStrategy):
    """Base class containing reusable helpers for TikTok search services."""

    def __init__(self, service: Any) -> None:
        self.service = service
        self.settings = service.settings
        self.logger = logging.getLogger(self.__class__.__module__)

    @abstractmethod
    async def search(
        self,
        query: Union[str, List[str]],
        num_videos: int,
        sort_type: str,
        recency_days: str,
    ) -> Dict[str, Any]:
        """Execute a TikTok search and return the structured results."""
        raise NotImplementedError

    # Validation helpers -------------------------------------------------
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
        queries = queries_or_err  # already List[str] thanks to ok branch
        self.logger.debug(f"[TikTokSearchService] Normalized queries: {queries}")
        return queries  # type: ignore[return-value]

    # Context helpers ----------------------------------------------------
    def _prepare_context(self, *, in_tests: bool) -> SearchContext:
        from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter, FetchArgComposer
        from app.services.common.browser.camoufox import CamoufoxArgsBuilder

        self.logger.debug(
            f"[TikTokSearchService] Preparing fetch context for independent search - in_tests: {in_tests}"
        )
        # Ensure proper event loop policy on Windows for Playwright/Scrapling
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                self.logger.debug(
                    "[TikTokSearchService] Set WindowsProactorEventLoopPolicy for Scrapling compatibility"
                )
            except Exception as e:  # pragma: no cover - defensive logging
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
        user_data_cleanup: Optional[CleanupCallable] = None
        additional_args: Dict[str, Any] = {}
        try:
            payload = type("Mock", (), {"force_user_data": True})()
            additional_args, extra_headers2 = camoufox_builder.build(payload, settings, caps)
            self.logger.debug(
                f"[TikTokSearchService] Built additional args for forced user data: {len(additional_args)} args"
            )
            if extra_headers is None and extra_headers2 is not None:
                extra_headers = extra_headers2
                self.logger.debug("[TikTokSearchService] Updated extra headers from camoufox build")
            cleanup_candidate = additional_args.get("_user_data_cleanup")
            if callable(cleanup_candidate):
                user_data_cleanup = cleanup_candidate  # type: ignore[assignment]
                self.logger.debug("[TikTokSearchService] Set up user_data_cleanup function")
        except Exception as e:
            self.logger.error(
                f"[TikTokSearchService] Failed to build additional args: {e}",
                exc_info=True,
            )
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

    async def _cleanup_user_data(self, cleanup_callable: Optional[CleanupCallable]) -> None:
        if not callable(cleanup_callable):
            return
        self.logger.debug("[TikTokSearchService] Calling user_data_cleanup function")
        try:
            sleep_func = asyncio.sleep
            # Tests patch asyncio.sleep on the concrete service module. Reuse that
            # patched version when available so existing expectations remain valid
            # after refactoring shared helpers into this abstract base.
            search_module = sys.modules.get("app.services.tiktok.search_service")
            if search_module is not None:
                maybe_asyncio = getattr(search_module, "asyncio", None)
                maybe_sleep = getattr(maybe_asyncio, "sleep", None)
                if callable(maybe_sleep):  # pragma: no branch - defensive branch
                    sleep_func = maybe_sleep  # type: ignore[assignment]

            await sleep_func(3)
            cleanup_callable()
            self.logger.debug("[TikTokSearchService] User data cleanup completed successfully")
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.error(
                f"[TikTokSearchService] User data cleanup failed: {e}",
                exc_info=True,
            )

    # Fetch API ----------------------------------------------------------
    @abstractmethod
    async def _fetch_html(self, query: str, *, context: SearchContext) -> Tuple[int, str]:
        """Fetch the raw HTML for the provided query."""

