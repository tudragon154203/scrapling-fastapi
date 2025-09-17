"""
Main strategy coordination for TikTok parsing
"""
import logging
from typing import Any, Dict, List

from .html_parser import TikTokHtmlParser

logger = logging.getLogger(__name__)


class TikTokSearchParser:
    """Parses TikTok search results HTML to extract video data."""

    def __init__(self) -> None:
        self._html_parser = TikTokHtmlParser()

    def parse(self, html: str) -> List[Dict[str, Any]]:
        """Parses the provided HTML content and extracts TikTok video data."""
        if not html:
            logger.warning("Empty HTML content provided for parsing.")
            return []

        return self._html_parser.parse(html)
