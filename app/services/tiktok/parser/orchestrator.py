"""
Main strategy coordination for TikTok parsing
"""
import logging
from typing import List, Dict, Any

from app.services.tiktok.parser.html_parser import extract_video_data_from_html

logger = logging.getLogger(__name__)


class TikTokSearchParser:
    """
    Parses TikTok search results HTML to extract video data.
    """

    def parse(self, html: str) -> List[Dict[str, Any]]:
        """
        Parses the provided HTML content and extracts TikTok video data.
        """
        if not html:
            logger.warning("Empty HTML content provided for parsing.")
            return []

        # Use the HTML parser to extract video data
        return extract_video_data_from_html(html)