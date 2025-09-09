import logging

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.schemas.dpd import DPDCrawlRequest, DPDCrawlResponse

from app.services.common.engine import CrawlerEngine

logger = logging.getLogger(__name__)


DPD_BASE = "https://tracking.dpd.de/status/en_US/parcel"

class DPDCrawler:
    """DPD-specific crawler that uses the CrawlerEngine without page actions."""
    
    def __init__(self, engine: CrawlerEngine = None):
        self.engine = engine or CrawlerEngine.from_settings(app_config.get_settings())
    
    def run(self, request: DPDCrawlRequest) -> DPDCrawlResponse:
        """Run a DPD crawl request."""
        # Convert DPDCrawlRequest to CrawlRequest
        crawl_request = self._convert_dpd_to_crawl_request(request)
        
        # Execute crawl with engine (no page action needed for DPD)
        crawl_response = self.engine.run(crawl_request)

        return DPDCrawlResponse(
            status=crawl_response.status,
            tracking_code=request.tracking_code,
            html=crawl_response.html,
            message=crawl_response.message,
        )
    
    def _convert_dpd_to_crawl_request(self, dpd_request: DPDCrawlRequest) -> CrawlRequest:
        """Convert DPD request to generic crawl request."""
        from app.schemas.crawl import CrawlRequest
        from urllib.parse import quote
        
        # Normalize tracking code: strip whitespace, remove spaces and hyphens, URL-encode if needed
        normalized_code = dpd_request.tracking_code.strip()
        normalized_code = normalized_code.replace(" ", "").replace("-", "")
        encoded_code = quote(normalized_code)
        
        url = f"{DPD_BASE}/{encoded_code}"
        
        return CrawlRequest(
            url=url,
            wait_for_selector="div.delivery-info",
            wait_for_selector_state="visible",
            network_idle=True,
            force_headful=dpd_request.force_headful,
            force_user_data=dpd_request.force_user_data,
            timeout_seconds=30,  # Converted from 30_000ms to seconds
        )





