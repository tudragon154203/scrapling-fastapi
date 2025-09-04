import logging
from typing import Dict, Any, Optional

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse

from ..utils.options import _resolve_effective_options, _build_camoufox_args
from ..utils.fetch import _detect_fetch_capabilities, _compose_fetch_kwargs


logger = logging.getLogger(__name__)


def crawl_single_attempt(payload: CrawlRequest) -> CrawlResponse:
    """Single-attempt crawl using StealthyFetcher (no retry)."""
    settings = app_config.get_settings()

    try:
        from scrapling.fetchers import StealthyFetcher  # type: ignore

        StealthyFetcher.adaptive = True

        options = _resolve_effective_options(payload, settings)
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
        )

        page = StealthyFetcher.fetch(str(payload.url), **fetch_kwargs)

        if getattr(page, "status", None) == 200:
            html = getattr(page, "html_content", None)
            return CrawlResponse(status="success", url=payload.url, html=html)
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
        return CrawlResponse(
            status="failure",
            url=payload.url,
            html=None,
            message=f"Exception during crawl: {type(e).__name__}: {e}",
        )
