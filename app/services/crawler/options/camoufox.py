import os
from typing import Dict, Any, Optional, Tuple

import app.core.config as app_config
from app.services.crawler.core.interfaces import IFetchArgComposer


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

        # User data directory with parameter detection
        if hasattr(payload, 'force_user_data') and payload.force_user_data is True and settings.camoufox_user_data_dir:
            user_data_param = None
            for param in ("user_data_dir", "profile_dir", "profile_path", "user_data"):
                if getattr(caps, param, False):
                    user_data_param = param
                    break
            if user_data_param:
                try:
                    os.makedirs(settings.camoufox_user_data_dir, exist_ok=True)
                except Exception:
                    pass
                else:
                    additional_args[user_data_param] = settings.camoufox_user_data_dir

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