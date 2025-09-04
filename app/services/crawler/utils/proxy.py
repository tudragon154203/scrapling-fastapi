import random
from typing import Optional, List, Dict, Any

# Global proxy health tracker (shared across executors)
health_tracker: Dict[str, Dict[str, Any]] = {}


def reset_health_tracker():
    """Reset health tracker for testing purposes."""
    global health_tracker
    health_tracker.clear()


def _redact_proxy(proxy: Optional[str]) -> Optional[str]:
    """Redact proxy URL for logging."""
    if not proxy:
        return None
    parts = proxy.split('://')
    if len(parts) == 2:
        proto, rest = parts
        host_port = rest.split('@')[-1]
        if ':' in host_port:
            _, port = host_port.rsplit(':', 1)
            return f"{proto}://***:{port}"
    return proxy


def _load_public_proxies(path: Optional[str]) -> List[str]:
    """Load public proxies from a file as socks5:// URLs by default."""
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            proxies = []
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if not line.startswith(("http://", "https://", "socks5://", "socks4://")):
                    line = f"socks5://{line}"
                proxies.append(line)
            return proxies
    except Exception:
        return []


def _select_proxy_for_request(settings, tracking_code: Optional[str] = None) -> Optional[str]:
    """Select a proxy for the given request based on proxy rotation mode.
    
    Args:
        settings: Application settings with proxy configuration
        tracking_code: Optional tracking code for session consistency
        
    Returns:
        Selected proxy URL or None
    """
    if not getattr(settings, "proxy_list_file_path", None) and not getattr(settings, "private_proxy_url", None):
        return None
    
    public_proxies = _load_public_proxies(settings.proxy_list_file_path)
    
    # For requests with tracking codes, prefer consistent private proxy if available
    if tracking_code and getattr(settings, "private_proxy_url", None):
        return settings.private_proxy_url
    
    # If no tracking code or no private proxy, select from public proxies
    if public_proxies:
        mode = getattr(settings, "proxy_rotation_mode", "sequential")
        if mode == "random":
            return random.choice(public_proxies)
        else:
            # Sequential rotation - round-robin selection
            # For simplicity, just return the first proxy for now
            # In a full implementation, you'd track which proxy was used last
            return public_proxies[0]
    
    return None


def _build_attempt_plan(settings, public_proxies: List[str]) -> List[Dict[str, Any]]:
    """Build the attempt plan for retry strategy."""
    plan: List[Dict[str, Any]] = []

    plan.append({"mode": "direct", "proxy": None})

    pubs = list(public_proxies)
    if getattr(settings, "proxy_rotation_mode", "sequential") == "random" and pubs:
        random.shuffle(pubs)

    remaining = max(0, int(getattr(settings, "max_retries", 1)) - 1)
    include_private = bool(getattr(settings, "private_proxy_url", None))
    reserve_final_direct = remaining > 1

    slots_for_public = remaining - (1 if include_private else 0) - (1 if reserve_final_direct else 0)
    slots_for_public = max(0, slots_for_public)
    for proxy in pubs[:slots_for_public]:
        plan.append({"mode": "public", "proxy": proxy})

    if include_private and len(plan) < getattr(settings, "max_retries", 1):
        plan.append({"mode": "private", "proxy": settings.private_proxy_url})

    if reserve_final_direct and len(plan) < getattr(settings, "max_retries", 1):
        plan.append({"mode": "direct", "proxy": None})

    proxy_index = 0
    while len(plan) < getattr(settings, "max_retries", 1):
        if proxy_index < len(pubs):
            plan.append({"mode": "public", "proxy": pubs[proxy_index]})
            proxy_index += 1
        else:
            plan.append({"mode": "direct", "proxy": None})

    return plan

