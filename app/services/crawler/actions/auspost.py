import logging
from typing import Any

import app.core.config as app_config
from app.schemas.auspost import AuspostCrawlRequest

from .base import BasePageAction
from .humanize import (
    human_pause,
    move_mouse_to_locator,
    jitter_mouse,
    click_like_human,
    type_like_human,
    scroll_noise,
)

logger = logging.getLogger(__name__)


class AuspostTrackAction(BasePageAction):
    """Page action for AusPost tracking automation."""
    
    def __init__(self, tracking_code: str):
        self.tracking_code = tracking_code
    
    def __call__(self, page: Any) -> Any:
        """Make the action directly callable."""
        return self._execute(page)
    
    def _execute(self, page: Any) -> Any:
        """Playwright page_action for AusPost tracking automation.

        - Waits for the tracking search input
        - Enters the tracking number and submits
        - Handles "Verifying the device..." interstitial if it appears
        - Waits for details URL and selector to appear
        """
        settings = app_config.get_settings()
        humanize = getattr(settings, 'auspost_humanize_enabled', True)

        if humanize:
            logger.debug("Humanization enabled for AusPost tracking action")
            logger.debug("Applying initial humanized pause and scroll noise")
            # initial small dwell
            try:
                human_pause(0.25, 0.8)
                scroll_noise(page, cycles_range=(1, 2))  # small, once
            except Exception:
                # Best-effort humanization; skip on any env limitations
                pass

        # We'll attempt up to 3 submissions to handle flows where
        # the site returns to the search page after verification.
        
        for attempt in range(3):
            try:
                # If we already reached details URL, break early
                if "/mypost/track/details/" in (page.url or ""):
                    break
            except Exception:
                pass

            if humanize:
                # short pre-interaction dwell (settings-based)
                logger.debug("Applying pre-interaction humanized pause")
                try:
                    human_pause(settings.auspost_micro_pause_min_s, settings.auspost_micro_pause_max_s)
                except Exception:
                    human_pause(0.15, 0.4)

            try:
                # If the global header/site search is open, close it so it doesn't steal focus
                self._close_global_search(page)

                # Re-query fresh locators each attempt to avoid stale references and prefer
                # the main page tracking form (avoid the global site search overlay)
                input_locator = self._first_visible(page, [
                    'input[placeholder="Enter tracking number(s)"]',
                    'main input[placeholder="Enter tracking number(s)"]',
                    'main input[data-testid="SearchBarInput"]:not([placeholder="Search our site"])',
                    'input[data-testid="SearchBarInput"]:not([placeholder="Search our site"])',
                    'main input[placeholder*="tracking number"]',
                    'main input[placeholder*="Tracking number"]',
                    'input[placeholder*="tracking number"]',
                    'input[placeholder*="Tracking number"]',
                    'input[aria-label*="tracking"]',
                    'input[aria-label*="Tracking"]',
                ], timeout=10_000)
                if humanize:
                    logger.debug("Using humanized input interaction: mouse move, jitter, click, type")
                    try:
                        move_mouse_to_locator(page, input_locator)
                        jitter_mouse(page, input_locator)
                    except Exception:
                        pass
                    input_locator.click()
                    try:
                        type_like_human(input_locator, self.tracking_code)
                    except Exception:
                        input_locator.fill(self.tracking_code)
                else:
                    input_locator.click()
                    try:
                        input_locator.fill("")
                    except Exception:
                        pass
                    input_locator.fill(self.tracking_code)

                # Prefer clicking the Track/Search button using its data-testid
                try:
                    track_btn = self._first_visible(page, [
                        'button:has-text("Track")',
                        'main button[data-testid="SearchButton"]',
                        'button[data-testid="SearchButton"]',
                    ], timeout=5_000)
                    if humanize:
                        logger.debug("Using humanized click for track button")
                        try:
                            jitter_mouse(page, track_btn)
                            click_like_human(track_btn)
                        except Exception:
                            track_btn.click()
                    else:
                        track_btn.click()
                except Exception:
                    # Fallback: press Enter
                    page.keyboard.press("Enter")

                # Handle AusPost "Verifying the device..." interstitial if it appears
                self._handle_verification(page)

                # Wait for details URL; if not, try clicking generic Track/Search buttons
                tried_generic = False
                try:
                    page.wait_for_url("**/mypost/track/details/**", timeout=15_000)
                    break
                except Exception:
                    try:
                        btn = page.locator('button:has-text("Track"), button:has-text("Search")').first
                        btn.wait_for(state="visible", timeout=5_000)
                        btn.click()
                        tried_generic = True
                        try:
                            page.wait_for_url("**/mypost/track/details/**", timeout=15_000)
                            break
                        except Exception:
                            pass
                    except Exception:
                        pass
                    if humanize:
                        logger.debug("Applying humanized pause and scroll noise after failed attempt")
                        try:
                            human_pause(0.25, 0.7)
                            scroll_noise(page, cycles_range=(1, 1))
                        except Exception:
                            pass

                # If we are still on search page (common after verification), loop and retry
                try:
                    if "/mypost/track/search" in (page.url or "") and not page.locator("h3#trackingPanelHeading").first.is_visible():
                        # small grace wait before next attempt to let any cookies settle
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=2_000)
                        except Exception:
                            pass
                        continue
                except Exception:
                    pass
            except Exception:
                # On any unexpected errors, continue attempts but don't fail the whole flow
                pass

        # Safety wait for the details header to appear (in addition to engine wait_selector)
        try:
            page.locator("h3#trackingPanelHeading").first.wait_for(state="visible", timeout=15_000)
        except Exception:
            pass

        if humanize:
            logger.debug("Applying final humanized pause and scroll noise")
            try:
                human_pause(0.2, 0.5)
                scroll_noise(page, cycles_range=(1, 2))
            except Exception:
                pass

        return page
    
    def _close_global_search(self, page: Any) -> None:
        """Close the global search overlay if it's open."""
        try:
            header_search = page.locator('input[placeholder="Search our site"]').first
            if header_search.is_visible():
                # Try close button first (more reliable than Escape)
                try:
                    close_btn = self._first_visible(page, [
                        "button[aria-label*='Close']",
                        "button[aria-label*='close']",
                        "button[title*='Close']",
                        "button:has-text('Ã—')",
                        "[role='dialog'] button",
                    ], timeout=2_000)
                    close_btn.click()
                    try:
                        header_search.wait_for(state="hidden", timeout=2_000)
                    except Exception:
                        pass
                except Exception:
                    # Fallback: press Escape
                    page.keyboard.press("Escape")
                    try:
                        header_search.wait_for(state="hidden", timeout=2_000)
                    except Exception:
                        pass
        except Exception:
            pass
    
    def _handle_verification(self, page: Any) -> None:
        """Handle the verification interstitial if it appears."""
        try:
            verifying = page.locator("text=Verifying the device")
            verifying.first.wait_for(state="visible", timeout=4_000)
            # Wait until verification finishes
            verifying.first.wait_for(state="hidden", timeout=20_000)
            page.wait_for_load_state(state="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle")
            except Exception:
                pass
        except Exception:
            pass


