"""
Persistent Chromium fetcher for maintaining browser profiles across sessions.

This module provides a custom fetcher that uses Playwright's persistent context
to ensure Chromium profiles are properly saved and maintained, unlike DynamicFetcher
which uses ephemeral contexts.
"""

import logging
import os
from typing import Any, Callable, Dict, Optional, Union

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    Page = None
    BrowserContext = None
    Playwright = None
    logger.warning("Playwright not available for persistent Chromium support")


class PageResult:
    """Mock result object to maintain compatibility with existing interface."""

    def __init__(self, page: Page, html_content: Optional[str] = None):
        self.page = page
        self.html_content = html_content or ""
        self.url = page.url if page else ""
        self.status = 200

    def __del__(self):
        """Cleanup when result is destroyed."""
        if hasattr(self, 'page') and self.page:
            try:
                self.page.close()
            except Exception:
                pass


class PersistentChromiumFetcher:
    """
    Chromium fetcher that supports persistent browser contexts.

    Unlike DynamicFetcher which uses ephemeral contexts, this fetcher uses
    Playwright's launch_persistent_context() to maintain browser profiles
    across sessions.
    """

    def __init__(self, user_data_dir: Optional[str] = None):
        """
        Initialize the fetcher with optional user data directory.

        Args:
            user_data_dir: Directory to store Chromium profile data
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is required for persistent Chromium support")

        self.user_data_dir = os.path.abspath(user_data_dir) if user_data_dir else None
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None

        logger.debug(f"PersistentChromiumFetcher initialized with user_data_dir: {self.user_data_dir}")

    def fetch(
        self,
        url: str,
        *,
        headless: bool = True,
        page_action: Optional[Callable[[Page], Any]] = None,
        timeout: int = 30000,
        network_idle: bool = False,
        browser_args: Optional[list] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        useragent: Optional[str] = None,
        wait: Union[int, float] = 0,
        **kwargs
    ) -> PageResult:
        """
        Fetch a URL using Chromium with persistent context support.

        Args:
            url: URL to fetch
            headless: Whether to run in headless mode
            page_action: Optional function to execute on the page
            timeout: Timeout in milliseconds
            network_idle: Whether to wait for network idle
            browser_args: Additional browser arguments
            extra_headers: Extra HTTP headers
            useragent: Custom user agent string
            wait: Time to wait after page load in milliseconds
            **kwargs: Additional arguments ignored for compatibility

        Returns:
            PageResult object with page content
        """
        if self.user_data_dir:
            logger.debug(f"Using persistent Chromium context: {self.user_data_dir}")
        else:
            logger.debug("Using ephemeral Chromium context")

        try:
            with sync_playwright() as p:
                self.playwright = p

                # Prepare browser arguments
                args = browser_args or []

                if self.user_data_dir:
                    # Use persistent context for profile persistence
                    context_options = {
                        "user_data_dir": self.user_data_dir,
                        "headless": headless,
                        "args": args,
                    }

                    # Add extra headers if provided
                    if extra_headers:
                        context_options["extra_http_headers"] = extra_headers

                    # Add user agent if provided
                    if useragent:
                        context_options["user_agent"] = useragent

                    self.context = p.chromium.launch_persistent_context(**context_options)
                    logger.debug("Launched persistent Chromium context")
                else:
                    # Use regular launch for temporary sessions
                    browser = p.chromium.launch(headless=headless, args=args)
                    context_options = {}

                    if extra_headers:
                        context_options["extra_http_headers"] = extra_headers
                    if useragent:
                        context_options["user_agent"] = useragent

                    self.context = browser.new_context(**context_options)
                    logger.debug("Launched ephemeral Chromium context")

                # Create and navigate to page
                page = self.context.new_page()

                try:
                    # Navigate to URL with timeout
                    page.goto(url, timeout=timeout)

                    # Wait for network idle if requested
                    if network_idle:
                        page.wait_for_load_state("networkidle", timeout=timeout)

                    # Wait additional time if specified
                    if wait > 0:
                        page.wait_for_timeout(wait)

                    # Execute page action if provided
                    if page_action:
                        try:
                            result = page_action(page)
                            logger.debug(f"Page action executed successfully: {result}")
                        except Exception as e:
                            logger.warning(f"Page action failed: {e}")

                    # Get page content
                    html_content = page.content()

                    # Return result object
                    return PageResult(page=page, html_content=html_content)

                except Exception as e:
                    # Ensure page is cleaned up on error
                    try:
                        page.close()
                    except Exception:
                        pass
                    raise e

        except Exception as e:
            logger.error(f"Persistent Chromium fetch failed: {e}")
            raise

    def close(self):
        """Close the browser context and cleanup resources."""
        if self.context:
            try:
                self.context.close()
                logger.debug("Chromium context closed")
            except Exception as e:
                logger.warning(f"Error closing Chromium context: {e}")
            finally:
                self.context = None

    def __del__(self):
        """Cleanup on destruction."""
        self.close()


def create_persistent_fetcher(user_data_dir: Optional[str] = None) -> PersistentChromiumFetcher:
    """
    Factory function to create a persistent Chromium fetcher.

    Args:
        user_data_dir: Directory to store Chromium profile data

    Returns:
        PersistentChromiumFetcher instance
    """
    return PersistentChromiumFetcher(user_data_dir=user_data_dir)
