from abc import ABC, abstractmethod
from typing import Any
from app.services.common.interfaces import PageAction


class BasePageAction(PageAction, ABC):
    """Base implementation of PageAction with common functionality."""
    
    def apply(self, page: Any) -> Any:
        """Apply the page action to the given page."""
        return self._execute(page)
    
    @abstractmethod
    def _execute(self, page: Any) -> Any:
        """Execute the specific page action logic."""
        ...
    
    def _first_visible(self, page: Any, selectors: list, timeout: int = 5000):
        """Helper to find the first visible selector."""
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=timeout)
                return loc
            except Exception:
                continue
        # Return last locator without waiting if nothing matched
        return page.locator(selectors[-1]).first
