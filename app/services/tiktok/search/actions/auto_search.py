"""TikTokAutoSearchAction - Page action for automated TikTok search."""

import logging
import time
from pathlib import Path
from typing import Callable, List, Optional

from app.services.browser.actions.base import BasePageAction
from app.services.browser.actions.humanize import human_pause, type_like_human, move_mouse_to_locator, click_like_human


class TikTokAutoSearchAction(BasePageAction):
    """Page action that automatically performs TikTok search using human-like typing."""

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
            self.page = page
            self.logger.info(f"Starting automated TikTok search for: '{self.search_query}'")

            # Register cleanup function
            self._cleanup_functions.append(self._cleanup_browser_resources)

            # Wait for page to load
            self.logger.info("Waiting for page to load...")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Find and click the search button using TikTok selectors
            search_selectors = [
                'button[data-e2e="nav-search"]',
                '.css-1o3yfob-5e6d46e3--DivSearchWrapper e9sj7gd4 button[data-e2e="nav-search"]',
                '.TUXButton[data-e2e="nav-search"]',
                '[data-e2e="nav-search"]',
                'button[aria-label*="Search"]',
                '.css-udify9-5e6d46e3--StyledTUXSearchButton'
            ]

            search_clicked = False
            search_bar = None
            for selector in search_selectors:
                try:
                    search_bar = page.query_selector(selector)
                    if search_bar:
                        self.logger.info(f"Found search bar with selector: {selector}")
                        # Use human-like hover and click
                        move_mouse_to_locator(page, search_bar, steps_range=(15, 25))
                        click_like_human(search_bar)
                        search_clicked = True
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not search_clicked:
                self.logger.warning("Could not find search button, proceeding with typing attempt...")
                try:
                    page.focus('body')
                except Exception:
                    pass

            # Ensure the search UI has rendered before locating input fields
            try:
                page.wait_for_load_state("networkidle")
                time.sleep(2)
            except Exception as e:
                self.logger.debug(f"Second load state wait failed: {e}")

            # Find the search input field
            search_input_selectors = [
                'input[data-e2e="search-user-input"]',
                'input[placeholder*="Search"]',
                'input[type="search"]',
                '.search-bar',
                'input[placeholder*="search"]',
                'input[data-e2e="search-input"]'
            ]

            search_input_found = False
            search_input = None
            for selector in search_input_selectors:
                try:
                    search_input = page.query_selector(selector)
                    if search_input:
                        self.logger.info(f"Found search input with selector: {selector}")
                        search_input_found = True
                        break
                except Exception as e:
                    self.logger.debug(f"Search input selector {selector} failed: {e}")
                    continue

            # Type the search query using human-like typing
            self.logger.info(f"Typing search query: '{self.search_query}'")
            search_query_encoded = self.search_query
            try:
                search_query_encoded = self.search_query.encode('utf-8', errors='ignore').decode('utf-8')
            except Exception:
                pass

            if search_input_found:
                try:
                    type_like_human(search_input, search_query_encoded, delay_ms_range=(50, 100))
                except Exception as e:
                    self.logger.warning(f"type_like_human failed: {e}")
                    try:
                        page.keyboard.type(search_query_encoded)
                    except Exception as e2:
                        self.logger.warning(f"Keyboard typing fallback failed: {e2}")
            else:
                try:
                    human_pause(1, 2)
                    page.keyboard.type(search_query_encoded)
                except Exception as e:
                    self.logger.warning(f"Fallback typing failed: {e}")

            # Submit the search
            self.logger.info("Submitting search...")
            try:
                page.keyboard.press('Enter')
            except Exception as e:
                self.logger.warning(f"Enter key failed: {e}")

            # Wait for search results to load
            self.logger.info("Waiting for search results page to load...")
            human_pause(2, 3)

            # Wait for URL to contain '/search'
            try:
                page.wait_for_function(
                    "window.location.href.includes('/search')",
                    timeout=15000
                )
                self.logger.info("Search URL detected!")
            except Exception as e:
                self.logger.warning(f"Search URL wait timeout or error: {e}")

            # Wait for search result elements
            self.logger.info("Waiting for search result elements...")
            result_selectors = [
                '[data-e2e="search-result-item"]',
                '[data-e2e="search-result-video"]',
                '[data-e2e="search_video-item"]',
                '[class*="video"]',
                '[class*="card"]',
                'img[src*="tiktokcdn"]',
                'video',
                'a[href*="/@"]',
                'a[href*="/video/"]'
            ]

            result_found = False
            for selector in result_selectors:
                try:
                    result_element = page.wait_for_selector(selector, timeout=5000)
                    if result_element:
                        self.logger.info(f"Found search result with selector: {selector}")
                        result_found = True
                        break
                except Exception as e:
                    self.logger.debug(f"Result selector {selector} failed: {e}")
                    continue

            if not result_found:
                self.logger.warning("No specific result selectors found, using content-based detection...")
                try:
                    page_content = page.content()
                    if len(page_content) > 10000:
                        self.logger.info("Page content detected (length > 10KB), assuming search results loaded")
                        result_found = True
                except Exception as e:
                    self.logger.warning(f"Could not check page content: {e}")

            # Scroll down to load more content
            self.logger.info("Scrolling down to load more content...")
            start_time = time.time()
            while time.time() - start_time < 10:
                try:
                    page.mouse.wheel(0, 500)
                    time.sleep(1)
                except Exception as e:
                    self.logger.warning(f"Scroll error: {e}")
                    break

            # Wait after scrolling for content to settle
            human_pause(1, 2)

            # Capture the HTML content
            self.logger.info("Capturing HTML content...")
            try:
                self.html_content = page.content()
                self.logger.info(f"Captured HTML content length: {len(self.html_content)}")
                if self.save_html and self.html_content:
                    self._persist_html_snapshot(self.html_content)
            except Exception as e:
                self.logger.error(f"Failed to capture HTML content: {e}")
                self.html_content = ""

            self.logger.info("Search automation completed successfully!")
            return page

        except Exception as e:
            self.logger.error(f"Error during automated search: {e}", exc_info=True)
            # Ensure cleanup even on error
            self._cleanup()
            raise
        finally:
            # Always attempt cleanup
            self._cleanup()

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
