"""Abstract helpers for TikTok search services."""

from __future__ import annotations

import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from app.core.config import get_settings
from app.services.tiktok.search.interfaces import TikTokSearchInterface
from app.services.tiktok.protocols import CleanupCallable, SearchContext


class AbstractTikTokSearchService(ABC, TikTokSearchInterface):
    """Base class containing reusable helpers for TikTok search services."""

    def __init__(self) -> None:
        from app.core.config import get_settings
        self.settings = get_settings()
        self.logger = logging.getLogger(self.__class__.__module__)

    @abstractmethod
    async def search(
        self,
        query: Union[str, List[str]],
        num_videos: int,
    ) -> Dict[str, Any]:
        """Execute a TikTok search and return the structured results."""
        raise NotImplementedError

    # Validation helpers -------------------------------------------------
    def _is_tests_env(self) -> bool:
        """Return whether the current execution is happening under tests or CI."""
        settings = get_settings()
        return (
            bool(settings.pytest_current_test) or
            settings.testing or
            settings.ci
        )

    def _normalize_queries(self, query: Union[str, List[str]]) -> Tuple[bool, Union[List[str], Dict[str, Any]]]:
        """Normalize user-provided queries into a filtered list of search strings."""
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
    ) -> Union[List[str], Dict[str, Any]]:
        """Validate the incoming query payload."""
        self.logger.debug(f"[TikTokSearchService] Normalizing query: {query}")
        ok, queries_or_err = self._normalize_queries(query)
        if not ok:
            self.logger.warning(f"[TikTokSearchService] Query normalization failed: {queries_or_err}")
            return queries_or_err
        queries = cast(List[str], queries_or_err)
        self.logger.debug(f"[TikTokSearchService] Normalized queries: {queries}")
        return queries

    # Context helpers ----------------------------------------------------
    def _prepare_context(self, *, in_tests: bool, force_headful: bool = False) -> SearchContext:
        """Compose fetch dependencies needed to perform an independent search."""
        from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter, FetchArgComposer
        from app.services.common.browser.camoufox import CamoufoxArgsBuilder

        self.logger.debug(
            f"[TikTokSearchService] Preparing fetch context for independent search - in_tests: {in_tests}, force_headful: {force_headful}"
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
        if not getattr(settings, "camoufox_user_data_dir", None):
            self.logger.warning(
                "[TikTokSearchService] camoufox_user_data_dir not configured; continuing without persistent user data"
            )
        fetcher = ScraplingFetcherAdapter()
        composer = FetchArgComposer()
        camoufox_builder = CamoufoxArgsBuilder()
        caps = fetcher.detect_capabilities()
        self.logger.debug(f"[TikTokSearchService] Detected capabilities: {caps}")
        try:
            base_payload = SimpleNamespace(
                force_user_data=False,
                force_mute_audio=True,
            )
            _, extra_headers = camoufox_builder.build(base_payload, settings, caps)
            self.logger.debug("[TikTokSearchService] Built base headers for non-force_user_data")
        except Exception as e:
            self.logger.warning(f"[TikTokSearchService] Failed to build base headers: {e}")
            extra_headers = None
        user_data_cleanup: Optional[CleanupCallable] = None
        additional_args: Dict[str, Any] = {}
        try:
            forced_payload = SimpleNamespace(
                force_user_data=True,
                force_mute_audio=True,
            )
            additional_args, extra_headers2 = camoufox_builder.build(forced_payload, settings, caps)
            self.logger.debug(
                f"[TikTokSearchService] Built additional args for forced user data: {len(additional_args)} args"
            )
            if extra_headers is None and extra_headers2 is not None:
                extra_headers = extra_headers2
                self.logger.debug("[TikTokSearchService] Updated extra headers from camoufox build")
            cleanup_candidate = additional_args.get("_user_data_cleanup")
            if callable(cleanup_candidate):
                user_data_cleanup = cast(CleanupCallable, cleanup_candidate)
                self.logger.debug("[TikTokSearchService] Set up user_data_cleanup function")
        except Exception as e:
            self.logger.error(
                f"[TikTokSearchService] Failed to build additional args: {e}",
                exc_info=True,
            )
            additional_args = {}

        # Determine headless mode:
        # 1. If in test environment, always use headless
        # 2. Otherwise, use force_headful parameter to determine mode
        if in_tests:
            headless_opt = True
        else:
            headless_opt = not force_headful  # force_headful=True means headless=False

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
        """Pause briefly and trigger any cleanup callback returned from Scrapling."""
        if not callable(cleanup_callable):
            return
        self.logger.debug("[TikTokSearchService] Calling user_data_cleanup function")
        try:
            # Give more time for processes to release file handles
            await asyncio.sleep(5)  # Increased sleep time
            self._handle_cleanup([cleanup_callable])

            # Explicitly check if the directory still exists after cleanup
            if cleanup_callable and hasattr(cleanup_callable, '__self__') and hasattr(cleanup_callable.__self__, 'clone_dir'):
                clone_dir_path = cleanup_callable.__self__.clone_dir
                if os.path.exists(clone_dir_path):
                    self.logger.warning(f"[TikTokSearchService] Clone directory {clone_dir_path} still exists after cleanup attempt.")
                else:
                    self.logger.debug("[TikTokSearchService] User data cleanup completed successfully")
            else:
                self.logger.debug("[TikTokSearchService] User data cleanup completed successfully (path not available for verification)")
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.error(
                f"[TikTokSearchService] User data cleanup failed: {e}",
                exc_info=True,
            )

    # Fetch API ----------------------------------------------------------
    @abstractmethod
    async def _fetch_html(self, query: str, *, context: SearchContext) -> Tuple[int, str]:
        """Fetch the raw HTML for the provided query."""

    def _handle_cleanup(self, cleanup_functions: Optional[List[CleanupCallable]]) -> None:
        """Invoke each provided cleanup callback, logging failures but continuing."""
        if not cleanup_functions:
            return

        for cleanup in cleanup_functions:
            if not callable(cleanup):
                continue
            try:
                cleanup()
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.error(
                    f"[TikTokSearchService] Cleanup callback raised an exception: {exc}",
                    exc_info=True,
                )
