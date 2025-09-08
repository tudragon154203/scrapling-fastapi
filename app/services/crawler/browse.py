import logging
from typing import Optional

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest
from app.schemas.browse import BrowseRequest, BrowseResponse
from app.services.crawler.core.engine import CrawlerEngine
from app.services.crawler.actions.wait_for_close import WaitForUserCloseAction
from app.services.crawler.options.user_data import user_data_context

logger = logging.getLogger(__name__)


class BrowseCrawler:
    """Browse-specific crawler for interactive user data population sessions."""

    def __init__(self, engine: CrawlerEngine = None):
        self.engine = engine or CrawlerEngine.from_settings(app_config.get_settings())

    def run(self, request: BrowseRequest) -> BrowseResponse:
        """Run a browse request for user data population."""
        try:
            # Convert browse request to crawl request with forced flags
            crawl_request = self._convert_browse_to_crawl_request(request)

            # Use user data context (always temporary clone)
            settings = app_config.get_settings()
            user_data_dir = getattr(settings, 'camoufox_user_data_dir', 'data/camoufox_profiles')

            with user_data_context(user_data_dir, 'write') as (effective_dir, cleanup):
                try:
                    # Update crawl request with effective user data directory
                    crawl_request.force_user_data = True

                    # Create wait for user close action
                    page_action = WaitForUserCloseAction()

                    # Execute browse session
                    crawl_response = self.engine.run(crawl_request, page_action)

                    # Return success response
                    return BrowseResponse(
                        status="success",
                        message="Browser session completed successfully"
                    )

                finally:
                    # Ensure cleanup is called
                    cleanup()

        except Exception as e:
            logger.error(f"Browse session failed: {e}")
            return BrowseResponse(
                status="failure",
                message=f"Error: {str(e)}"
            )

    def _convert_browse_to_crawl_request(self, browse_request: BrowseRequest) -> CrawlRequest:
        """Convert browse request to generic crawl request with forced flags."""
        # Use provided URL or default to about:blank
        url = str(browse_request.url) if browse_request.url else "about:blank"

        return CrawlRequest(
            url=url,
            force_headful=True,  # Always use headful mode for interactive browsing
            force_user_data=True,  # Always enable user data
            timeout_seconds=None,  # No timeout for manual sessions
        )