import os
from typing import Dict, Any, Optional

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest
from app.services.crawler.core.interfaces import IOptionsResolver
from app.services.crawler.core.types import CrawlOptions


class OptionsResolver(IOptionsResolver):
    """Resolver for crawl options with simplified field names."""
    
    def resolve(self, request: CrawlRequest, settings) -> dict[str, Any]:
        """Resolve effective options from request and settings."""
        wait_selector = request.wait_for_selector
        # Only propagate selector state when a selector is provided
        wait_selector_state = request.wait_for_selector_state if wait_selector else None

        timeout_ms: int = (
            (request.timeout_seconds * 1000) if request.timeout_seconds is not None else settings.default_timeout_ms
        )

        # Determine headless mode: respect force_headful, otherwise use .env setting
        if request.force_headful is True:
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
            # If force_headful is False or None, respect the .env setting
            headless = settings.default_headless

        network_idle: bool = (
            request.network_idle if request.network_idle is not None else settings.default_network_idle
        )

        # Return an options dict expected by our fetch arg composer
        return {
            "wait_for_selector": wait_selector,
            "wait_for_selector_state": wait_selector_state,
            "timeout_ms": timeout_ms,
            # include seconds echo for convenience when present
            "timeout_seconds": request.timeout_seconds,
            "headless": headless,
            "network_idle": network_idle,
        }
