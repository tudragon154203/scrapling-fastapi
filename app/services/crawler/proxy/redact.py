from typing import Optional


def redact_proxy(proxy: Optional[str]) -> Optional[str]:
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