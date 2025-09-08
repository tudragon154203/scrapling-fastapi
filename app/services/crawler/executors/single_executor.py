import logging
import sys
import asyncio
from typing import Any, Dict, Optional

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.crawler.core.interfaces import IExecutor, PageAction
from app.services.crawler.core.types import FetchCapabilities
from app.services.crawler.adapters.scrapling_fetcher import ScraplingFetcherAdapter, FetchArgComposer
from app.services.crawler.options.resolver import OptionsResolver
from app.services.crawler.options.camoufox import CamoufoxArgsBuilder

logger = logging.getLogger(__name__)


class SingleAttemptExecutor(IExecutor):
    """Single-attempt crawl executor that performs one fetch operation."""
    
    def __init__(self, fetch_client: Optional[ScraplingFetcherAdapter] = None,
                 options_resolver: Optional[OptionsResolver] = None,
                 arg_composer: Optional[FetchArgComposer] = None,
                 camoufox_builder: Optional[CamoufoxArgsBuilder] = None):
        self.fetch_client = fetch_client or ScraplingFetcherAdapter()
        self.options_resolver = options_resolver or OptionsResolver()
        self.arg_composer = arg_composer or FetchArgComposer()
        self.camoufox_builder = camoufox_builder or CamoufoxArgsBuilder()
    
    def execute(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Execute a single crawl attempt."""
        settings = app_config.get_settings()

        # Ensure proper event loop policy on Windows for Playwright
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
        
        # Resolve options and potential lightweight headers early so we can fallback if needed
        options = self.options_resolver.resolve(request, settings)
        additional_args, extra_headers = self.camoufox_builder.build(request, settings, caps={})

        try:
            caps = self.fetch_client.detect_capabilities()
            additional_args, extra_headers = self.camoufox_builder.build(request, settings, caps)

            if not caps.supports_proxy:
                logger.warning(
                    "StealthyFetcher.fetch does not support proxy parameter, continuing without proxy"
                )

            selected_proxy = getattr(settings, "private_proxy_url", None) or None

            fetch_kwargs = self.arg_composer.compose(
                options=options,
                caps=caps,
                selected_proxy=selected_proxy,
                additional_args=additional_args,
                extra_headers=extra_headers,
                settings=settings,
                page_action=page_action,
            )

            page = self.fetch_client.fetch(str(request.url), fetch_kwargs)

            if getattr(page, "status", None) == 200:
                html = getattr(page, "html_content", None)
                min_len = int(getattr(settings, "min_html_content_length", 500) or 0)
                if html and len(html) >= min_len:
                    return CrawlResponse(status="success", url=request.url, html=html)
                else:
                    msg = f"HTML too short (<{min_len} chars); suspected bot detection"
                    return CrawlResponse(status="failure", url=request.url, html=None, message=msg)
            else:
                return CrawlResponse(
                    status="failure",
                    url=request.url,
                    html=None,
                    message=f"HTTP status: {getattr(page, 'status', 'unknown')}",
                )
        except Exception as e:
            if isinstance(e, ImportError):
                return CrawlResponse(
                    status="failure",
                    url=request.url,
                    html=None,
                    message="Scrapling library not available",
                )
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message=f"Exception during crawl: {type(e).__name__}: {e}",
            )
    

