"""Tests for HTML snapshot capturing helper."""

from __future__ import annotations

from unittest.mock import Mock

from app.services.tiktok.search.actions.snapshot import SearchSnapshotCapturer


def test_capture_html_returns_content_without_saving(tmp_path):
    page = Mock()
    page.content.return_value = "<html></html>"
    capturer = SearchSnapshotCapturer(
        logger=Mock(),
        save_html=False,
        snapshot_path=tmp_path / "snapshot.html",
        search_query="cats",
    )

    html = capturer.capture_html(page)

    assert html == "<html></html>"
    assert not (tmp_path / "snapshot.html").exists()


def test_capture_html_persists_when_enabled(tmp_path):
    page = Mock()
    page.content.return_value = "<html></html>"
    snapshot_path = tmp_path / "snapshot.html"
    capturer = SearchSnapshotCapturer(
        logger=Mock(),
        save_html=True,
        snapshot_path=snapshot_path,
        search_query="cats",
    )

    html = capturer.capture_html(page)

    assert html == "<html></html>"
    assert snapshot_path.exists()
    written = snapshot_path.read_text(encoding="utf-8")
    assert "cats" in written
