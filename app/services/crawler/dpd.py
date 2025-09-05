import logging

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.schemas.dpd import DPDCrawlRequest, DPDCrawlResponse

from .core.engine import CrawlerEngine

logger = logging.getLogger(__name__)


class DPDCrawler:
    """DPD-specific crawler that uses the CrawlerEngine without page actions."""
    
    def __init__(self, engine: CrawlerEngine = None):
        self.engine = engine or CrawlerEngine.from_settings(app_config.get_settings())
    
    def run(self, request: DPDCrawlRequest) -> CrawlResponse:
        """Run a DPD crawl request."""
        # Convert DPDCrawlRequest to CrawlRequest
        crawl_request = self._convert_dpd_to_crawl_request(request)
        
        # Execute crawl with engine (no page action needed for DPD)
        return self.engine.run(crawl_request)
    
    def _convert_dpd_to_crawl_request(self, dpd_request: DPDCrawlRequest) -> CrawlRequest:
        """Convert DPD request to generic crawl request."""
        from app.schemas.crawl import CrawlRequest
        
        return CrawlRequest(
            url=f"https://dhlparcel.nl/en/track-and-trace/{dpd_request.tracking_code}",
            headless=True,
            x_force_headful=dpd_request.x_force_headful,
            x_force_user_data=dpd_request.x_force_user_data,
            wait_selector="div.delivery-info",
            wait_selector_state="visible",
            network_idle=True,
            x_wait_time=2,
            timeout_ms=30_000,
        )





