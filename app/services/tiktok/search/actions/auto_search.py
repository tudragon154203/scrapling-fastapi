"""TikTokAutoSearchAction - Page action for automated TikTok search."""

import logging
import time
from pathlib import Path
from typing import Callable, List, Optional

from app.services.browser.actions.base import BasePageAction
from app.services.browser.actions.humanize import (
    click_like_human,
    human_pause,
    move_mouse_to_locator,
    type_like_human,
)


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

    SEARCH_INPUT_SELECTORS = [
        'input[data-e2e="search-user-input"]',
        'input[data-e2e="search-box-input"]',
        'input[data-e2e="search-suggest"]',
        'input[placeholder*="Search"]',
        'input[type="search"]',
        'input[aria-label*="Search"]',
        '.search-bar',
        'input[placeholder*="search"]',
        'input[aria-label*="search"]',
        'input[data-e2e="search-input"]',
        'input[name="search"]',
        'input[data-testid="search-input"]',
        'input[class*="search"]',
        'input[role="combobox"]',
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

    def __init__(
        self,
        search_query: str,
        *,
        save_html: bool = False,
        html_save_path: Optional[str] = None,
    ):
        self.search_query = search_query
        self.page = None
        self.html_content = ""
        self.logger = logging.getLogger(__name__)
        self._cleanup_functions: List[Callable] = []
        self.save_html = save_html
        default_snapshot_path = Path(__file__).resolve().parents[1] / "browsing_tiktok_search.html"
        self._html_snapshot_path = Path(html_save_path) if html_save_path else default_snapshot_path

    def __call__(self, page):
        return self._execute(page)

    def _execute(self, page):
        """Execute the automated search process."""
        try:
            self._initialize(page)
            self._prepare_search_ui(page)
            search_input = self._find_search_input(page)
            search_query = self._encode_search_query()
            self._enter_search_query(page, search_input, search_query)
            self._submit_search(page)
            self._await_search_results(page)
            self._scroll_results(page)
            self._capture_html(page)

            self.logger.info("Search automation completed successfully!")
            return page

        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("Error during automated search: %s", exc, exc_info=True)
            self._cleanup()
            raise
        finally:
            self._cleanup()

    def _initialize(self, page) -> None:
        """Set up logging, state and cleanup hooks before execution."""
        self.page = page
        self.logger.info("Starting automated TikTok search for: '%s'", self.search_query)
        self._cleanup_functions.append(self._cleanup_browser_resources)
        self._wait_for_initial_load(page)

    def _prepare_search_ui(self, page) -> None:
        """Ensure the search UI is visible and ready for typing."""
        if not self._click_search_button(page):
            self.logger.warning(
                "Could not find search button, proceeding with typing attempt..."
            )
            self._focus_page_body(page)
        self._wait_for_search_ui(page)

    def _wait_for_initial_load(self, page) -> None:
        """Wait for the page to settle before interacting with it."""
        self.logger.info("Waiting for page to load...")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

    def _wait_for_search_ui(self, page) -> None:
        """Wait for the search interface to be rendered."""
        self._wait_for_network_idle(page)

    def _click_search_button(self, page) -> bool:
        """Locate the search button and click it using human-like motions."""
        for selector in self.SEARCH_BUTTON_SELECTORS:
            try:
                search_bar = page.query_selector(selector)
                if search_bar:
                    self.logger.info("Found search bar with selector: %s", selector)
                    move_mouse_to_locator(page, search_bar, steps_range=(15, 25))
                    click_like_human(search_bar)
                    return True
            except Exception as exc:
                self.logger.debug("Selector %s failed: %s", selector, exc)
        return False

    def _focus_page_body(self, page) -> None:
        """Attempt to focus the page body when no search button is found."""
        try:
            page.focus("body")
        except Exception:  # pragma: no cover - focus is best-effort
            pass

    def _find_search_input(self, page):
        """Return the first matching search input element, if any."""
        for selector in self.SEARCH_INPUT_SELECTORS:
            try:
                search_input = page.query_selector(selector)
                if search_input:
                    self.logger.info("Found search input with selector: %s", selector)
                    return search_input
            except Exception as exc:
                self.logger.debug("Search input selector %s failed: %s", selector, exc)
        return None

    def _encode_search_query(self) -> str:
        """Best-effort encoding of the search query to UTF-8."""
        self.logger.info("Typing search query: '%s'", self.search_query)
        try:
            return self.search_query.encode("utf-8", errors="ignore").decode("utf-8")
        except Exception:  # pragma: no cover - encoding rarely fails
            return self.search_query

    def _enter_search_query(self, page, search_input, search_query: str) -> None:
        """Type the search query either in the input field or directly via keyboard."""
        if search_input:
            self._type_into_search_input(page, search_input, search_query)
            return

        try:
            human_pause(1, 2)
            page.keyboard.type(search_query)
        except Exception as exc:
            self.logger.warning("Fallback typing failed: %s", exc)

    def _type_into_search_input(self, page, search_input, search_query: str) -> None:
        """Type the query into the located search input with human-like behaviour."""
        try:
            type_like_human(search_input, search_query, delay_ms_range=(50, 100))
        except Exception as exc:
            self.logger.warning("type_like_human failed: %s", exc)
            try:
                page.keyboard.type(search_query)
            except Exception as fallback_exc:
                self.logger.warning("Keyboard typing fallback failed: %s", fallback_exc)

    def _submit_search(self, page) -> None:
        """Trigger the search submission."""
        self.logger.info("Submitting search...")
        try:
            page.keyboard.press("Enter")
        except Exception as exc:
            self.logger.warning("Enter key failed: %s", exc)

    def _await_search_results(self, page) -> None:
        """Wait until search results are likely loaded."""
        self.logger.info("Waiting for search results page to load...")
        human_pause(2, 3)
        self._wait_for_results_url(page)
        self._wait_for_network_idle(page)
        if not self._scan_result_selectors(page):
            self._fallback_result_detection(page)

    def _wait_for_results_url(self, page) -> None:
        """Block until the page URL indicates that search results are shown."""
        try:
            page.wait_for_function(
                "window.location.href.includes('/search')",
                timeout=15000,
            )
            self.logger.info("Search URL detected!")
        except Exception as exc:
            self.logger.warning("Search URL wait timeout or error: %s", exc)

    def _wait_for_network_idle(self, page) -> None:
        """Wait for the page network activity to settle."""
        try:
            page.wait_for_load_state("networkidle")
        except Exception as exc:  # pragma: no cover - best-effort wait
            self.logger.debug("Network idle wait failed: %s", exc)
        time.sleep(2)

    def _scan_result_selectors(self, page) -> bool:
        """Scan for known result selectors without per-selector waits."""
        self.logger.info("Scanning for search result elements...")
        for selector in self.RESULT_SELECTORS:
            try:
                result_element = page.query_selector(selector)
                if result_element:
                    self.logger.info("Found search result with selector: %s", selector)
                    return True
            except Exception as exc:
                self.logger.debug("Result selector %s failed: %s", selector, exc)
        return False

    def _fallback_result_detection(self, page) -> None:
        """Fallback detection when specific selectors cannot be located."""
        self.logger.warning(
            "No specific result selectors found, using content-based detection..."
        )
        try:
            page_content = page.content()
            if len(page_content) > 10000:
                self.logger.info(
                    "Page content detected (length > 10KB), assuming search results loaded"
                )
        except Exception as exc:
            self.logger.warning("Could not check page content: %s", exc)

    def _scroll_results(self, page) -> None:
        """Scroll to encourage dynamic result loading."""
        self.logger.info("Scrolling down to load more content...")
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                page.mouse.wheel(0, 500)
                time.sleep(1)
            except Exception as exc:
                self.logger.warning("Scroll error: %s", exc)
                break
        human_pause(1, 2)

    def _capture_html(self, page) -> None:
        """Capture and optionally persist the HTML content of the results."""
        self.logger.info("Capturing HTML content...")
        try:
            self.html_content = page.content()
            self.logger.info(
                "Captured HTML content length: %s", len(self.html_content)
            )
            if self.save_html and self.html_content:
                self._persist_html_snapshot(self.html_content)
        except Exception as exc:
            self.logger.error("Failed to capture HTML content: %s", exc)
            self.html_content = ""

    def _cleanup_browser_resources(self):
        """Cleanup browser resources."""
        try:
            if self.page and not self.page.is_closed():
                self.page.close()
                self.logger.debug("Closed browser page during cleanup")
        except Exception as e:
            self.logger.warning(f"Error during browser cleanup: {e}")

    def _cleanup(self):
        """Execute all registered cleanup functions."""
        for cleanup_func in self._cleanup_functions:
            try:
                cleanup_func()
            except Exception as e:
                self.logger.warning(f"Cleanup function failed: {e}")
        self._cleanup_functions.clear()

    def _persist_html_snapshot(self, html_content: str) -> None:
        """Persist captured HTML to disk for debugging and parity with demo script."""
        try:
            snapshot_path = self._html_snapshot_path
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            header = (
                f"<!-- TikTok Search Results Snapshot - {timestamp} -->\n"
                f"<!-- Search query: {self.search_query} -->\n\n"
            )
            try:
                snapshot_path.write_text(header + html_content, encoding="utf-8")
            except UnicodeEncodeError:
                snapshot_path.write_text(
                    header + html_content, encoding="latin-1", errors="replace"
                )
            self.logger.info("Saved HTML snapshot to %s", snapshot_path)
        except Exception as exc:
            self.logger.warning("Failed to save HTML snapshot: %s", exc)
