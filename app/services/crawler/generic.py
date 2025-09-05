from typing import Optional
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.crawler.core.engine import CrawlerEngine
from app.services.crawler.core.interfaces import PageAction
from app.services.crawler.executors.retry_executor import RetryingExecutor


class GenericCrawler:
    """Generic crawler that uses the CrawlerEngine."""
    
    def __init__(self, engine: CrawlerEngine = None):
        self.engine = engine or CrawlerEngine.from_settings(None)
    
    def run(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Run a generic crawl request."""
        return self.engine.run(request, page_action)


