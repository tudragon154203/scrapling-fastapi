"""Helpers for determining Scrapling fetcher compatibility."""

from __future__ import annotations

import inspect
from typing import Any, Callable, Optional


def fetch_method_supports_argument(fetcher: Any, argument_name: str) -> bool:
    """Return True if the fetcher.fetch callable supports a given argument."""
    fetch_callable: Optional[Callable[..., Any]]
    if hasattr(fetcher, "fetch"):
        fetch_callable = getattr(fetcher, "fetch")
    elif callable(fetcher):  # pragma: no cover - flexibility for callable inputs
        fetch_callable = fetcher
    else:
        return False

    try:
        signature = inspect.signature(fetch_callable)
    except (
        TypeError,
        ValueError,
    ):  # pragma: no cover - inspect can fail on C extensions
        return False

    parameters = signature.parameters
    if argument_name in parameters:
        return True

    return any(
        param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()
    )
