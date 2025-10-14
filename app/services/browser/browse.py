import importlib
import logging
import app.core.config as app_config
from app.schemas.crawl import CrawlRequest
from app.schemas.browse import BrowseRequest, BrowseResponse, BrowserEngine
from app.services.common.engine import CrawlerEngine
from app.services.browser.actions.wait_for_close import WaitForUserCloseAction
from app.services.common.browser import user_data as user_data_mod
from app.services.common.browser import user_data_chromium
from app.services.browser.executors.browse_executor import BrowseExecutor
from app.services.browser.executors.chromium_browse_executor import ChromiumBrowseExecutor
from app.services.browser.utils.error_advice import (
    ChromiumErrorAdvisor,
    chromium_dependency_missing_advice,
)
from app.services.browser.utils.runtime_contexts import (
    CamoufoxRuntimeContext,
    ChromiumRuntimeContext,
)

logger = logging.getLogger(__name__)

_ORIGINAL_MANAGER_CLS = user_data_chromium.ChromiumUserDataManager
ChromiumUserDataManager = _ORIGINAL_MANAGER_CLS
_ORIGINAL_EXECUTOR_CLS = ChromiumBrowseExecutor


def _resolve_chromium_manager_cls():
    """Return the Chromium user-data manager class, honoring test-time patches."""
    override = globals().get("ChromiumUserDataManager", None)
    module_cls = getattr(user_data_chromium, "ChromiumUserDataManager")

    if override is not None and override is not _ORIGINAL_MANAGER_CLS:
        return override
    if module_cls is not _ORIGINAL_MANAGER_CLS:
        return module_cls
    return override or module_cls


def _resolve_chromium_executor_cls():
    """Return the Chromium browse executor class, honoring test-time patches."""
    override = globals().get("ChromiumBrowseExecutor", None)
    module_cls = getattr(
        importlib.import_module("app.services.browser.executors.chromium_browse_executor"),
        "ChromiumBrowseExecutor",
    )

    if override is not None and override is not _ORIGINAL_EXECUTOR_CLS:
        return override
    if module_cls is not _ORIGINAL_EXECUTOR_CLS:
        return module_cls
    return override or module_cls


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
                executor_cls = _resolve_chromium_executor_cls()
                browse_executor = executor_cls()
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
            # Convert browse request to crawl request with forced flags
            crawl_request = self._convert_browse_to_crawl_request(request)

            # Handle user data context for Camoufox only
            if request.engine == BrowserEngine.CAMOUFOX:
                return self._run_camoufox_session(crawl_request)
            return self._run_chromium_session(crawl_request)

        except ImportError as e:
            advice = chromium_dependency_missing_advice(e)
            log_message = advice.log_message or advice.message
            getattr(logger, advice.log_level)(log_message)
            return BrowseResponse(
                status="failure",
                message=advice.message,
            )
        except Exception as e:
            engine_label = getattr(request, "engine", BrowserEngine.CAMOUFOX)
            try:
                engine_name = getattr(engine_label, "value", str(engine_label))
            except Exception:
                engine_name = str(engine_label)
            logger.error(f"{engine_name.capitalize()} browse session failed: {e}")
            return BrowseResponse(
                status="failure",
                message=f"Error: {str(e)}",
            )

    def _run_camoufox_session(self, crawl_request: CrawlRequest) -> BrowseResponse:
        """Run a Camoufox browse session with user data context."""
        settings = app_config.get_settings()
        user_data_dir = getattr(
            settings, 'camoufox_user_data_dir', 'data/camoufox_profiles'
        ) or 'data/camoufox_profiles'

        with CamoufoxRuntimeContext(settings, user_data_dir, user_data_context_fn=user_data_context):
            # Update crawl request with user-data enablement
            crawl_request.force_user_data = True

            # Create wait for user close action
            page_action = WaitForUserCloseAction()

            # Execute browse session
            self.engine.run(crawl_request, page_action)

            # Log session completion for Camoufox
            logger.info("Camoufox browse session completed")

            # Return success response
            return BrowseResponse(
                status="success",
                message="Browser session completed successfully",
            )

    def _run_chromium_session(self, crawl_request: CrawlRequest) -> BrowseResponse:
        """Run a Chromium browse session with user data context."""
        settings = app_config.get_settings()

        # Get user data directory for Chromium
        user_data_dir = getattr(
            settings, 'chromium_user_data_dir', 'data/chromium_profiles'
        )

        manager_cls = _resolve_chromium_manager_cls()
        user_data_manager = manager_cls(user_data_dir)
        self.user_data_manager = user_data_manager  # Store for error handling
        advisor = ChromiumErrorAdvisor(
            settings=settings,
            user_data_dir=user_data_dir,
            lock_file=getattr(user_data_manager, "lock_file", None),
        )

        try:
            with ChromiumRuntimeContext(settings, user_data_manager) as (effective_dir, _):
                # Update crawl request with user-data enablement
                crawl_request.force_user_data = True

                # Create wait for user close action
                page_action = WaitForUserCloseAction()

                # Execute browse session
                crawl_result = self.engine.run(crawl_request, page_action)

                # If the executor surfaced a failure (without raising), propagate it
                try:
                    result_status = getattr(crawl_result, "status", None)
                    result_message = getattr(crawl_result, "message", None)
                except Exception:
                    result_status = None
                    result_message = None

                if result_status != "success":
                    # Do not export cookies; propagate failure upstream
                    logger.error(f"Chromium browse executor returned failure status: {result_message}")
                    return BrowseResponse(
                        status="failure",
                        message=f"Chromium browse executor failed: {result_message or 'Unknown error'}"
                    )

                # Export cookies from the master profile after successful session
                user_data_manager.export_cookies()
                logger.info("Chromium browse session completed, cookies exported to master profile")

                # Return success response
                return BrowseResponse(
                    status="success",
                    message="Chromium browser session completed successfully",
                )
        except RuntimeError as e:
            advice = advisor.handle_runtime_error(e)
            if advice is None:
                raise
            log_message = advice.log_message or advice.message
            getattr(logger, advice.log_level)(log_message)
            return BrowseResponse(status="failure", message=advice.message)
        except (OSError, PermissionError, TimeoutError, ConnectionError, MemoryError, ImportError) as e:
            advice = advisor.handle_known_exception(e)
            log_message = advice.log_message or advice.message
            getattr(logger, advice.log_level)(log_message)
            return BrowseResponse(status="failure", message=advice.message)
        except Exception as e:
            advice = advisor.generic_failure(e)
            log_message = advice.log_message or advice.message
            getattr(logger, advice.log_level)(log_message)
            return BrowseResponse(status="failure", message=advice.message)

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
