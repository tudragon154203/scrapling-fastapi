import os
from typing import Dict, Any, Optional

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest
from app.services.crawler.core.interfaces import IOptionsResolver
from app.services.crawler.core.types import CrawlOptions


class OptionsResolver(IOptionsResolver):
    """Resolver for crawl options with legacy compatibility."""
    
    def resolve(self, request: CrawlRequest, settings) -> CrawlOptions:
        """Resolve effective options from request and settings."""
        wait_selector = request.wait_selector or request.x_wait_for_selector

        timeout_ms: int = (
            request.timeout_ms if request.timeout_ms is not None else settings.default_timeout_ms
        )

        wait_ms: Optional[int] = None
        if request.x_wait_time is not None:
            wait_ms = int(request.x_wait_time * 1000)

        # Determine headless mode: respect x_force_headful, otherwise use .env setting
        if request.x_force_headful is True:
            try:
                import platform  # local import to avoid module-level cost
                if platform.system().lower() == "windows":
                    headless = False
                else:
                    # On non-Windows, ignore headful request per legacy behavior
                    headless = settings.default_headless
            except Exception:
                # If platform detection fails, fall back to forcing headful
                headless = False
        else:
            # If x_force_headful is False or None, respect the .env setting
            headless = settings.default_headless

        network_idle: bool = (
            request.network_idle if request.network_idle is not None else settings.default_network_idle
        )

        # Convert to CrawlOptions and then to dict for compatibility
        options = CrawlOptions(
            headless=headless,
            network_idle=network_idle,
            timeout=timeout_ms // 1000,  # Convert to seconds for compatibility
            wait_for_selector=wait_selector
        )

        return {
            "wait_selector": wait_selector,
            "timeout_ms": timeout_ms,
            "wait_ms": wait_ms,
            "headless": headless,
            "network_idle": network_idle,
            "wait_selector_state": request.wait_selector_state,
        }