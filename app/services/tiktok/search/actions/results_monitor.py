"""Helper for monitoring and validating TikTok search results loading."""

from __future__ import annotations

import logging
import time
from typing import Any, Iterable

from app.services.browser.actions.humanize import human_pause

from .ui_controls import wait_for_network_idle


class SearchResultsMonitor:
    """Monitor the search results page and ensure content is available."""

    def __init__(
        self,
        *,
        logger: logging.Logger,
        result_selectors: Iterable[str],
        result_scan_timeout: float,
        result_scan_interval: float,
        ui_ready_pause: float,
    ) -> None:
        self._logger = logger
        self._result_selectors = tuple(result_selectors)
        self._result_scan_timeout = result_scan_timeout
        self._result_scan_interval = result_scan_interval
        self._ui_ready_pause = ui_ready_pause

    def await_search_results(self, page: Any) -> None:
        """Wait until search results are likely loaded."""
        self._logger.debug("Waiting for search results page to load...")
        human_pause(2, 3)
        self._wait_for_results_url(page)
        wait_for_network_idle(page, self._logger, self._ui_ready_pause)
        if not self._scan_result_selectors(page):
            self._fallback_result_detection(page)

    def _wait_for_results_url(self, page: Any) -> None:
        """Block until the page URL indicates that search results are shown."""
        try:
            page.wait_for_function(
                "window.location.href.includes('/search')",
                timeout=15000,
            )
            self._logger.debug("Search URL detected!")
        except Exception as exc:
            self._logger.warning("Search URL wait timeout or error: %s", exc)

    def _scan_result_selectors(self, page: Any) -> bool:
        """Scan for known result selectors while waiting for them to appear."""
        self._logger.debug("Scanning for search result elements...")
        deadline = time.time() + self._result_scan_timeout
        while time.time() < deadline:
            for selector in self._result_selectors:
                try:
                    result_element = page.query_selector(selector)
                    if result_element:
                        self._logger.debug(
                            "Found search result with selector: %s", selector
                        )
                        return True
                except Exception as exc:
                    self._logger.debug("Result selector %s failed: %s", selector, exc)
            time.sleep(self._result_scan_interval)
        self._logger.debug(
            "No search result selectors found within %.1f seconds",
            self._result_scan_timeout,
        )
        return False

    def _fallback_result_detection(self, page: Any) -> None:
        """Fallback detection when specific selectors cannot be located."""
        self._logger.warning(
            "No specific result selectors found, using content-based detection..."
        )
        try:
            page_content = page.content()
            if len(page_content) > 10000:
                self._logger.debug(
                    "Page content detected (length > 10KB), assuming search results loaded"
                )
        except Exception as exc:
            self._logger.warning("Could not check page content: %s", exc)
