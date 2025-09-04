import logging
from typing import Dict, Any, Optional, Callable

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse

from ..utils.options import _resolve_effective_options, _build_camoufox_args
from ..utils.fetch import _detect_fetch_capabilities, _compose_fetch_kwargs, _simple_http_fetch


logger = logging.getLogger(__name__)


def crawl_single_attempt(payload: CrawlRequest, page_action: Optional[Callable] = None) -> CrawlResponse:
    """Single-attempt crawl using StealthyFetcher (no retry)."""
    settings = app_config.get_settings()

    # Resolve options and potential lightweight headers early so we can fallback if needed
    options = _resolve_effective_options(payload, settings)
    additional_args, extra_headers = _build_camoufox_args(payload, settings, caps={})

    try:
        from scrapling.fetchers import StealthyFetcher  # type: ignore

        StealthyFetcher.adaptive = True

        caps = _detect_fetch_capabilities(StealthyFetcher.fetch)
        additional_args, extra_headers = _build_camoufox_args(payload, settings, caps)

        caps = _detect_fetch_capabilities(StealthyFetcher.fetch)
        if not caps.get("proxy"):
            logger.warning(
                "StealthyFetcher.fetch does not support proxy parameter, continuing without proxy"
            )

        selected_proxy = getattr(settings, "private_proxy_url", None) or None

        fetch_kwargs = _compose_fetch_kwargs(
            options=options,
            caps=caps,
            selected_proxy=selected_proxy,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=settings,
            page_action=page_action,
        )

        page = StealthyFetcher.fetch(str(payload.url), **fetch_kwargs)

        if getattr(page, "status", None) == 200:
            html = getattr(page, "html_content", None)
            min_len = int(getattr(settings, "min_html_content_length", 500) or 0)
            if html and len(html) >= min_len:
                return CrawlResponse(status="success", url=payload.url, html=html)
            else:
                msg = f"HTML too short (<{min_len} chars); suspected bot detection"
                return CrawlResponse(status="failure", url=payload.url, html=None, message=msg)
        else:
            return CrawlResponse(
                status="failure",
                url=payload.url,
                html=None,
                message=f"HTTP status: {getattr(page, 'status', 'unknown')}",
            )
    except Exception as e:
        if isinstance(e, ImportError):
            return CrawlResponse(
                status="failure",
                url=payload.url,
                html=None,
                message="Scrapling library not available",
            )
        # Attempt a very small HTTP-only fallback to handle Playwright sync-in-async errors
        msg = f"{type(e).__name__}: {e}"
        if ("Playwright" in msg) or ("asyncio loop" in msg) or ("Async API" in msg):
            fallback = _simple_http_fetch(str(payload.url), timeout_ms=options["timeout_ms"], extra_headers=extra_headers)
            if int(fallback.get("status", 0)) == 200 and fallback.get("html_content"):
                html = fallback.get("html_content")
                min_len = int(getattr(settings, "min_html_content_length", 500) or 0)
                if html and len(html) >= min_len:
                    return CrawlResponse(status="success", url=payload.url, html=html)
                else:
                    return CrawlResponse(
                        status="failure",
                        url=payload.url,
                        html=None,
                        message=f"HTML too short (<{min_len} chars) via fallback",
                    )
        return CrawlResponse(
            status="failure",
            url=payload.url,
            html=None,
            message=f"Exception during crawl: {type(e).__name__}: {e}",
        )
