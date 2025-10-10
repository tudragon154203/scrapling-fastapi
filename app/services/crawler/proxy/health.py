import logging
import threading
import time
from typing import Dict, Any
from app.services.common.interfaces import IProxyHealthTracker

logger = logging.getLogger(__name__)


class ProxyHealthTracker(IProxyHealthTracker):
    """Thread-safe proxy health tracker that manages proxy failures and cooldowns."""

    def __init__(self):
        self._health_map: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        # Expose the internal store for compatibility with existing test functions
        self.health_map = self._health_map

    def mark_failure(self, proxy: str) -> None:
        """Mark a proxy as failed and potentially mark it as unhealthy."""
        with self._lock:
            if proxy not in self._health_map:
                self._health_map[proxy] = {"failures": 0, "unhealthy_until": 0}

            ht = self._health_map[proxy]
            ht["failures"] += 1

    def mark_success(self, proxy: str) -> None:
        """Mark a proxy as successful, resetting its failure count."""
        with self._lock:
            if proxy in self._health_map:
                self._health_map[proxy]["failures"] = 0
                self._health_map[proxy]["unhealthy_until"] = 0

    def is_unhealthy(self, proxy: str) -> bool:
        """Check if a proxy is currently unhealthy."""
        with self._lock:
            if proxy not in self._health_map:
                return False

            health = self._health_map[proxy]
            if health["unhealthy_until"] > time.time():
                return True

            return False

    def reset(self) -> None:
        """Reset all proxy health states."""
        with self._lock:
            self._health_map.clear()

    def set_unhealthy(self, proxy: str, cooldown_minutes: float = None) -> None:
        """Manually mark a proxy as unhealthy for a specified cooldown period."""
        with self._lock:
            if proxy not in self._health_map:
                self._health_map[proxy] = {"failures": 0, "unhealthy_until": 0}

            cooldown_seconds = (cooldown_minutes or 1) * 60
            self._health_map[proxy]["unhealthy_until"] = time.time() + cooldown_seconds
            logger.debug(f"Proxy {self._redact_proxy(proxy)} marked unhealthy for {cooldown_minutes} minutes")

    def get_failure_count(self, proxy: str) -> int:
        """Get the current failure count for a proxy."""
        with self._lock:
            return self._health_map.get(proxy, {}).get("failures", 0)

    def _redact_proxy(self, proxy: str) -> str:
        """Redact proxy URL for logging."""
        if not proxy:
            return ""
        parts = proxy.split('://')
        if len(parts) == 2:
            proto, rest = parts
            host_port = rest.split('@')[-1]
            if ':' in host_port:
                _, port = host_port.rsplit(':', 1)
                return f"{proto}://***:{port}"
        return proxy


# Global singleton instance for compatibility
_health_tracker_instance = None


def get_health_tracker() -> ProxyHealthTracker:
    """Get the global health tracker instance."""
    global _health_tracker_instance
    if _health_tracker_instance is None:
        _health_tracker_instance = ProxyHealthTracker()
    return _health_tracker_instance


def reset_health_tracker():
    """Reset health tracker for testing purposes."""
    if _health_tracker_instance is not None:
        _health_tracker_instance.reset()


# Legacy compatibility - expose global health tracker
reset_health_tracker_globals = reset_health_tracker
