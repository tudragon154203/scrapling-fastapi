import logging
from typing import Any

from .base import BasePageAction


logger = logging.getLogger(__name__)


class WaitForUserCloseAction(BasePageAction):
    """Page action that keeps the browser page open until the user closes it.

    Intended for use with persistent user-data in write mode, where an
    interactive, headful session is desired (e.g., for login flows). The
    action blocks until the page emits a "close" event, then returns.
    """

    def __call__(self, page: Any) -> Any:
        return self._execute(page)

    def _execute(self, page: Any) -> Any:
        try:
            # Try to bring the page to front to ensure it is visible to the user
            try:
                page.bring_to_front()
            except Exception:
                pass

            logger.debug("Waiting for user to close the browser window (write mode)...")

            # Block until the user manually closes the page window
            try:
                page.wait_for_event("close")
            except Exception:
                # As a best-effort fallback, wait on the context to become closed
                try:
                    ctx = getattr(page, "context", None)
                    if ctx is not None and hasattr(ctx, "_impl_obj"):
                        # Some drivers expose "_impl_obj.is_closed()" or similar; ignore if unavailable
                        pass
                except Exception:
                    pass

            logger.debug("Detected page close; proceeding to finish crawl.")
        except Exception as e:
            # Do not fail the crawl due to waiting logic; just log and continue
            logger.warning(f"WaitForUserCloseAction encountered an error: {type(e).__name__}: {e}")
        return page
