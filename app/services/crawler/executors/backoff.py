import random
from app.services.common.interfaces import IBackoffPolicy


class BackoffPolicy(IBackoffPolicy):
    """Configurable backoff policy for retry attempts."""

    def __init__(self, base_ms: int = 1000, max_ms: int = 30000, jitter_ms: int = 500):
        self.base_ms = base_ms
        self.max_ms = max_ms
        self.jitter_ms = jitter_ms

    def delay_for_attempt(self, attempt_idx: int) -> float:
        """Calculate delay for the given attempt index in seconds."""
        delay_ms = min(self.max_ms, self.base_ms * (2 ** attempt_idx)) + random.randint(0, self.jitter_ms)
        return delay_ms / 1000.0

    @classmethod
    def from_settings(cls, settings) -> 'BackoffPolicy':
        """Create backoff policy from settings."""
        return cls(
            base_ms=getattr(settings, 'retry_backoff_base_ms', 1000),
            max_ms=getattr(settings, 'retry_backoff_max_ms', 30000),
            jitter_ms=getattr(settings, 'retry_jitter_ms', 500)
        )
