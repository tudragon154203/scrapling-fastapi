"""Context managers encapsulating runtime flag management for browse sessions."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Callable, ContextManager, Optional, Tuple


CleanupFn = Optional[Callable[[], None]]
UserDataContextFn = Callable[[str, str], ContextManager[Tuple[str | None, CleanupFn]]]


@contextmanager
def CamoufoxRuntimeContext(
    settings,
    user_data_dir: str,
    *,
    user_data_context_fn: UserDataContextFn,
):
    """Manage Camoufox runtime flags for user-data write sessions."""

    previous_mute = bool(getattr(settings, "camoufox_runtime_force_mute_audio", False))
    previous_mode = getattr(settings, "camoufox_runtime_user_data_mode", None)
    previous_effective = getattr(settings, "camoufox_runtime_effective_user_data_dir", None)

    cleanup: CleanupFn = None
    settings.camoufox_runtime_force_mute_audio = True

    try:
        with user_data_context_fn(user_data_dir, "write") as (effective_dir, cleanup):
            settings.camoufox_runtime_user_data_mode = "write"
            settings.camoufox_runtime_effective_user_data_dir = effective_dir
            yield effective_dir, cleanup
    finally:
        settings.camoufox_runtime_user_data_mode = previous_mode
        settings.camoufox_runtime_effective_user_data_dir = previous_effective
        if callable(cleanup):
            cleanup()
        settings.camoufox_runtime_force_mute_audio = previous_mute


@contextmanager
def ChromiumRuntimeContext(settings, manager, *, mode: str = "write"):
    """Manage Chromium runtime flags while a user-data context is active."""

    previous_mode = getattr(settings, "chromium_runtime_user_data_mode", None)
    previous_effective = getattr(settings, "chromium_runtime_effective_user_data_dir", None)

    cleanup: CleanupFn = None
    try:
        with manager.get_user_data_context(mode) as (effective_dir, cleanup):
            absolute_dir = os.path.abspath(effective_dir) if effective_dir else None
            settings.chromium_runtime_user_data_mode = mode
            settings.chromium_runtime_effective_user_data_dir = absolute_dir
            yield absolute_dir, cleanup
    finally:
        settings.chromium_runtime_user_data_mode = previous_mode
        settings.chromium_runtime_effective_user_data_dir = previous_effective
        if callable(cleanup):
            cleanup()
