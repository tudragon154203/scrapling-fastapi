from typing import Optional

from app.services.crawler.executors.single_executor import SingleAttemptExecutor


class SingleAttemptNoProxy(SingleAttemptExecutor):
    """Single attempt executor that forces no proxy for AusPost endpoint."""

    def _select_proxy(self, settings) -> Optional[str]:
        """Always disable proxy usage for AusPost-specific crawls."""
        return None
