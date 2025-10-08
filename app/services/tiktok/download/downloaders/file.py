"""File downloader for streaming TikTok videos."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

try:
    import httpx
except Exception:  # pragma: no cover - httpx is provided by test dependencies
    httpx = None

logger = logging.getLogger(__name__)

# Download configuration
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "90"))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class VideoFileDownloader:
    """Downloader for streaming video files from resolved URLs."""

    def __init__(self, timeout: Optional[float] = None):
        """
        Initialize the video file downloader.

        Args:
            timeout: Request timeout in seconds, defaults to REQUEST_TIMEOUT_SECONDS
        """
        self.timeout = timeout or REQUEST_TIMEOUT_SECONDS
        self.logger = logging.getLogger(__name__)

    async def get_file_info(self, url: str, referer: Optional[str] = None) -> dict:
        """
        Get information about the video file without downloading the entire content.

        Args:
            url: Direct video URL
            referer: Optional referer header

        Returns:
            Dictionary with file information (size, headers, etc.)

        Raises:
            RuntimeError: If httpx is not available or request fails
        """
        if httpx is None:
            raise RuntimeError("httpx library is not available")

        headers = {"User-Agent": USER_AGENT}
        if referer:
            headers["Referer"] = referer

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(self.timeout)
            ) as client:
                response = await client.head(url, headers=headers)
                response.raise_for_status()

                content_length = response.headers.get("content-length")
                file_size = int(content_length) if content_length else None

                filename = self._extract_filename_from_url_or_headers(url, response.headers)

                return {
                    "file_size": file_size,
                    "content_type": response.headers.get("content-type"),
                    "filename": filename,
                    "headers": dict(response.headers),
                }
        except Exception as exc:
            logger.error(f"Failed to get file info: {exc}")
            raise RuntimeError(f"Failed to get file info: {exc}") from exc

    async def stream_to_memory(self, url: str, referer: Optional[str] = None) -> bytes:
        """
        Stream the video content to memory.

        Args:
            url: Direct video URL
            referer: Optional referer header

        Returns:
            Video content as bytes

        Raises:
            RuntimeError: If httpx is not available or download fails
        """
        if httpx is None:
            raise RuntimeError("httpx library is not available")

        headers = {"User-Agent": USER_AGENT}
        if referer:
            headers["Referer"] = referer

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(self.timeout)
            ) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    response.raise_for_status()

                    content = b""
                    async for chunk in response.aiter_bytes(chunk_size=1 << 16):
                        content += chunk

                    return content
        except Exception as exc:
            logger.error(f"Failed to stream video to memory: {exc}")
            raise RuntimeError(f"Failed to stream video: {exc}") from exc

    async def stream_to_file(
        self,
        url: str,
        output_path: Path,
        referer: Optional[str] = None
    ) -> Path:
        """
        Stream the video content directly to a file.

        Args:
            url: Direct video URL
            output_path: Output file path (can be directory)
            referer: Optional referer header

        Returns:
            Final file path

        Raises:
            RuntimeError: If httpx is not available or download fails
        """
        if httpx is None:
            raise RuntimeError("httpx library is not available")

        headers = {"User-Agent": USER_AGENT}
        if referer:
            headers["Referer"] = referer

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(self.timeout)
            ) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    response.raise_for_status()

                    final_path = output_path
                    if output_path.is_dir():
                        filename = self._extract_filename_from_url_or_headers(url, response.headers)
                        final_path = output_path / filename

                    final_path.parent.mkdir(parents=True, exist_ok=True)
                    with final_path.open("wb") as fp:
                        async for chunk in response.aiter_bytes(chunk_size=1 << 16):
                            fp.write(chunk)

                    logger.info(f"Video saved to: {final_path}")
                    return final_path
        except Exception as exc:
            logger.error(f"Failed to stream video to file: {exc}")
            raise RuntimeError(f"Failed to download video: {exc}") from exc

    def _extract_filename_from_url_or_headers(
        self,
        url: str,
        headers: dict,
        fallback_name: str = "video.mp4"
    ) -> str:
        """
        Extract a filename from Content-Disposition, query string, or URL path.

        Args:
            url: Video URL
            headers: HTTP response headers
            fallback_name: Default filename if no other can be determined

        Returns:
            Extracted filename
        """
        # Try Content-Disposition header first
        content_disposition = headers.get("content-disposition") or headers.get("Content-Disposition") or ""
        import re
        match = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)\"?", content_disposition)
        if match:
            return unquote(match.group(1))

        # Try query string parameters
        query = parse_qs(urlparse(url).query or "")
        if query.get("filename"):
            return unquote(query["filename"][0])

        # Try URL path
        path_name = Path(urlparse(url).path).name
        return path_name or fallback_name
