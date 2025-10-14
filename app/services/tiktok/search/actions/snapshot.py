"""HTML snapshot helpers for TikTok search results."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any


class SearchSnapshotCapturer:
    """Capture and optionally persist HTML snapshots of search results."""

    def __init__(
        self,
        *,
        logger: logging.Logger,
        save_html: bool,
        snapshot_path: Path,
        search_query: str,
    ) -> None:
        self._logger = logger
        self._save_html = save_html
        self._snapshot_path = snapshot_path
        self._search_query = search_query

    def capture_html(self, page: Any) -> str:
        """Capture page HTML and optionally persist it."""
        self._logger.debug("Capturing HTML content...")
        try:
            html_content = page.content()
            self._logger.debug(
                "Captured HTML content length: %s", len(html_content)
            )
            if self._save_html and html_content:
                self._persist_html_snapshot(html_content)
            return html_content
        except Exception as exc:
            self._logger.error("Failed to capture HTML content: %s", exc)
            return ""

    def _persist_html_snapshot(self, html_content: str) -> None:
        """Persist captured HTML to disk for debugging."""
        try:
            snapshot_path = self._snapshot_path
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            header = (
                f"<!-- TikTok Search Results Snapshot - {timestamp} -->\n"
                f"<!-- Search query: {self._search_query} -->\n\n"
            )
            try:
                snapshot_path.write_text(header + html_content, encoding="utf-8")
            except UnicodeEncodeError:
                snapshot_path.write_text(
                    header + html_content, encoding="latin-1", errors="replace"
                )
            self._logger.debug("Saved HTML snapshot to %s", snapshot_path)
        except Exception as exc:
            self._logger.warning("Failed to save HTML snapshot: %s", exc)
