from time import time, sleep
from typing import Any, Optional

from app.services.browser.actions.base import BasePageAction


class ScrollDownAction(BasePageAction):
    """Simple scroll-down action for dynamic result loading.

    Tries multiple strategies to be resilient across environments:
    - Use page.mouse.wheel when available (Playwright-like)
    - Fallback to window.scrollBy via page.evaluate
    - Optional brief waits between steps to allow content to render
    """

    def __init__(self, duration_s: float = 10.0, step_px: int = 600, interval_s: float = 1.0,
                 settle_s: float = 1.0, wait_selector: Optional[str] = None):
        self.duration_s = max(0.0, float(duration_s))
        self.step_px = int(step_px)
        self.interval_s = max(0.0, float(interval_s))
        self.settle_s = max(0.0, float(settle_s))
        self.wait_selector = wait_selector

    def _execute(self, page: Any) -> Any:
        # Optional: wait for a hint selector that indicates results are present
        if self.wait_selector:
            try:
                page.wait_for_selector(self.wait_selector, timeout=5000)
            except Exception:
                pass

        start = time()
        while time() - start < self.duration_s:
            if not self._scroll_once(page, self.step_px):
                break
            if self.interval_s:
                sleep(self.interval_s)

        if self.settle_s:
            sleep(self.settle_s)

        return page

    def _scroll_once(self, page: Any, dy: int) -> bool:
        # Try mouse.wheel first
        try:
            page.mouse.wheel(0, dy)
            return True
        except Exception:
            pass
        # Fallback to evaluate scrollBy
        try:
            page.evaluate("window.scrollBy(0, arguments[0]);", dy)
            return True
        except Exception:
            pass
        # As a last resort, try 'End' key if available
        try:
            page.keyboard.press('End')
            return True
        except Exception:
            pass
        return False
