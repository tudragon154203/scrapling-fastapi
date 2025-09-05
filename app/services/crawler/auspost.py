import logging

import app.core.config as app_config
from app.schemas.auspost import AuspostCrawlRequest, AuspostCrawlResponse
from app.schemas.crawl import CrawlRequest, CrawlResponse

from .core.engine import CrawlerEngine
from .actions.auspost import AuspostTrackAction

logger = logging.getLogger(__name__)


class AuspostCrawler:
    """AusPost-specific crawler that uses the CrawlerEngine with page actions."""
    
    def __init__(self, engine: CrawlerEngine = None):
        self.engine = engine or CrawlerEngine.from_settings(app_config.get_settings())
    
    def run(self, request: AuspostCrawlRequest) -> AuspostCrawlResponse:
        """Run an AusPost crawl request."""
        # Convert AusPost request to generic crawl request
        crawl_request = self._convert_auspost_to_crawl_request(request)
        
        # Create page action for AusPost automation
        page_action = AuspostTrackAction(request.tracking_code)
        
        # Execute crawl with page action
        crawl_response = self.engine.run(crawl_request, page_action)
        
        # Convert back to AusPost response
        return self._convert_crawl_to_auspost_response(crawl_response, request.tracking_code)
    
    def _convert_auspost_to_crawl_request(self, auspost_request: AuspostCrawlRequest) -> CrawlRequest:
        """Convert AusPost request to generic crawl request."""
        return CrawlRequest(
            url="https://auspost.com.au/mypost/track/search",
            headless=False,
            x_force_headful=auspost_request.x_force_headful,
            x_force_user_data=auspost_request.x_force_user_data,
            wait_selector="h3#trackingPanelHeading",
            wait_selector_state="visible",
            network_idle=True,
            x_wait_time=2,
            timeout_ms=30_000,
        )
    
    def _convert_crawl_to_auspost_response(self, 
                                         crawl_response: CrawlResponse, 
                                         tracking_code: str) -> AuspostCrawlResponse:
        """Convert generic crawl response to AusPost-specific response."""
        return AuspostCrawlResponse(
            status=crawl_response.status,
            tracking_code=tracking_code,
            html=crawl_response.html,
            message=crawl_response.message
        )





