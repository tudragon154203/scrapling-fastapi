from typing import Optional
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.crawler.core.engine import CrawlerEngine
from app.services.crawler.core.interfaces import PageAction
from app.services.crawler.executors.retry_executor import RetryingExecutor
from app.services.crawler.actions.wait_for_close import WaitForUserCloseAction
import app.core.config as app_config


class GenericCrawler:
    """Generic crawler that uses the CrawlerEngine."""
    
    def __init__(self, engine: CrawlerEngine = None):
        self.engine = engine or CrawlerEngine.from_settings(None)
    
    def run(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Run a generic crawl request.

        When persistent user-data is requested in write mode and the
        session is intended to be headful, keep the browser open until the
        user manually closes the window (per spec docs/sprint/18_camoufox_user_data_spec.md).
        """
        # Auto-attach a manual-close page action for write-mode interactive sessions
        if (
            page_action is None
            and getattr(request, "force_user_data", False) is True
            and getattr(request, "user_data_mode", "read") == "write"
            and getattr(request, "force_headful", False) is True
        ):
            # Only apply when persistent user-data directory is configured
            settings = app_config.get_settings()
            if getattr(settings, "camoufox_user_data_dir", None):
                page_action = WaitForUserCloseAction()

        return self.engine.run(request, page_action)
