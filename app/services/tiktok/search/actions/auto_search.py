"""TikTokAutoSearchAction - Page action for automated TikTok search."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, List, Optional

from app.services.browser.actions.base import BasePageAction

from .results_monitor import SearchResultsMonitor
from .scrolling import SearchResultsScroller
from .snapshot import SearchSnapshotCapturer
from .ui_controls import SearchUIController


class TikTokAutoSearchAction(BasePageAction):
    """Page action that automatically performs TikTok search using human-like typing."""

    SEARCH_BUTTON_SELECTORS = [
        'button[data-e2e="nav-search"]',
        'button[data-e2e="search-button"]',
        'button[data-e2e="top-search"]',
        '.css-1o3yfob-5e6d46e3--DivSearchWrapper e9sj7gd4 button[data-e2e="nav-search"]',
        '.TUXButton[data-e2e="nav-search"]',
        '[data-e2e="nav-search"]',
        'button[aria-label*="Search"]',
        'button[aria-label*="search"]',
        'button[class*="search"]',
        'button[data-testid="search-button"]',
        'form[role="search"] button',
        '.css-udify9-5e6d46e3--StyledTUXSearchButton',
    ]

    RESULT_SELECTORS = [
        '[data-e2e="search-result-item"]',
        '[data-e2e="search-general-item"]',
        '[data-e2e="search-user-item"]',
        '[data-e2e="search-result-video"]',
        '[data-e2e="search_video-item"]',
        '[data-e2e="search_top-item"]',
        '[data-e2e="search-card"]',
        '[data-e2e="general-search-card"]',
        '[class*="video"]',
        '[class*="card"]',
        '[class*="search-result"]',
        '[class*="searchItem"]',
        'div[data-testid="search-item"]',
        'li[data-testid="search-item"]',
        'img[src*="tiktokcdn"]',
        'video',
        'a[href*="/@"]',
        'a[href*="/video/"]',
    ]

    RESULT_SCAN_TIMEOUT = 10
    RESULT_SCAN_INTERVAL = 0.5

    UI_READY_PAUSE = 2  # seconds

    SCROLL_MAX_ATTEMPTS = 20
    SCROLL_NO_CHANGE_LIMIT = 3
    SCROLL_INTERVAL_SECONDS = 1.5

    def __init__(
        self,
        search_query: str,
        *,
        save_html: bool = False,
        html_save_path: Optional[str] = None,
        ui_controller: Optional[SearchUIController] = None,
        results_monitor: Optional[SearchResultsMonitor] = None,
        scroller: Optional[SearchResultsScroller] = None,
        snapshot_capturer: Optional[SearchSnapshotCapturer] = None,
    ) -> None:
        self.search_query = search_query
        self.page: Optional[Any] = None
        self.html_content = ""
        self.logger = logging.getLogger(__name__)
        self._cleanup_functions: List[Callable[[], None]] = []
        default_snapshot_path = (
            Path(__file__).resolve().parents[1] / "browsing_tiktok_search.html"
        )
        snapshot_path = Path(html_save_path) if html_save_path else default_snapshot_path
        self.target_videos: Optional[int] = None

        self.ui_controller = ui_controller or SearchUIController(
            logger=self.logger,
            search_button_selectors=self.SEARCH_BUTTON_SELECTORS,
            ui_ready_pause=self.UI_READY_PAUSE,
        )
        self.results_monitor = results_monitor or SearchResultsMonitor(
            logger=self.logger,
            result_selectors=self.RESULT_SELECTORS,
            result_scan_timeout=self.RESULT_SCAN_TIMEOUT,
            result_scan_interval=self.RESULT_SCAN_INTERVAL,
            ui_ready_pause=self.UI_READY_PAUSE,
        )
        self.scroller = scroller or SearchResultsScroller(
            logger=self.logger,
            scroll_max_attempts=self.SCROLL_MAX_ATTEMPTS,
            scroll_no_change_limit=self.SCROLL_NO_CHANGE_LIMIT,
            scroll_interval_seconds=self.SCROLL_INTERVAL_SECONDS,
        )
        self.snapshot_capturer = snapshot_capturer or SearchSnapshotCapturer(
            logger=self.logger,
            save_html=save_html,
            snapshot_path=snapshot_path,
            search_query=self.search_query,
        )

    def set_target_videos(self, target_videos: Optional[int]) -> None:
        """Configure the desired number of videos to load while scrolling."""
        if target_videos is not None and target_videos > 0:
            self.target_videos = int(target_videos)
        else:
            self.target_videos = None

    def __call__(self, page: Any) -> Any:
        return self._execute(page)

    def _execute(self, page: Any) -> Any:
        """Execute the automated search process."""
        try:
            self._initialize(page)
            self.ui_controller.prepare_search_ui(page)
            search_query = self.ui_controller.encode_search_query(self.search_query)
            self.ui_controller.enter_search_query(page, None, search_query)
            self.ui_controller.submit_search(page)
            self.results_monitor.await_search_results(page)
            self.scroller.scroll_results(page, self.target_videos)
            self.html_content = self.snapshot_capturer.capture_html(page)

            self.logger.info("Search automation completed successfully!")
            return page

        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("Error during automated search: %s", exc, exc_info=True)
            self._cleanup()
            raise
        finally:
            self._cleanup()

    def _initialize(self, page: Any) -> None:
        """Set up logging, state and cleanup hooks before execution."""
        self.page = page
        self.logger.info("Starting automated TikTok search for: '%s'", self.search_query)
        self._cleanup_functions.append(self._cleanup_browser_resources)
        self.ui_controller.wait_for_initial_load(page)

    def _cleanup_browser_resources(self) -> None:
        """Cleanup browser resources."""
        try:
            if self.page and not self.page.is_closed():
                self.page.close()
                self.logger.debug("Closed browser page during cleanup")
        except Exception as exc:  # pragma: no cover - cleanup best-effort
            self.logger.warning("Error during browser cleanup: %s", exc)

    def _cleanup(self) -> None:
        """Execute all registered cleanup functions."""
        for cleanup_func in self._cleanup_functions:
            try:
                cleanup_func()
            except Exception as exc:  # pragma: no cover - cleanup best-effort
                self.logger.warning("Cleanup function failed: %s", exc)
        self._cleanup_functions.clear()
