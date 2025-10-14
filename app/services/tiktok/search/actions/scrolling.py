"""Scrolling helpers for TikTok search results."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.services.browser.actions.humanize import human_pause


class SearchResultsScroller:
    """Handle scrolling behaviour for search results pages."""

    def __init__(
        self,
        *,
        logger: logging.Logger,
        scroll_max_attempts: int,
        scroll_no_change_limit: int,
        scroll_interval_seconds: float,
    ) -> None:
        self._logger = logger
        self._scroll_max_attempts = scroll_max_attempts
        self._scroll_no_change_limit = scroll_no_change_limit
        self._scroll_interval_seconds = scroll_interval_seconds

    def scroll_results(self, page: Any, target_videos: Optional[int]) -> None:
        """Scroll until the desired number of videos are present or scrolling stalls."""
        if target_videos is None:
            self._logger.debug(
                "Target video count not provided; performing default timed scroll"
            )
            self._timed_scroll(page)
            return

        current_count = self._count_video_results(page)
        if current_count >= target_videos:
            self._logger.debug(
                "Detected %s videos which meets requested count (%s); skipping scroll",
                current_count,
                target_videos,
            )
            return

        self._logger.debug(
            "Scrolling to reach %s videos (currently detected: %s)",
            target_videos,
            current_count,
        )

        no_change_streak = 0
        attempts = 0

        while attempts < self._scroll_max_attempts:
            attempts += 1
            try:
                page.mouse.wheel(0, 800)
            except Exception as exc:
                self._logger.warning("Scroll error on attempt %s: %s", attempts, exc)
                break

            time.sleep(self._scroll_interval_seconds)
            new_count = self._count_video_results(page)

            if new_count >= target_videos:
                self._logger.debug(
                    "Reached requested video count (%s) after %s scroll attempts",
                    target_videos,
                    attempts,
                )
                break

            if new_count <= current_count:
                no_change_streak += 1
                self._logger.debug(
                    "Scroll attempt %s yielded no new videos (still %s); streak=%s",
                    attempts,
                    new_count,
                    no_change_streak,
                )
            else:
                no_change_streak = 0
                current_count = new_count

            if no_change_streak >= self._scroll_no_change_limit:
                self._logger.debug(
                    "Stopping scroll after %s attempts with no additional videos (current=%s)",
                    attempts,
                    new_count,
                )
                break

            if self._is_near_page_end(page):
                self._logger.debug(
                    "Reached end of page after %s attempts with %s videos detected",
                    attempts,
                    new_count,
                )
                break

        human_pause(1, 2)

    def _timed_scroll(self, page: Any) -> None:
        """Fallback scroll behaviour when no target is supplied."""
        self._logger.debug("Scrolling down to load more content (timed fallback)...")
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                page.mouse.wheel(0, 500)
                time.sleep(1)
            except Exception as exc:
                self._logger.warning("Scroll error: %s", exc)
                break
        human_pause(1, 2)

    def _count_video_results(self, page: Any) -> int:
        """Best-effort detection of how many video cards are currently in the DOM."""
        selectors = [
            'div[id^="column-item-video-container-"]',
            '[data-e2e="search-card"]',
            '[data-e2e="search-result-item"]',
        ]

        max_count = 0
        best_selector: Optional[str] = None
        for selector in selectors:
            try:
                count = (
                    page.eval_on_selector_all(selector, "elements => elements.length")
                    or 0
                )
                self._logger.debug("Selector %s found %s elements", selector, count)
                if count > max_count:
                    max_count = int(count)
                    best_selector = selector
            except Exception as exc:
                self._logger.debug("Counting selector %s failed: %s", selector, exc)

        if best_selector:
            self._logger.debug(
                "Best result selector %s yielded %s elements", best_selector, max_count
            )

        return max_count

    def _is_near_page_end(self, page: Any) -> bool:
        """Check whether the scroll position is near the bottom of the page."""
        try:
            return bool(
                page.evaluate(
                    "() => (window.innerHeight + window.scrollY) >= (document.body.scrollHeight - 200)"
                )
            )
        except Exception as exc:
            self._logger.debug("Failed to determine page end: %s", exc)
            return False
