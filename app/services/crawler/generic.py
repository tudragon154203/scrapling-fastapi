import random
import time
import logging
import inspect
import os
from typing import Optional, List, Dict, Any, Tuple

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse

# Global proxy health tracker
health_tracker: Dict[str, Dict[str, Any]] = {}

def reset_health_tracker():
    """Reset health tracker for testing purposes."""
    global health_tracker
    health_tracker.clear()

# Logger
logger = logging.getLogger(__name__)


def _redact_proxy(proxy: Optional[str]) -> Optional[str]:
    """Redact proxy URL for logging."""
    if not proxy:
        return None
    parts = proxy.split('://')
    if len(parts) == 2:
        proto, rest = parts
        # Handle user:pass@host:port
        host_port = rest.split('@')[-1]
        if ':' in host_port:
            host, port = host_port.rsplit(':', 1)
            return f"{proto}://***:{port}"
    return proxy  # fallback


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

    # Prepare public proxies list (shuffle in random mode)
    pubs = list(public_proxies)
    if getattr(settings, "proxy_rotation_mode", "sequential") == "random" and pubs:
        random.shuffle(pubs)

    remaining = max(0, int(getattr(settings, "max_retries", 1)) - 1)  # after initial direct
    include_private = bool(getattr(settings, "private_proxy_url", None))
    reserve_final_direct = remaining > 1  # keep a final direct when we have room

    # Slots available for public proxies
    slots_for_public = remaining - (1 if include_private else 0) - (1 if reserve_final_direct else 0)
    slots_for_public = max(0, slots_for_public)
    for proxy in pubs[:slots_for_public]:
        plan.append({"mode": "public", "proxy": proxy})

    # Add private proxy if configured and we still have capacity
    if include_private and len(plan) < getattr(settings, "max_retries", 1):
        plan.append({"mode": "private", "proxy": settings.private_proxy_url})

    # Add final direct attempt as fallback if we have capacity
    if reserve_final_direct and len(plan) < getattr(settings, "max_retries", 1):
        plan.append({"mode": "direct", "proxy": None})

    # If we still don't have enough attempts, continue with remaining public proxies, then direct
    proxy_index = 0
    while len(plan) < getattr(settings, "max_retries", 1):
        if proxy_index < len(pubs):
            plan.append({"mode": "public", "proxy": pubs[proxy_index]})
            proxy_index += 1
        else:
            plan.append({"mode": "direct", "proxy": None})

    return plan


def _parse_window_size(value: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parse a window size string into (width, height).

    Accepts formats like "1366x768" or "1366,768". Returns None if invalid.
    """
    if not value:
        return None
    raw = value.strip().lower().replace(" ", "")
    sep = "x" if "x" in raw else "," if "," in raw else None
    if not sep:
        return None
    try:
        w_str, h_str = raw.split(sep, 1)
        w, h = int(w_str), int(h_str)
        if w > 0 and h > 0:
            return (w, h)
    except Exception:
        return None
    return None


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
    settings = app_config.get_settings()
    public_proxies = _load_public_proxies(settings.proxy_list_file_path)
    # Debug prints removed for clarity

    # Build candidates list
    candidates = public_proxies.copy()
    if getattr(settings, "private_proxy_url", None):
        candidates.append(settings.private_proxy_url)

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

    # Build Camoufox additional args (user data + stealth extras)
    additional_args: Dict[str, Any] = {}
    if payload.x_force_user_data is True and settings.camoufox_user_data_dir:
        try:
            os.makedirs(settings.camoufox_user_data_dir, exist_ok=True)
        except Exception:
            # Best-effort; if creation fails, continue without persistence
            pass
        else:
            additional_args["user_data_dir"] = settings.camoufox_user_data_dir

    # Optional stealth extras from config
    if getattr(settings, "camoufox_disable_coop", False):
        additional_args["disable_coop"] = True
    if getattr(settings, "camoufox_virtual_display", None):
        additional_args["virtual_display"] = settings.camoufox_virtual_display
    # Locale and matching Accept-Language header
    extra_headers: Optional[Dict[str, str]] = None
    if getattr(settings, "camoufox_locale", None):
        additional_args["locale"] = settings.camoufox_locale
        extra_headers = {"Accept-Language": settings.camoufox_locale}
    # Fixed window size if configured
    win = _parse_window_size(getattr(settings, "camoufox_window", None))
    if win:
        additional_args["window"] = win

    last_error = None
    last_status = None

    # Lazy import so tests that don't exercise crawling won't require the
    # Scrapling dependency to be installed.
    try:
        from scrapling.fetchers import StealthyFetcher  # type: ignore

        # Global adaptive selectors can improve resilience on dynamic sites
        StealthyFetcher.adaptive = True

        # Feature detection for supported fetch kwargs
        _sig = inspect.signature(StealthyFetcher.fetch)
        _fetch_params = set(_sig.parameters.keys())
        _has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in _sig.parameters.values())
        proxy_supported = ('proxy' in _fetch_params) or _has_varkw
        geoip_supported = ('geoip' in _fetch_params) or _has_varkw
        extra_headers_supported = ('extra_headers' in _fetch_params) or _has_varkw
        additional_args_supported = ('additional_args' in _fetch_params) or _has_varkw
        if not proxy_supported:
            logger.warning("StealthyFetcher.fetch does not support proxy parameter, continuing without proxy")

        attempt_count = 0
        proxy_index = 0
        last_used_proxy = None

        # Build attempt plan
        attempt_plan = _build_attempt_plan(settings, public_proxies)
        
        # Prepare for attempts loop
        while attempt_count < settings.max_retries:
            selected_proxy = None
            mode = 'direct'

            if getattr(settings, "proxy_rotation_mode", "sequential") != 'random' or not candidates:
                # For sequential mode, we need to find the next healthy proxy in the attempt plan
                found_healthy_attempt = False
                while attempt_count < settings.max_retries:
                    attempt_config = attempt_plan[attempt_count]
                    candidate_proxy = attempt_config["proxy"]
                    candidate_mode = attempt_config["mode"]
                    
                    # Skip unhealthy proxies (but allow direct connections)
                    if candidate_proxy and health_tracker.get(candidate_proxy, {}).get('unhealthy_until', 0) > time.time():
                        logger.info(f"Attempt {attempt_count+1} skipped - {candidate_mode} proxy {_redact_proxy(candidate_proxy)} is unhealthy")
                        attempt_count += 1
                        continue
                    
                    # Found healthy proxy or direct connection
                    selected_proxy = candidate_proxy
                    mode = candidate_mode
                    found_healthy_attempt = True
                    break
                
                if not found_healthy_attempt:
                    # No healthy proxy found at this time
                    break
            else:
                # For random mode, dynamically select a healthy proxy
                healthy_proxies = [p for p in candidates if health_tracker.get(p, {}).get('unhealthy_until', 0) <= time.time()]
                if healthy_proxies:
                    # Avoid immediate repetition when multiple healthy proxies are available
                    if len(healthy_proxies) > 1 and last_used_proxy in healthy_proxies:
                        healthy_proxies.remove(last_used_proxy)
                    selected_proxy = random.choice(healthy_proxies)
                    # Determine mode
                    if selected_proxy == getattr(settings, "private_proxy_url", None):
                        mode = 'private'
                    else:
                        mode = 'public'
                else:
                    # No healthy proxies, use direct or private
                    if getattr(settings, "private_proxy_url", None) and health_tracker.get(settings.private_proxy_url, {}).get('unhealthy_until', 0) <= time.time():
                        selected_proxy = settings.private_proxy_url
                        mode = 'private'
                    else:
                        selected_proxy = None
                        mode = 'direct'

            # Log attempt
            redacted_proxy = _redact_proxy(selected_proxy)
            logger.info(f"Attempt {attempt_count+1} using {mode} connection, proxy: {redacted_proxy}")

            try:
                # Build kwargs safely based on supported params
                geoip_enabled = bool(getattr(settings, "camoufox_geoip", True) and selected_proxy)
                fetch_kwargs: Dict[str, Any] = dict(
                    headless=headless,
                    network_idle=network_idle,
                    wait_selector=wait_selector,
                    wait_selector_state=payload.wait_selector_state,
                    timeout=timeout_ms,
                    wait=wait_ms or 0,
                )
                if proxy_supported and selected_proxy:
                    fetch_kwargs["proxy"] = selected_proxy
                if geoip_supported and geoip_enabled:
                    fetch_kwargs["geoip"] = True
                if additional_args_supported and additional_args:
                    fetch_kwargs["additional_args"] = additional_args
                if extra_headers_supported and extra_headers:
                    fetch_kwargs["extra_headers"] = extra_headers

                page = StealthyFetcher.fetch(str(payload.url), **fetch_kwargs)

                if getattr(page, "status", None) == 200:
                    html = getattr(page, "html_content", None)
                    # Success: reset health
                    if selected_proxy:
                        health_tracker[selected_proxy] = {'failures': 0, 'unhealthy_until': 0}
                        logger.info(f"Proxy {redacted_proxy} recovered")
                    logger.info(f"Attempt {attempt_count+1} outcome: success")
                    return CrawlResponse(status="success", url=payload.url, html=html)
                else:
                    last_status = getattr(page, "status", None)
                    last_error = f"Non-200 status: {last_status}"
                    # Failure: update health
                    if selected_proxy:
                        ht = health_tracker.setdefault(selected_proxy, {'failures': 0, 'unhealthy_until': 0})
                        ht['failures'] += 1
                        if ht['failures'] >= settings.proxy_health_failure_threshold:
                            ht['unhealthy_until'] = time.time() + settings.proxy_unhealthy_cooldown_ms / 1000
                            logger.info(f"Proxy {redacted_proxy} marked unhealthy")
                    logger.info(f"Attempt {attempt_count+1} outcome: failure - {last_error}")
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                # Exception: update health
                if selected_proxy:
                    ht = health_tracker.setdefault(selected_proxy, {'failures': 0, 'unhealthy_until': 0})
                    ht['failures'] += 1
                    if ht['failures'] >= settings.proxy_health_failure_threshold:
                        ht['unhealthy_until'] = time.time() + settings.proxy_unhealthy_cooldown_ms / 1000
                        logger.info(f"Proxy {redacted_proxy} marked unhealthy")
                logger.info(f"Attempt {attempt_count+1} outcome: failure - {last_error}")

            attempt_count += 1
            last_used_proxy = selected_proxy

            # Backoff before next attempt if any remain
            if attempt_count < settings.max_retries:
                delay = _calculate_backoff_delay(attempt_count - 1, settings)
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
    settings = app_config.get_settings()
    
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

            # Camoufox additional args (user data + stealth extras)
            additional_args: Dict[str, Any] = {}
            if payload.x_force_user_data is True and settings.camoufox_user_data_dir:
                try:
                    os.makedirs(settings.camoufox_user_data_dir, exist_ok=True)
                except Exception:
                    pass
                else:
                    additional_args["user_data_dir"] = settings.camoufox_user_data_dir

            if getattr(settings, "camoufox_disable_coop", False):
                additional_args["disable_coop"] = True
            if getattr(settings, "camoufox_virtual_display", None):
                additional_args["virtual_display"] = settings.camoufox_virtual_display

            extra_headers: Optional[Dict[str, str]] = None
            if getattr(settings, "camoufox_locale", None):
                additional_args["locale"] = settings.camoufox_locale
                extra_headers = {"Accept-Language": settings.camoufox_locale}

            win = _parse_window_size(getattr(settings, "camoufox_window", None))
            if win:
                additional_args["window"] = win

            try:
                # Feature detection for supported fetch kwargs
                _sig = inspect.signature(StealthyFetcher.fetch)
                _fetch_params = set(_sig.parameters.keys())
                _has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in _sig.parameters.values())
                proxy_supported = ('proxy' in _fetch_params) or _has_varkw
                geoip_supported = ('geoip' in _fetch_params) or _has_varkw
                extra_headers_supported = ('extra_headers' in _fetch_params) or _has_varkw
                additional_args_supported = ('additional_args' in _fetch_params) or _has_varkw
                if not proxy_supported:
                    logger.warning("StealthyFetcher.fetch does not support proxy parameter, continuing without proxy")

                # For single attempt, use private proxy if configured
                selected_proxy = getattr(settings, "private_proxy_url", None) or None

                # GeoIP spoofing is recommended when using proxies
                geoip_enabled = bool(getattr(settings, "camoufox_geoip", True) and selected_proxy)

                fetch_kwargs: Dict[str, Any] = dict(
                    headless=headless,
                    network_idle=network_idle,
                    wait_selector=wait_selector,
                    wait_selector_state=payload.wait_selector_state,
                    timeout=timeout_ms,
                    wait=wait_ms or 0,
                )
                if proxy_supported and selected_proxy:
                    fetch_kwargs["proxy"] = selected_proxy
                if geoip_supported and geoip_enabled:
                    fetch_kwargs["geoip"] = True
                if additional_args_supported and additional_args:
                    fetch_kwargs["additional_args"] = additional_args
                if extra_headers_supported and extra_headers:
                    fetch_kwargs["extra_headers"] = extra_headers

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
