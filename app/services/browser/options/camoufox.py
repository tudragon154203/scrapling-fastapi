import os
import logging
import platform
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

import app.core.config as app_config
from app.services.common.interfaces import IFetchArgComposer
from app.services.browser.options import user_data as user_data_mod

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
        logger.debug(f"CamoufoxArgsBuilder.build called with force_user_data={getattr(payload, 'force_user_data', None)}, camoufox_user_data_dir={getattr(settings, 'camoufox_user_data_dir', None)}")

        # User data directory with Firefox semantics (force profile_dir regardless of capability detection)
        # - Crawl flows: use read-mode clones (temporary)
        # - Browse flows: if BrowseCrawler set write-mode flags on settings, use master directly
        if (hasattr(payload, 'force_user_data') and payload.force_user_data is True and
            settings.camoufox_user_data_dir):
                try:
                    # Check if browse flow requested write mode via settings flags
                    write_mode = getattr(settings, '_camoufox_user_data_mode', None) == 'write'
                    write_dir = getattr(settings, '_camoufox_effective_user_data_dir', None)

                    if write_mode and write_dir:
                        # Use master directory directly (lock managed by BrowseCrawler)
                        logger.debug(f"Using WRITE user data directory: {write_dir}")
                        resolved_path = str(Path(write_dir).resolve()) if platform.system() == 'Windows' else os.path.abspath(write_dir)
                        # Ensure directory exists and is writable
                        Path(resolved_path).mkdir(parents=True, exist_ok=True)
                        if not os.access(resolved_path, os.W_OK):
                            raise PermissionError(f"User data directory is not writable: {resolved_path}")
                        additional_args["user_data_dir"] = resolved_path
                    else:
                        # Default to read-mode clone for regular crawl flows
                        with user_data_mod.user_data_context(settings.camoufox_user_data_dir, 'read') as (effective_dir, cleanup):
                            logger.debug(f"Using user data directory: {effective_dir}")
                            resolved_path = str(Path(effective_dir).resolve()) if platform.system() == 'Windows' else os.path.abspath(effective_dir)
                            # Ensure directory exists and is writable
                            Path(resolved_path).mkdir(parents=True, exist_ok=True)
                            if not os.access(resolved_path, os.W_OK):
                                raise PermissionError(f"User data directory is not writable: {resolved_path}")
                            additional_args["user_data_dir"] = resolved_path
                            # Store cleanup function in additional_args for post-fetch cleanup
                            additional_args['_user_data_cleanup'] = cleanup

                except Exception as e:
                    logger.warning(f"Failed to setup user data directory: {e}")
                    # Continue without user-data on error

        if getattr(settings, "camoufox_disable_coop", False):
            additional_args["disable_coop"] = True
        if getattr(settings, "camoufox_virtual_display", None):
            additional_args["virtual_display"] = settings.camoufox_virtual_display

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
