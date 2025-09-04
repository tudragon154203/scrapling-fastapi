import random
import time
from typing import Optional, List, Dict, Any

from app.core.config import get_settings
from app.schemas.crawl import CrawlRequest, CrawlResponse


def _load_public_proxies(path: Optional[str]) -> List[str]:
    """Load public proxies from a file.
    
    Public proxies are in the format <ip>:<port> without prefixes.
    They are treated as SOCKS5 proxies by default.
    
    Args:
        path: Path to the proxy list file
        
    Returns:
        List of proxy URLs with socks5:// prefix
    """
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            proxies = []
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # If the line doesn't have a prefix, treat it as SOCKS5
                if not line.startswith(("http://", "https://", "socks5://", "socks4://")):
                    # Assume it's in format <ip>:<port>
                    line = f"socks5://{line}"
                proxies.append(line)
            return proxies
    except Exception:
        return []


def _build_attempt_plan(settings, public_proxies: List[str]) -> List[Dict[str, Any]]:
    """Build the attempt plan for retry strategy.
    
    Args:
        settings: Application settings
        public_proxies: List of public proxy URLs
        
    Returns:
        List of attempt configurations
    """
    plan: List[Dict[str, Any]] = []
    
    # Start with direct connection
    plan.append({"mode": "direct", "proxy": None})
    
    # Add public proxies if configured
    for proxy in public_proxies:
        plan.append({"mode": "public", "proxy": proxy})
        
    # Add private proxy if configured
    if settings.private_proxy_url:
        plan.append({"mode": "private", "proxy": settings.private_proxy_url})
        
    # Add final direct attempt as fallback if we have other attempts
    if len(plan) > 1:
        plan.append({"mode": "direct", "proxy": None})
    
    # If we still don't have enough attempts and have public proxies, cycle through them
    if len(plan) < settings.max_retries and public_proxies:
        # Cycle through public proxies to fill remaining attempts
        proxy_index = 0
        while len(plan) < settings.max_retries:
            plan.append({"mode": "public", "proxy": public_proxies[proxy_index]})
            proxy_index = (proxy_index + 1) % len(public_proxies)
    
    # Trim to max_retries if we have too many
    if len(plan) > settings.max_retries:
        plan = plan[:settings.max_retries]
    
    # If we don't have enough attempts (e.g., max_retries > 1 but no proxies configured),
    # add more direct attempts
    while len(plan) < settings.max_retries:
        plan.append({"mode": "direct", "proxy": None})
    
    return plan


def _calculate_backoff_delay(attempt_idx: int, settings) -> float:
    """Calculate backoff delay with exponential growth and jitter.
    
    Args:
        attempt_idx: Current attempt index (0-based)
        settings: Application settings
        
    Returns:
        Delay in seconds
    """
    base = settings.retry_backoff_base_ms
    cap = settings.retry_backoff_max_ms
    jitter = settings.retry_jitter_ms
    
    delay_ms = min(cap, base * (2 ** attempt_idx)) + random.randint(0, jitter)
    return delay_ms / 1000.0


def execute_crawl_with_retries(payload: CrawlRequest) -> CrawlResponse:
    """Execute crawl with retry and proxy strategy.
    
    Args:
        payload: Crawl request payload
        
    Returns:
        Crawl response
    """
    settings = get_settings()
    public_proxies = _load_public_proxies(settings.proxy_list_file_path)
    
    # Build attempt plan
    plan = _build_attempt_plan(settings, public_proxies)
    
    # Resolve inputs with sensible defaults and legacy compat
    wait_selector = payload.wait_selector or payload.x_wait_for_selector

    # timeout in ms comes from new field or defaults; legacy x_wait_time maps to "wait" not timeout
    timeout_ms: int = (
        payload.timeout_ms
        if payload.timeout_ms is not None
        else settings.default_timeout_ms
    )
    wait_ms: Optional[int] = None
    if payload.x_wait_time is not None:
        # x_wait_time in seconds -> ms (fixed delay before capture)
        wait_ms = int(payload.x_wait_time * 1000)

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
    
    last_error = None
    last_status = None

    # Lazy import so tests that don't exercise crawling won't require the
    # Scrapling dependency to be installed.
    try:
        from scrapling.fetchers import StealthyFetcher  # type: ignore

        # Global adaptive selectors can improve resilience on dynamic sites
        StealthyFetcher.adaptive = True

        for i, attempt in enumerate(plan):
            try:
                # Log attempt
                print(f"Attempt {i+1}/{len(plan)} using {attempt['mode']} connection")
                
                page = StealthyFetcher.fetch(
                    str(payload.url),
                    headless=headless,
                    network_idle=network_idle,
                    wait_selector=wait_selector,
                    wait_selector_state=payload.wait_selector_state,
                    timeout=timeout_ms,
                    wait=wait_ms or 0,
                    # TODO: when supported, pass proxy=attempt["proxy"]
                )

                if getattr(page, "status", None) == 200:
                    html = getattr(page, "html_content", None)
                    return CrawlResponse(status="success", url=payload.url, html=html)
                else:
                    last_status = getattr(page, "status", None)
                    last_error = f"Non-200 status: {last_status}"
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"

            # Backoff before next attempt if any remain
            if i < len(plan) - 1:
                delay = _calculate_backoff_delay(i, settings)
                time.sleep(delay)

        return CrawlResponse(
            status="failure", 
            url=payload.url, 
            html=None, 
            message=last_error or "exhausted retries"
        )
    except ImportError:
        # Fallback for tests that don't have scrapling installed
        return CrawlResponse(
            status="failure",
            url=payload.url,
            html=None,
            message="Scrapling library not available",
        )


def crawl_generic(payload: CrawlRequest) -> CrawlResponse:
    """Generic crawl using Scrapling's StealthyFetcher with retry capability.

    First sprint keeps parameters minimal while supporting
    legacy fields for a smoother transition.
    """
    settings = get_settings()
    
    # If retries are disabled or set to 1, use the original implementation
    if settings.max_retries <= 1:
        # Lazy import so tests that don't exercise crawling won't require the
        # Scrapling dependency to be installed.
        try:
            from scrapling.fetchers import StealthyFetcher  # type: ignore

            # Global adaptive selectors can improve resilience on dynamic sites
            StealthyFetcher.adaptive = True

            # Resolve inputs with sensible defaults and legacy compat
            wait_selector = payload.wait_selector or payload.x_wait_for_selector

            # timeout in ms comes from new field or defaults; legacy x_wait_time maps to "wait" not timeout
            timeout_ms: int = (
                payload.timeout_ms
                if payload.timeout_ms is not None
                else settings.default_timeout_ms
            )
            wait_ms: Optional[int] = None
            if payload.x_wait_time is not None:
                # x_wait_time in seconds -> ms (fixed delay before capture)
                wait_ms = int(payload.x_wait_time * 1000)

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
                    wait=wait_ms or 0,
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
        except ImportError:
            # Fallback for tests that don't have scrapling installed
            return CrawlResponse(
                status="failure",
                url=payload.url,
                html=None,
                message="Scrapling library not available",
            )
    else:
        # Use the new retry implementation
        return execute_crawl_with_retries(payload)