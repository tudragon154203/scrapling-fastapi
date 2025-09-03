from typing import Optional

from app.core.config import get_settings
from app.schemas.crawl import CrawlRequest, CrawlResponse


def crawl_generic(payload: CrawlRequest) -> CrawlResponse:
    """Generic crawl using Scrapling's StealthyFetcher.

    First sprint keeps parameters minimal while supporting
    legacy fields for a smoother transition.
    """
    settings = get_settings()

    # Lazy import so tests that don't exercise crawling won't require the
    # Scrapling dependency to be installed.
    from scrapling.fetchers import StealthyFetcher  # type: ignore

    # Global adaptive selectors can improve resilience on dynamic sites
    StealthyFetcher.adaptive = True

    # Resolve inputs with sensible defaults and legacy compat
    wait_selector = payload.wait_selector or payload.x_wait_for_selector

    # timeout in ms can come from new field, or x_wait_time seconds
    timeout_ms: int = (
        payload.timeout_ms
        if payload.timeout_ms is not None
        else settings.default_timeout_ms
    )
    if payload.x_wait_time is not None:
        # x_wait_time in seconds -> ms
        timeout_ms = int(payload.x_wait_time * 1000)

    # headless logic: prefer explicit value; legacy x_force_headful wins if set
    headless: bool = (
        payload.headless
        if payload.headless is not None
        else settings.default_headless
    )
    if payload.x_force_headful is True:
        headless = False

    network_idle: bool = (
        payload.network_idle
        if payload.network_idle is not None
        else settings.default_network_idle
    )

    try:
        page = StealthyFetcher.fetch(
            str(payload.url),
            headless=headless,
            network_idle=network_idle,
            wait_selector=wait_selector,
            wait_selector_state=payload.wait_selector_state,
            timeout=timeout_ms,
        )

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
        return CrawlResponse(
            status="failure",
            url=payload.url,
            html=None,
            message=f"Exception during crawl: {type(e).__name__}: {e}",
        )
