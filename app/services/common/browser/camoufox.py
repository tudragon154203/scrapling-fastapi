import logging
import os
import platform
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.services.common.browser import user_data as user_data_mod
import app.core.config as app_config

logger = logging.getLogger(__name__)


_CAMOUFOX_READY = False


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
        skip_ready_check = False

        testing_flag = getattr(settings, "testing", None)
        if isinstance(testing_flag, bool):
            skip_ready_check = testing_flag
        elif os.getenv("PYTEST_CURRENT_TEST"):
            skip_ready_check = True
        else:
            try:
                skip_ready_check = app_config.get_settings().testing
            except Exception:  # pragma: no cover - defensive fallback
                skip_ready_check = False

        if not skip_ready_check:
            env_skip = os.getenv("CAMOUFOX_SKIP_READY_CHECK", "")
            skip_ready_check = env_skip.lower() in {"1", "true", "yes"}

        if skip_ready_check:
            logger.debug("Skipping Camoufox readiness check (testing mode detected)")
        else:
            try:
                CamoufoxArgsBuilder._ensure_camoufox_ready()
            except RuntimeError as exc:
                if os.getenv("PYTEST_CURRENT_TEST") or getattr(settings, "pytest_current_test", None):
                    logger.debug("Camoufox readiness failed in test mode: %s", exc)
                    skip_ready_check = True
                else:
                    raise

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

        # Camoufox must remain muted across all endpoints regardless of payload
        # or runtime settings. Enforce the Firefox preference explicitly instead
        # of relying on configurable flags.
        force_mute = True

        if force_mute:
            existing_prefs = additional_args.get("firefox_user_prefs")
            firefox_prefs = dict(existing_prefs) if isinstance(existing_prefs, dict) else {}
            firefox_prefs.setdefault("dom.audiochannel.mutedByDefault", True)
            additional_args["firefox_user_prefs"] = firefox_prefs

        # Do NOT pass `solve_cloudflare` via additional_args.
        # It is a top-level argument of StealthyFetcher.fetch and forwarding it inside
        # Camoufox launch options causes Playwright to receive an unexpected kwarg.

        extra_headers: Optional[Dict[str, str]] = None
        if getattr(settings, "camoufox_locale", None):
            additional_args["locale"] = settings.camoufox_locale
            extra_headers = {"Accept-Language": settings.camoufox_locale}

        # Merge headers from payload if available
        if hasattr(payload, "headers") and payload.headers:
            payload_headers = payload.headers
            if isinstance(payload_headers, dict) and payload_headers:
                if extra_headers:
                    # Merge with existing headers (payload headers take precedence)
                    extra_headers.update(payload_headers)
                else:
                    extra_headers = dict(payload_headers)

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
    def _ensure_camoufox_ready() -> None:
        """Ensure Camoufox binaries are installed before attempting to launch."""

        global _CAMOUFOX_READY
        if _CAMOUFOX_READY:
            return

        try:
            from camoufox import pkgman  # type: ignore

            pkgman.camoufox_path()
            _CAMOUFOX_READY = True
        except Exception as exc:  # pragma: no cover - depends on system setup
            logger.error("Camoufox installation check failed: %s", exc, exc_info=True)
            raise RuntimeError(
                "Camoufox runtime is not available. Please ensure `camoufox fetch` succeeds."
            ) from exc

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
        normalized_mode = mode.lower() if isinstance(mode, str) and mode else None

        raw_dir = getattr(settings, "camoufox_runtime_effective_user_data_dir", None)
        if raw_dir is None:
            raw_dir = getattr(settings, "_camoufox_effective_user_data_dir", None)
        if isinstance(raw_dir, (str, os.PathLike)) and raw_dir:
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
