import logging

import app.core.config as app_config
from app.schemas.auspost import AuspostCrawlRequest, AuspostCrawlResponse
from app.schemas.crawl import CrawlRequest, CrawlResponse

from app.services.common.engine import CrawlerEngine
from .actions.auspost import AuspostTrackAction
from .executors.auspost_no_proxy import SingleAttemptNoProxy

logger = logging.getLogger(__name__)


class AuspostCrawler:
    """AusPost-specific crawler that uses the CrawlerEngine with page actions."""
    
    def __init__(self, engine: CrawlerEngine = None):
        # For AusPost, use a single-attempt, no-proxy executor to improve stability with DataDome
        self.engine = engine or CrawlerEngine(executor=SingleAttemptNoProxy())
    
    def run(self, request: AuspostCrawlRequest) -> AuspostCrawlResponse:
        """Run an AusPost crawl request."""
        # Convert AusPost request to generic crawl request
        crawl_request = self._convert_auspost_to_crawl_request(request)
        
        # Create page action for AusPost automation
        page_action = AuspostTrackAction(request.tracking_code)
        
        # Execute crawl with page action
        crawl_response = self.engine.run(crawl_request, page_action)

        # Fallback: if environment does not support interactive page actions
        # (e.g., NotImplementedError from underlying driver), try direct details URL
        if (
            crawl_response.status == "failure"
            and isinstance(crawl_response.message, str)
            and "NotImplementedError" in crawl_response.message
        ):
            try:
                details_url = f"https://auspost.com.au/mypost/track/details/{request.tracking_code}"
                fb_request = CrawlRequest(
                    url=details_url,
                    wait_for_selector="h3#trackingPanelHeading",
                    wait_for_selector_state="visible",
                    network_idle=True,
                    force_headful=request.force_headful,
                    force_user_data=request.force_user_data,
                    timeout_seconds=30,
                )
                fb_response = self.engine.run(fb_request, page_action=None)
                # Prefer successful fallback result
                if fb_response.status == "success":
                    return self._convert_crawl_to_auspost_response(fb_response, request.tracking_code)
            except Exception:
                # Ignore fallback errors and return original failure below
                pass
        
        # Convert back to AusPost response
        return self._convert_crawl_to_auspost_response(crawl_response, request.tracking_code)
    
    def _convert_auspost_to_crawl_request(self, auspost_request: AuspostCrawlRequest) -> CrawlRequest:
        """Convert AusPost request to generic crawl request."""
        return CrawlRequest(
            url="https://auspost.com.au/mypost/track/search",
            wait_for_selector="h3#trackingPanelHeading",
            wait_for_selector_state="visible",
            network_idle=True,
            force_headful=auspost_request.force_headful,
            force_user_data=auspost_request.force_user_data,
            timeout_seconds=30,  # Converted from 30_000ms to seconds
        )
    
    def _convert_crawl_to_auspost_response(
        self, 
        crawl_response: CrawlResponse, 
        tracking_code: str
    ) -> AuspostCrawlResponse:
        """Convert generic crawl response to AusPost-specific response."""
        return AuspostCrawlResponse(
            status=crawl_response.status,
            tracking_code=tracking_code,
            html=crawl_response.html,
            message=crawl_response.message
        )

