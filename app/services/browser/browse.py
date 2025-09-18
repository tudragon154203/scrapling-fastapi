import logging

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest
from app.schemas.browse import BrowseRequest, BrowseResponse
from app.services.common.engine import CrawlerEngine
from app.services.browser.actions.wait_for_close import WaitForUserCloseAction
from app.services.common.browser import user_data as user_data_mod
from app.services.browser.executors.browse_executor import BrowseExecutor

logger = logging.getLogger(__name__)


def user_data_context(*args, **kwargs):
    """Proxy to the shared user-data context for easier patching in tests."""
    return user_data_mod.user_data_context(*args, **kwargs)


class BrowseCrawler:
    """Browse-specific crawler for interactive user data population sessions."""

    def __init__(self, engine: CrawlerEngine = None):
        # Use a custom browse engine that respects user close actions
        if engine is None:
            # Create a browse-specific engine that never retries
            browse_engine = BrowseExecutor()
            self.engine = CrawlerEngine(
                executor=browse_engine,
                fetch_client=browse_engine.fetch_client,
                options_resolver=browse_engine.options_resolver,
                camoufox_builder=browse_engine.camoufox_builder
            )
        else:
            self.engine = engine

    def run(self, request: BrowseRequest) -> BrowseResponse:
        """Run a browse request for user data population."""
        try:
            # Convert browse request to crawl request with forced flags
            crawl_request = self._convert_browse_to_crawl_request(request)

            # Use user data context (always temporary clone)
            settings = app_config.get_settings()
            user_data_dir = getattr(settings, 'camoufox_user_data_dir', 'data/camoufox_profiles')

            mute_flag_set = False
            try:
                setattr(settings, '_camoufox_force_mute_audio', True)
                mute_flag_set = True
            except Exception:
                pass

            try:
                with user_data_context(user_data_dir, 'write') as (effective_dir, cleanup):
                    try:
                        # Signal write-mode to CamoufoxArgsBuilder via settings (runtime-only flags)
                        try:
                            setattr(settings, '_camoufox_user_data_mode', 'write')
                            setattr(settings, '_camoufox_effective_user_data_dir', effective_dir)
                        except Exception:
                            pass

                        # Update crawl request with user-data enablement
                        crawl_request.force_user_data = True

                        # Create wait for user close action
                        page_action = WaitForUserCloseAction()

                        # Execute browse session
                        self.engine.run(crawl_request, page_action)

                        # Return success response
                        return BrowseResponse(
                            status="success",
                            message="Browser session completed successfully"
                        )

                    finally:
                        # Ensure cleanup is called
                        try:
                            # Remove runtime flags to avoid leaking into subsequent requests
                            if hasattr(settings, '_camoufox_user_data_mode'):
                                delattr(settings, '_camoufox_user_data_mode')
                            if hasattr(settings, '_camoufox_effective_user_data_dir'):
                                delattr(settings, '_camoufox_effective_user_data_dir')
                        except Exception:
                            pass
                        if callable(cleanup):
                            cleanup()
            finally:
                if mute_flag_set and hasattr(settings, '_camoufox_force_mute_audio'):
                    try:
                        delattr(settings, '_camoufox_force_mute_audio')
                    except Exception:
                        pass

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
