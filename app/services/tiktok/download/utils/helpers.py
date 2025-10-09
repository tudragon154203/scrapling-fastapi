"""Utility functions for TikTok download service."""

from __future__ import annotations

import re
from urllib.parse import urlparse
from typing import Optional


def extract_tiktok_video_id(url: str) -> Optional[str]:
    """
    Extract the video ID from a TikTok URL.

    Args:
        url: TikTok video URL

    Returns:
        Video ID if found, None otherwise
    """
    # Handle various TikTok URL formats:
    # https://www.tiktok.com/@username/video/1234567890
    # https://tiktok.com/@username/video/1234567890
    # https://vm.tiktok.com/shortcode/
    # https://v.tiktok.com/shortcode/

    patterns = [
        r'tiktok\.com/@[^/]+/video/(\d+)',  # Standard format
        r'tiktok\.com/@[^/]+/live/(\d+)',   # Live format (shouldn't happen for downloads)
        r'(?:vm|v)\.tiktok\.com/([A-Za-z0-9]+)',  # Short format
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def is_valid_tiktok_url(url: str) -> bool:
    """
    Validate if the URL is a valid TikTok video URL.

    Args:
        url: URL to validate

    Returns:
        True if valid TikTok video URL, False otherwise
    """
    try:
        parsed = urlparse(url.lower())
        valid_domains = ['tiktok.com', 'www.tiktok.com', 'vm.tiktok.com', 'v.tiktok.com']

        return (
            parsed.scheme in ['http', 'https'] and
            any(domain in parsed.netloc for domain in valid_domains) and
            ('/video/' in parsed.path or '/live/' in parsed.path or parsed.netloc in ['vm.tiktok.com', 'v.tiktok.com'])
        )
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe file system storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)

    # Trim whitespace and dots from start/end
    sanitized = sanitized.strip('. ')

    # Ensure it's not empty
    if not sanitized:
        sanitized = 'video'

    # Limit length (typical filesystem limit)
    if len(sanitized) > 255:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        if ext:
            sanitized = name[:255 - len(ext) - 1] + '.' + ext
        else:
            sanitized = sanitized[:255]

    return sanitized


def extract_video_metadata_from_url(url: str) -> dict:
    """
    Extract basic metadata from a TikTok URL.

    Args:
        url: TikTok video URL

    Returns:
        Dictionary with extracted metadata
    """
    video_id = extract_tiktok_video_id(url)

    # Extract username from URL
    username_match = re.search(r'@([^/]+)', url)
    username = username_match.group(1) if username_match else None

    return {
        'id': video_id,
        'username': username,
        'url': url,
    }


def format_file_size(size_bytes: Optional[int]) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    if size_bytes is None:
        return "Unknown"

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
