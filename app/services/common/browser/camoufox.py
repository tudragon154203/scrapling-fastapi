import logging
import os
import platform
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.services.common.browser import user_data as user_data_mod

logger = logging.getLogger(__name__)


class CamoufoxArgsBuilder:
    """Builder for Camoufox additional arguments and headers."""

    @staticmethod
    def build(payload, settings, caps: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, str]]]:
        """Build Camoufox additional_args and optional extra headers from settings/payload.

        Args:
            payload: Can be CrawlRequest or any other payload type with x_force_user_data field
            settings: Application settings
            caps: Detected capabilities for Camoufox

        Returns:
            Tuple of (additional_args, extra_headers)
        """
        additional_args: Dict[str, Any] = {}

        # Debug: Log that build method was called
        logger.debug(
            f"CamoufoxArgsBuilder.build called with force_user_data="
            f"{getattr(payload, 'force_user_data', None)}, "
            f"camoufox_user_data_dir={getattr(settings, 'camoufox_user_data_dir', None)}"
        )

        # User data directory with Firefox semantics (force profile_dir regardless of capability detection)
        # - Crawl flows: use read-mode clones (temporary)
        # - Browse flows: if BrowseCrawler set write-mode flags on settings, use master directly
        if (
            hasattr(payload, "force_user_data")
            and payload.force_user_data is True
            and settings.camoufox_user_data_dir
        ):
            try:
                write_mode, write_dir = CamoufoxArgsBuilder._runtime_user_data_overrides(
                    settings
                )

                if write_mode == "write" and write_dir:
                    # Use master directory directly (lock managed by BrowseCrawler)
                    logger.debug(f"Using WRITE user data directory: {write_dir}")
                    resolved_path = CamoufoxArgsBuilder._resolve_path(write_dir)
                    # Ensure directory exists and is writable
                    Path(resolved_path).mkdir(parents=True, exist_ok=True)
                    if not os.access(resolved_path, os.W_OK):
                        raise PermissionError(f"User data directory is not writable: {resolved_path}")
                    additional_args["user_data_dir"] = resolved_path
                else:
                    # Default to read-mode clone for regular crawl flows
                    with user_data_mod.user_data_context(
                        settings.camoufox_user_data_dir, 'read'
                    ) as (effective_dir, cleanup):
                        logger.debug(f"Using user data directory: {effective_dir}")
                        resolved_path = CamoufoxArgsBuilder._resolve_path(effective_dir)
                        # Ensure directory exists and is writable
                        Path(resolved_path).mkdir(parents=True, exist_ok=True)
                        if not os.access(resolved_path, os.W_OK):
                            raise PermissionError(f"User data directory is not writable: {resolved_path}")
                        additional_args["user_data_dir"] = resolved_path
                        # Store cleanup function in additional_args for post-fetch cleanup
                        additional_args['_user_data_cleanup'] = cleanup

            except Exception as e:
                logger.warning(f"Failed to setup user data directory: {e}")
                warnings.warn(str(e), UserWarning)
                # Continue without user-data on error

        if getattr(settings, "camoufox_disable_coop", False):
            additional_args["disable_coop"] = True
        if getattr(settings, "camoufox_virtual_display", None):
            additional_args["virtual_display"] = settings.camoufox_virtual_display

        force_mute = bool(getattr(payload, "force_mute_audio", False))
        if not force_mute:
            force_mute = bool(
                getattr(settings, "camoufox_runtime_force_mute_audio", False)
            )
        if not force_mute:
            force_mute = bool(getattr(settings, "_camoufox_force_mute_audio", False))
        if force_mute:
            existing_prefs = additional_args.get("firefox_user_prefs")
            firefox_prefs = dict(existing_prefs) if isinstance(existing_prefs, dict) else {}
            firefox_prefs.setdefault("media.volume_scale", 0.0)
            firefox_prefs.setdefault("media.default_volume", 0.0)
            firefox_prefs.setdefault("dom.audiochannel.mutedByDefault", True)
            additional_args["firefox_user_prefs"] = firefox_prefs

        # Do NOT pass `solve_cloudflare` via additional_args.
        # It is a top-level argument of StealthyFetcher.fetch and forwarding it inside
        # Camoufox launch options causes Playwright to receive an unexpected kwarg.

        extra_headers: Optional[Dict[str, str]] = None
        if getattr(settings, "camoufox_locale", None):
            additional_args["locale"] = settings.camoufox_locale
            extra_headers = {"Accept-Language": settings.camoufox_locale}

        win = CamoufoxArgsBuilder._parse_window_size(getattr(settings, "camoufox_window", None))
        if win:
            additional_args["window"] = win

        # Do not pass `wait` via additional_args; it is a top-level
        # StealthyFetcher.fetch parameter and forwarding it into Camoufox
        # options will be passed into Playwright launch where it's invalid.

        # Debug logging for additional_args keys
        if additional_args:
            logger.debug(f"Camoufox additional_args keys: {list(additional_args.keys())}")

        return additional_args, extra_headers

    @staticmethod
    def _parse_window_size(value: Optional[str]) -> Optional[Tuple[int, int]]:
        """Parse a window size string into (width, height)."""
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

    @staticmethod
    def _runtime_user_data_overrides(settings) -> Tuple[Optional[str], Optional[str]]:
        """Extract sanitized runtime user-data overrides from settings."""

        mode = getattr(settings, "camoufox_runtime_user_data_mode", None)
        if mode is None:
            mode = getattr(settings, "_camoufox_user_data_mode", None)
        normalized_mode = mode.lower() if isinstance(mode, str) else None

        raw_dir = getattr(settings, "camoufox_runtime_effective_user_data_dir", None)
        if raw_dir is None:
            raw_dir = getattr(settings, "_camoufox_effective_user_data_dir", None)
        if isinstance(raw_dir, (str, os.PathLike)):
            try:
                normalized_dir = os.fspath(raw_dir)
            except TypeError:
                normalized_dir = None
        else:
            normalized_dir = None

        return normalized_mode, normalized_dir

    @staticmethod
    def _resolve_path(path_value: str) -> str:
        """Return an absolute path for the provided path string."""

        if platform.system() == "Windows":
            return str(Path(path_value).resolve())
        return os.path.abspath(path_value)
