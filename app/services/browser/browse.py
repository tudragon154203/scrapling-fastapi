import logging
import os

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest
from app.schemas.browse import BrowseRequest, BrowseResponse, BrowserEngine
from app.services.common.engine import CrawlerEngine
from app.services.browser.actions.wait_for_close import WaitForUserCloseAction
from app.services.common.browser import user_data as user_data_mod
from app.services.browser.executors.browse_executor import BrowseExecutor
from app.services.browser.executors.chromium_browse_executor import ChromiumBrowseExecutor
from app.services.common.browser.user_data_chromium import ChromiumUserDataManager

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
            # Convert browse request to crawl request with forced flags
            crawl_request = self._convert_browse_to_crawl_request(request)

            # Handle user data context for Camoufox only
            if request.engine == BrowserEngine.CAMOUFOX:
                return self._run_camoufox_session(self, crawl_request)
            else:
                return self._run_chromium_session(self, crawl_request)

        except ImportError as e:
            # Surface helpful guidance when Chromium dependencies are missing before session start
            error_msg = (
                f"Chromium dependencies are not available: {str(e)}\n"
                "To resolve this issue:\n"
                "1. Install the required dependencies: pip install 'scrapling[chromium]'\n"
                "2. Ensure Playwright browsers are installed: playwright install chromium\n"
                "3. Alternatively, use the Camoufox engine by setting 'engine': 'camoufox' in your request"
            )
            logger.error(f"Chromium dependencies missing: {e}")
            return BrowseResponse(
                status="failure",
                message=error_msg
            )
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

                # Log session completion for Camoufox
                logger.info("Camoufox browse session completed")

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
            user_data_manager = ChromiumUserDataManager(user_data_dir)
            self.user_data_manager = user_data_manager  # Store for error handling

            with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
                # Ensure absolute path for profile persistence
                effective_dir = os.path.abspath(effective_dir) if effective_dir else None

                # Signal write-mode to Chromium executor via settings (runtime-only flags)
                settings.chromium_runtime_user_data_mode = 'write'
                settings.chromium_runtime_effective_user_data_dir = os.path.abspath(effective_dir) if effective_dir else None

                # Update crawl request with user-data enablement
                crawl_request.force_user_data = True

                # Create wait for user close action
                page_action = WaitForUserCloseAction()

                # Execute browse session
                crawl_result = crawler.engine.run(crawl_request, page_action)

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
                    message="Chromium browser session completed successfully"
                )
        except RuntimeError as e:
            # Handle specific RuntimeError cases
            msg_lower = str(e).lower()

            # Handle lock conflicts specifically
            if "already in use" in msg_lower or "lock" in msg_lower or "exclusive" in msg_lower:
                error_msg = (
                    "Chromium profile is already in use by another session. "
                    "To resolve this issue:\n"
                    "1. Wait for the current session to complete\n"
                    "2. Check if another browser instance is running\n"
                    "3. If no session is active, manually remove the lock file: "
                    f"{getattr(self, 'user_data_manager', None) and self.user_data_manager.lock_file}\n"
                    "4. Consider using a different user data directory via CHROMIUM_USER_DATA_DIR environment variable"
                )
                logger.warning(f"Chromium profile locked: {e}")
                return BrowseResponse(
                    status="failure",
                    message=error_msg
                )

            # Profile corruption guidance
            if "corrupt" in msg_lower or "corrupted" in msg_lower or "database is corrupted" in msg_lower:
                error_msg = (
                    f"Chromium user profile appears corrupted: {str(e)}\n"
                    "Recovery steps:\n"
                    "1. Close all Chromium/Chrome instances\n"
                    "2. Backup and then delete the corrupted profile directory\n"
                    f"   Path: {getattr(app_config.get_settings(), 'chromium_runtime_effective_user_data_dir', None) or os.path.abspath(user_data_dir)}\n"
                    "3. Re-run the browse session to rebuild a fresh profile\n"
                    "4. If issues persist, reinstall Playwright browsers: playwright install chromium")
                logger.error(f"Chromium profile corruption detected: {e}")
                return BrowseResponse(
                    status="failure",
                    message=error_msg
                )

            # Version compatibility guidance
            if "version" in msg_lower or "compatib" in msg_lower:
                error_msg = (
                    f"Chromium/Playwright version compatibility issue: {str(e)}\n"
                    "Troubleshooting:\n"
                    "1. Update Playwright and browsers: pip install -U playwright && playwright install chromium\n"
                    "2. Ensure system Chromium matches Playwright's expected version\n"
                    "3. Consider using the Camoufox engine as a temporary workaround"
                )
                logger.error(f"Chromium version compatibility issue: {e}")
                return BrowseResponse(
                    status="failure",
                    message=error_msg
                )

            # Re-raise other runtime errors to be handled by generic block
            raise

        except OSError as e:
            # Disk space or filesystem-related issues
            msg_lower = str(e).lower()
            error_msg = (
                f"Disk space or filesystem error during Chromium browse: {str(e)}\n"
                "Troubleshooting:\n"
                "1. Free up disk space for the Chromium user data directory\n"
                f"2. Verify write permissions to: {getattr(app_config.get_settings(), 'chromium_runtime_effective_user_data_dir', None) or "
                f"os.path.abspath(user_data_dir)}\n"
                "3. Consider changing CHROMIUM_USER_DATA_DIR to a drive with more space")
            # Highlight 'no space' explicitly when present
            if "no space" in msg_lower:
                error_msg = "Disk space issue detected (No space left on device).\n" + error_msg
            logger.error(f"Chromium disk space/filesystem error: {e}")
            return BrowseResponse(
                status="failure",
                message=error_msg
            )

        except PermissionError as e:
            # Permission issues
            error_msg = (
                f"Permission error accessing Chromium user data: {str(e)}\n"
                "Troubleshooting:\n"
                "1. Ensure the process has access permissions to the user data directory\n"
                f"2. Check directory path: {getattr(app_config.get_settings(), 'chromium_runtime_effective_user_data_dir', None) or "
                f"os.path.abspath(user_data_dir)}\n"
                "3. Run the service with sufficient privileges or adjust directory ACLs")
            logger.error(f"Chromium permission/access error: {e}")
            return BrowseResponse(
                status="failure",
                message=error_msg
            )

        except TimeoutError as e:
            # Timeouts during browser operations
            error_msg = (
                f"Timeout occurred during Chromium browse session: {str(e)}\n"
                "Troubleshooting:\n"
                "1. Verify display availability for headful sessions\n"
                "2. Check system resource utilization (CPU/RAM) and reduce load\n"
                "3. Try again after restarting the browser or use Camoufox engine"
            )
            logger.error(f"Chromium browse timeout: {e}")
            return BrowseResponse(
                status="failure",
                message=error_msg
            )

        except ConnectionError as e:
            # Network connectivity issues
            error_msg = (
                f"Network/connection error during Chromium browse: {str(e)}\n"
                "Troubleshooting:\n"
                "1. Check internet connectivity and proxy settings\n"
                "2. Ensure firewall or VPN isn't blocking Chromium/Playwright\n"
                "3. Retry the session after network is stable"
            )
            logger.error(f"Chromium browse network connectivity error: {e}")
            return BrowseResponse(
                status="failure",
                message=error_msg
            )

        except MemoryError as e:
            # Insufficient memory issues
            error_msg = (
                f"Insufficient memory for Chromium browse: {str(e)}\n"
                "Troubleshooting:\n"
                "1. Close other applications to free memory\n"
                "2. Reduce concurrent workloads and try again\n"
                "3. Consider using Camoufox engine which may have lower memory footprint"
            )
            logger.error(f"Chromium browse memory error: {e}")
            return BrowseResponse(
                status="failure",
                message=error_msg
            )

        except ImportError as e:
            error_msg = (
                f"Chromium browser engine is not available: {str(e)}\n"
                "To resolve this issue:\n"
                "1. Install the required dependencies: pip install 'scrapling[chromium]'\n"
                "2. Ensure Playwright browsers are installed: playwright install chromium\n"
                "3. Alternatively, use the Camoufox engine by setting 'engine': 'camoufox' in your request"
            )
            logger.error(f"Chromium dependencies missing: {e}")
            return BrowseResponse(
                status="failure",
                message=error_msg
            )

        except Exception as e:
            error_msg = (
                f"Chromium browse session failed: {str(e)}\n"
                "Troubleshooting steps:\n"
                "1. Check that Chromium/Chrome is properly installed\n"
                "2. Verify display settings if running in headful mode\n"
                "3. Check available disk space for user data directory\n"
                "4. Try running with Camoufox engine as an alternative"
            )
            logger.error(f"Chromium browse session failed: {e}")
            return BrowseResponse(
                status="failure",
                message=error_msg
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
