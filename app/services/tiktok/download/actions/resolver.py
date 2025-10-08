"""TikVid page action for resolving TikTok video download URLs."""

from __future__ import annotations

import os
from typing import Any, List, Optional

from app.services.browser.actions.base import BasePageAction

# TikVid serves regional variants; default to Vietnamese because it currently
# avoids the heavy advertisement overlays seen on the English page.
TIKVID_BASE = os.environ.get("TIKVID_BASE", "https://tikvid.io/vi")


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
        print(f"DEBUG: Page type: {type(page)}, URL: {getattr(page, 'url', 'N/A')}")

        # Ensure the browser is on TikVid; Camoufox navigation failures are rare
        # but we guard against them to make debugging easier for future users.
        try:
            if TIKVID_BASE not in getattr(page, "url", ""):
                page.goto(TIKVID_BASE, wait_until="domcontentloaded", timeout=60000)
        except Exception as exc:
            print(f"Navigation warning: {_format_exception(exc)}")

        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as exc:
            print(f"Load state warning: {_format_exception(exc)}")

        # Populate the TikTok URL field; selectors are ordered by specificity.
        selectors = [
            "input[name='url']",
            "input[name='q']",
            "input[type='text']",
            "input[placeholder*='url']",
            "input[placeholder*='link']",
        ]
        field = self._first_visible(page, selectors, timeout=15000)
        try:
            field.click()
            field.fill("")
            field.fill(self.tiktok_url)
        except Exception as exc:
            print(f"Field fill error: {_format_exception(exc)}")
            try:
                page.keyboard.insert_text(self.tiktok_url)
            except Exception as exc2:
                print(f"Keyboard insert error: {_format_exception(exc2)}")
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
                print("Successfully clicked download button")
                break
            except Exception as exc:
                print(f"Click strategy failed: {_format_exception(exc)}")
        else:
            raise Exception("Could not click download button")

        # Wait until either download links or an error toast appears.
        try:
            page.wait_for_function(
                """() => {
                    const downloadLinks = document.querySelectorAll('a[href*="mp4"], a[href*="download"]');
                    const errorElements = document.querySelectorAll('[class*="error"], [class*="alert"]');
                    return downloadLinks.length > 0 || errorElements.length > 0;
                }""",
                timeout=45000,
            )
        except Exception as exc:
            print(f"Wait for links warning: {_format_exception(exc)}")

        page.wait_for_timeout(1000)  # allow async DOM changes to settle

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

        print(f"Total download links found: {len(hrefs)}")
        self.result_links = hrefs

        # Returning the page keeps StealthyFetcher happy; consumers inspect
        # `self.result_links` to obtain the URLs collected above.
        return page
