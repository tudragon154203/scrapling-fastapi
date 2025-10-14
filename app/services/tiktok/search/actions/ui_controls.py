"""Helper utilities for preparing and interacting with the TikTok search UI."""

from __future__ import annotations

import logging
import time
from typing import Any, Iterable, Tuple

from app.services.browser.actions.humanize import (
    click_like_human,
    human_pause,
    move_mouse_to_locator,
    type_like_human,
)

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
except ImportError:  # pragma: no cover - Playwright might be unavailable in tests
    PlaywrightTimeoutError = TimeoutError  # type: ignore[misc, assignment]


DEFAULT_SEARCH_INPUT_SELECTORS: Tuple[str, ...] = (
    'input[data-e2e="search-input"]',
    'input[data-e2e="top-search-input"]',
    'input[placeholder*="Search"]',
    'input[aria-label*="Search"]',
    'input[type="search"]',
    'input[type="text"]',
    'input[class*="search"]',
    'input[data-testid="search-input"]',
    'input[name="search"]',
    'input[role="combobox"]',
)


def wait_for_network_idle(
    page: Any, logger: logging.Logger, ui_ready_pause: float
) -> None:
    """Wait for the page network state to settle and pause briefly."""
    try:
        page.wait_for_load_state("networkidle")
    except Exception as exc:  # pragma: no cover - best-effort wait
        logger.debug("Network idle wait failed: %s", exc)
    time.sleep(ui_ready_pause)


class SearchUIController:
    """Encapsulates operations for preparing and interacting with the search UI."""

    def __init__(
        self,
        *,
        logger: logging.Logger,
        search_button_selectors: Iterable[str],
        search_input_selectors: Iterable[str] | None,
        ui_ready_pause: float,
    ) -> None:
        self._logger = logger
        self._search_button_selectors = tuple(search_button_selectors)
        self._search_input_selectors = (
            tuple(search_input_selectors)
            if search_input_selectors is not None
            else DEFAULT_SEARCH_INPUT_SELECTORS
        )
        self._ui_ready_pause = ui_ready_pause

    def wait_for_initial_load(self, page: Any) -> None:
        """Wait for the page to finish its initial load state."""
        self._logger.debug("Waiting for page to load...")
        page.wait_for_load_state("networkidle")
        time.sleep(self._ui_ready_pause)

    def prepare_search_ui(self, page: Any) -> None:
        """Ensure the search UI is ready for typing."""
        clicked = self._click_search_button(page)
        if not clicked:
            self._logger.warning(
                "Could not find search button, proceeding with typing attempt..."
            )
            self._focus_page_body(page)
        else:
            time.sleep(self._ui_ready_pause)
        self.wait_for_search_ui(page)

    def wait_for_search_ui(self, page: Any) -> None:
        """Wait for search UI elements to become interactive."""
        wait_for_network_idle(page, self._logger, self._ui_ready_pause)

    def encode_search_query(self, search_query: str) -> str:
        """Best-effort encoding of the search query to UTF-8."""
        self._logger.debug("Typing search query: '%s'", search_query)
        try:
            return search_query.encode("utf-8", errors="ignore").decode("utf-8")
        except Exception:  # pragma: no cover - encoding rarely fails
            return search_query

    def enter_search_query(
        self, page: Any, search_input: Any | None, search_query: str
    ) -> None:
        """Type the search query either in the input or via keyboard."""
        target_input = search_input or self._find_search_input(page)
        if target_input:
            self._type_into_search_input(page, target_input, search_query)
            return

        try:
            human_pause(1, 2)
            page.keyboard.type(search_query)
        except Exception as exc:
            self._logger.warning("Fallback typing failed: %s", exc)

    def _find_search_input(self, page: Any) -> Any | None:
        """Locate a search input element using known selectors."""
        for selector in self._search_input_selectors:
            try:
                input_element = page.query_selector(selector)
                if input_element:
                    self._logger.debug(
                        "Found search input with selector: %s", selector
                    )
                    return input_element
            except Exception as exc:
                self._logger.debug(
                    "Search input selector %s failed: %s", selector, exc
                )

        self._logger.debug("No search input located; will fall back to keyboard typing")
        return None

    def submit_search(self, page: Any) -> None:
        """Trigger search submission."""
        self._logger.debug("Submitting search...")
        try:
            page.keyboard.press("Enter")
        except Exception as exc:
            self._logger.warning("Enter key failed: %s", exc)

    def _click_search_button(self, page: Any) -> bool:
        """Locate the search button and click it using human-like motions."""
        for selector in self._search_button_selectors:
            try:
                visible_selector = f"{selector} >> visible=true"
                search_bar = page.wait_for_selector(visible_selector, timeout=5_000)
                if not search_bar:
                    continue
                try:
                    box = search_bar.bounding_box()
                except Exception:
                    box = None
                if not box or box.get("width", 0) < 5 or box.get("height", 0) < 5:
                    self._logger.debug(
                        "Search bar selector %s had no usable bounding box; skipping",
                        selector,
                    )
                    continue
                try:
                    if hasattr(search_bar, "is_enabled") and not search_bar.is_enabled():
                        self._logger.debug(
                            "Search bar selector %s is not enabled; skipping",
                            selector,
                        )
                        continue
                except Exception:
                    pass
                self._logger.debug("Found search bar with selector: %s", selector)
                move_mouse_to_locator(page, search_bar, steps_range=(15, 25))
                click_like_human(search_bar)
                return True
            except Exception as exc:
                if isinstance(exc, PlaywrightTimeoutError):
                    self._logger.debug(
                        "Search button selector %s not visible: %s", selector, exc
                    )
                else:
                    self._logger.debug("Selector %s failed: %s", selector, exc)
        return False

    def _focus_page_body(self, page: Any) -> None:
        """Attempt to focus the page body when no search button is found."""
        try:
            page.focus("body")
        except Exception:  # pragma: no cover - focus is best-effort
            pass

    def _type_into_search_input(
        self, page: Any, search_input: Any, search_query: str
    ) -> None:
        """Type the query into the located search input with human-like behaviour."""
        try:
            type_like_human(search_input, search_query, delay_ms_range=(50, 100))
        except Exception as exc:
            self._logger.warning("type_like_human failed: %s", exc)
            try:
                page.keyboard.type(search_query)
            except Exception as fallback_exc:
                self._logger.warning(
                    "Keyboard typing fallback failed: %s", fallback_exc
                )
