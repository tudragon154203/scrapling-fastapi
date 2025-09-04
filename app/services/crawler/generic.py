import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from .executors.retry import execute_crawl_with_retries
from .executors.single import crawl_single_attempt


def crawl_generic(payload: CrawlRequest) -> CrawlResponse:
    """Generic crawl wrapper selecting single attempt or retry strategy."""
    settings = app_config.get_settings()
    if settings.max_retries <= 1:
        return crawl_single_attempt(payload)
    return execute_crawl_with_retries(payload)
