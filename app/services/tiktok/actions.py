"""Helper utilities for dispatching TikTok executor actions."""
from __future__ import annotations

from typing import Any

from app.services.tiktok.tiktok_executor import TiktokExecutor


async def dispatch_action(executor: TiktokExecutor, action: str, **kwargs: Any) -> Any:
    """Invoke an action on the provided executor."""
    if not hasattr(executor, action):
        raise AttributeError(f"Unknown action: {action}")
    method = getattr(executor, action)
    return await method(**kwargs)
