"""TikVid page action for resolving TikTok video download URLs."""

from __future__ import annotations

from typing import Any, List, Optional

from app.services.browser.actions.base import BasePageAction
from app.core.config import get_settings

# Get TikVid base URL from configuration
settings = get_settings()
TIKVID_BASE = settings.tikvid_base


def _format_exception(exc: BaseException) -> str:
    """Render exceptions so that Windows consoles do not crash on Unicode."""
    try:
        text = str(exc)
    except Exception:
        text = repr(exc)
    try:
        return text.encode("ascii", "backslashreplace").decode()
    except Exception:
        return repr(exc)


class TikVidResolveAction(BasePageAction):
    """
    Page action executed within Camoufox to obtain MP4 download links.

    The action is written defensively: it tries multiple selectors and click
    strategies so it works across localized TikVid UIs and minor DOM changes.
    """

    def __init__(self, tiktok_url: str, quality_hint: Optional[str] = None):
        self.tiktok_url = tiktok_url
        self.quality_hint = (quality_hint or "").lower().strip() or None
        self.result_links: List[str] = []

    def _execute(self, page: Any) -> Any:
        """Execute the TikVid resolution action."""
        import time
        import logging
        logger = logging.getLogger(__name__)

        start_time = time.time()
        logger.debug(f"Page type: {type(page)}, URL: {getattr(page, 'url', 'N/A')}")

        # Block heavy assets for faster loading
        try:
            page.route("**/*.{png,jpg,jpeg,gif,svg,webp,css,font,woff,woff2,ttf,eot}", lambda route: route.abort())
            page.route("**/analytics/**", lambda route: route.abort())
            page.route("**/ads/**", lambda route: route.abort())
            page.route("**/tracking/**", lambda route: route.abort())
            logger.debug("Asset blocking enabled for tikvid.io")
        except Exception as exc:
            logger.warning(f"Asset blocking setup warning: {_format_exception(exc)}")

        # Ensure the browser is on TikVid; Camoufox navigation failures are rare
        # but we guard against them to make debugging easier for future users.
        try:
            if TIKVID_BASE not in getattr(page, "url", ""):
                page.goto(TIKVID_BASE, wait_until="domcontentloaded", timeout=60000)
                navigation_time = time.time() - start_time
                logger.debug(f"TikVid navigation completed in {navigation_time:.2f}s")
        except Exception as exc:
            logger.warning(f"Navigation warning: {_format_exception(exc)}")

        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            dom_load_time = time.time() - start_time
            logger.debug(f"DOM content loaded in {dom_load_time:.2f}s")
        except Exception as exc:
            logger.warning(f"Load state warning: {_format_exception(exc)}")

        # Populate the TikTok URL field; selectors are ordered by specificity.
        selectors = [
            "input[name='url']",
            "input[name='q']",
            "input[type='text']",
            "input[placeholder*='url']",
            "input[placeholder*='link']",
        ]
        field = self._first_visible(page, selectors, timeout=15000)

        field_fill_start = time.time()
        try:
            field.click()
            field.fill("")
            field.fill(self.tiktok_url)
            field_fill_time = time.time() - field_fill_start
            logger.debug(f"URL field filled in {field_fill_time:.2f}s")

            # Check if we're meeting the 3.5s target for the overall page-to-field-fill process
            total_time = time.time() - start_time
            if total_time > 3.5:
                logger.info(f"PERFORMANCE NOTE: Page load to URL fill took {total_time:.2f}s (target: 3.5s)")
                logger.info(f"  - Actual field fill time: {field_fill_time:.2f}s (excellent)")
                logger.info(f"  - Page setup and navigation: {total_time - field_fill_time:.2f}s")
            else:
                logger.debug(f"PERFORMANCE: Page load to URL fill completed within target: {total_time:.2f}s")

        except Exception as exc:
            logger.warning(f"Field fill error: {_format_exception(exc)}")
            try:
                page.keyboard.insert_text(self.tiktok_url)
            except Exception as exc2:
                logger.warning(f"Keyboard insert error: {_format_exception(exc2)}")
                raise Exception("Could not input TikTok URL")

        # TikVid localizes the CTA; run a sequence of strategies until one works.
        strategies = [
            lambda: field.press("Enter"),
            lambda: page.locator("button:has-text('Tải xuống')").first.click(),
            lambda: page.get_by_role("button", name="Download").first.click(),
            lambda: page.locator("text=Download").first.click(),
            lambda: page.locator("button:has-text('Download')").first.click(),
            lambda: page.locator("input[type='submit'][value*='Download']").first.click(),
            lambda: page.locator("form").first.locator("button, input[type='submit']").first.click(),
            lambda: page.locator("#submit").first.click(),
        ]

        for strategy in strategies:
            try:
                strategy()
                logger.debug("Successfully clicked download button")
                break
            except Exception as exc:
                logger.debug(f"Click strategy failed: {_format_exception(exc)}")
        else:
            raise Exception("Could not click download button")

        # Wait until either download links or an error toast appears.
        # Reduced timeout for faster failure and better performance
        wait_start = time.time()
        try:
            page.wait_for_function(
                """() => {
                    const downloadLinks = document.querySelectorAll('a[href*="mp4"], a[href*="download"]');
                    const errorElements = document.querySelectorAll('[class*="error"], [class*="alert"]');
                    return downloadLinks.length > 0 || errorElements.length > 0;
                }""",
                timeout=15000,  # Reduced from 45s to 15s for faster response
            )
            wait_time = time.time() - wait_start
            logger.debug(f"Download links detected in {wait_time:.2f}s")
        except Exception as exc:
            wait_time = time.time() - wait_start
            logger.warning(f"Wait for links timeout after {wait_time:.2f}s: {_format_exception(exc)}")

        page.wait_for_timeout(500)  # Reduced from 1000ms to 500ms

        selectors = [
            "a:has-text('Download MP4')",
            "a[href*='mp4']",
            "a[href*='download']",
            ".download-link a",
            ".video-download a",
        ]

        hrefs: List[str] = []
        for selector in selectors:
            try:
                mp4_links = page.locator(selector)
                for i in range(mp4_links.count()):
                    href = mp4_links.nth(i).get_attribute("href")
                    if not href:
                        continue
                    try:
                        abs_url = page.evaluate("(u) => new URL(u, window.location.href).toString()", href)
                    except Exception:
                        abs_url = href
                    if abs_url not in hrefs:
                        hrefs.append(abs_url)
            except Exception as exc:
                print(f"Selector {selector} failed: {_format_exception(exc)}")

        logger.debug(f"Total download links found: {len(hrefs)}")
        self.result_links = hrefs

        # Returning the page keeps StealthyFetcher happy; consumers inspect
        # `self.result_links` to obtain the URLs collected above.
        return page
