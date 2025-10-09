import logging

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest
from app.schemas.browse import BrowseRequest, BrowseResponse, BrowserEngine
from app.services.common.engine import CrawlerEngine
from app.services.browser.actions.wait_for_close import WaitForUserCloseAction
from app.services.common.browser import user_data as user_data_mod
from app.services.browser.executors.browse_executor import BrowseExecutor
from app.services.browser.executors.chromium_browse_executor import ChromiumBrowseExecutor

logger = logging.getLogger(__name__)


def user_data_context(*args, **kwargs):
    """Proxy to the shared user-data context for easier patching in tests."""
    return user_data_mod.user_data_context(*args, **kwargs)


class BrowseCrawler:
    """Browse-specific crawler for interactive user data population sessions."""

    def __init__(self, engine: CrawlerEngine = None, browser_engine: BrowserEngine = BrowserEngine.CAMOUFOX):
        # Use a custom browse engine that respects user close actions
        if engine is None:
            # Create a browse-specific engine based on the selected browser engine
            if browser_engine == BrowserEngine.CHROMIUM:
                browse_executor = ChromiumBrowseExecutor()
                # For Chromium, we don't have all the same components as Camoufox
                self.engine = CrawlerEngine(executor=browse_executor)
            else:
                # Default to Camoufox
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
            # Create the appropriate crawler based on engine selection
            crawler = BrowseCrawler(browser_engine=request.engine)

            # Convert browse request to crawl request with forced flags
            crawl_request = self._convert_browse_to_crawl_request(request)

            # Handle user data context for Camoufox only
            if request.engine == BrowserEngine.CAMOUFOX:
                return self._run_camoufox_session(crawler, crawl_request)
            else:
                return self._run_chromium_session(crawler, crawl_request)

        except Exception as e:
            logger.error(f"Browse session failed: {e}")
            return BrowseResponse(
                status="failure",
                message=f"Error: {str(e)}"
            )

    def _run_camoufox_session(self, crawler: 'BrowseCrawler', crawl_request: CrawlRequest) -> BrowseResponse:
        """Run a Camoufox browse session with user data context."""
        settings = app_config.get_settings()
        user_data_dir = getattr(
            settings, 'camoufox_user_data_dir', 'data/camoufox_profiles'
        )

        previous_mute = bool(
            getattr(settings, 'camoufox_runtime_force_mute_audio', False)
        )
        settings.camoufox_runtime_force_mute_audio = True

        cleanup = None
        previous_mode = getattr(settings, 'camoufox_runtime_user_data_mode', None)
        previous_effective_dir = getattr(
            settings, 'camoufox_runtime_effective_user_data_dir', None
        )

        try:
            with user_data_context(user_data_dir, 'write') as (effective_dir, cleanup):
                # Signal write-mode to CamoufoxArgsBuilder via settings (runtime-only flags)
                settings.camoufox_runtime_user_data_mode = 'write'
                settings.camoufox_runtime_effective_user_data_dir = effective_dir

                # Update crawl request with user-data enablement
                crawl_request.force_user_data = True

                # Create wait for user close action
                page_action = WaitForUserCloseAction()

                # Execute browse session
                crawler.engine.run(crawl_request, page_action)

                # Export cookies from the master profile after session
                user_data_manager.export_cookies()
                logger.info("Chromium browse session completed, cookies exported to master profile")

                # Return success response
                return BrowseResponse(
                    status="success",
                    message="Browser session completed successfully"
                )
        finally:
            settings.camoufox_runtime_user_data_mode = previous_mode
            settings.camoufox_runtime_effective_user_data_dir = previous_effective_dir
            if callable(cleanup):
                cleanup()
            settings.camoufox_runtime_force_mute_audio = previous_mute

    def _run_chromium_session(self, crawler: 'BrowseCrawler', crawl_request: CrawlRequest) -> BrowseResponse:
        """Run a Chromium browse session with user data context."""
        settings = app_config.get_settings()

        # Get user data directory for Chromium
        user_data_dir = getattr(
            settings, 'chromium_user_data_dir', 'data/chromium_profiles'
        )

        cleanup = None
        previous_mode = getattr(settings, 'chromium_runtime_user_data_mode', None)
        previous_effective_dir = getattr(
            settings, 'chromium_runtime_effective_user_data_dir', None
        )

        try:
            # Use Chromium user data context in write mode
            from app.services.common.browser.user_data_chromium import ChromiumUserDataManager
            user_data_manager = ChromiumUserDataManager(user_data_dir)

            with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
                # Signal write-mode to Chromium executor via settings (runtime-only flags)
                settings.chromium_runtime_user_data_mode = 'write'
                settings.chromium_runtime_effective_user_data_dir = effective_dir

                # Update crawl request with user-data enablement
                crawl_request.force_user_data = True

                # Create wait for user close action
                page_action = WaitForUserCloseAction()

                # Execute browse session
                crawler.engine.run(crawl_request, page_action)

                # Export cookies from the master profile after session
                user_data_manager.export_cookies()
                logger.info("Chromium browse session completed, cookies exported to master profile")

                # Return success response
                return BrowseResponse(
                    status="success",
                    message="Browser session completed successfully"
                )
        except RuntimeError as e:
            # Handle lock conflicts specifically
            if "already in use" in str(e) or "lock" in str(e).lower():
                logger.warning(f"Chromium profile locked: {e}")
                return BrowseResponse(
                    status="failure",
                    message="Chromium profile already in use by another session"
                )
            # Re-raise other runtime errors
            raise
        except Exception as e:
            logger.error(f"Chromium browse session failed: {e}")
            return BrowseResponse(
                status="failure",
                message=f"Error: {str(e)}"
            )
        finally:
            # Restore previous runtime settings
            settings.chromium_runtime_user_data_mode = previous_mode
            settings.chromium_runtime_effective_user_data_dir = previous_effective_dir
            if callable(cleanup):
                cleanup()

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
