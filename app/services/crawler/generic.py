from typing import Optional
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.common.engine import CrawlerEngine
from app.services.common.interfaces import PageAction


class GenericCrawler:
    """Generic crawler that uses the CrawlerEngine."""

    def __init__(self, engine: CrawlerEngine = None):
        self.engine = engine or CrawlerEngine.from_settings(None)

    def run(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Run a generic crawl request.

        The /crawl endpoint only supports read mode for user data.
        Auto-close behavior has been removed as write mode is no longer supported.
        """
        # Since write mode is removed from /crawl endpoint, no need for auto-close action
        # The endpoint will always use read mode for user data
        return self.engine.run(request, page_action)
