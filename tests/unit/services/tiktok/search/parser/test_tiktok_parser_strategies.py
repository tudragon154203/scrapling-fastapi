"""Strategy-level tests for the TikTok search parser components."""

from __future__ import annotations

import json

import pytest

from app.services.tiktok.search.parser.html_parser import TikTokHtmlParser
from app.services.tiktok.search.parser.orchestrator import TikTokSearchParser

pytestmark = [pytest.mark.unit]


def _wrap_html(body: str) -> str:
    """Helper to embed snippet into a minimal HTML document."""
    return f"<html><head></head><body>{body}</body></html>"


def test_html_parser_prefers_sigi_state_payload() -> None:
    """SIGI_STATE JSON should be used before other extraction strategies."""
    sigi_state = {
        "ItemModule": {
            "video-1": {
                "id": "video-1",
                "desc": "Primary caption",
                "author": "primary_author",
                "stats": {"diggCount": 12},
                "createTime": "1700000000",
            }
        },
        "UserModule": {"users": {}},
    }
    dom_fallback = """
    <div id=\"column-item-video-container-99\">
        <a href=\"https://www.tiktok.com/@domuser/video/999\">Video Link</a>
    </div>
    """
    html = (
        "<html><head>"
        "<script id=\"SIGI_STATE\" type=\"application/json\">"
        f"{json.dumps(sigi_state)}"
        "</script>"
        "</head><body>"
        f"{dom_fallback}"
        "</body></html>"
    )

    parser = TikTokHtmlParser()
    results = parser.parse(html)

    assert len(results) == 1
    item = results[0]
    assert item == {
        "id": "video-1",
        "caption": "Primary caption",
        "authorHandle": "primary_author",
        "likeCount": 12,
        "uploadTime": "2023-11-14",
        "webViewUrl": "https://www.tiktok.com/@primary_author/video/video-1",
    }


def test_html_parser_uses_extracted_search_items_payload() -> None:
    """Extraction from EXTRACTED_SEARCH_ITEMS should normalize pagination metadata."""
    extracted_payload = [
        {
            "id": "9876543210",
            "caption": "Script provided caption",
            "authorHandle": "@ScriptedAuthor",
            "likeCount": 2048,
            "uploadTime": "2024-02-01",
            "webViewUrl": "https://www.tiktok.com/@scripted/video/9876543210",
            "cursor": "opaque-cursor",  # pagination info that should be ignored
            "hasMore": True,
        }
    ]
    html = _wrap_html(
        "<script id=\"EXTRACTED_SEARCH_ITEMS\" type=\"application/json\">"
        f"{json.dumps(extracted_payload)}"
        "</script>"
    )

    parser = TikTokHtmlParser()
    results = parser.parse(html)

    assert len(results) == 1
    item = results[0]
    assert item == {
        "id": "9876543210",
        "caption": "Script provided caption",
        "authorHandle": "ScriptedAuthor",
        "likeCount": 2048,
        "uploadTime": "2024-02-01",
        "webViewUrl": "https://www.tiktok.com/@scripted/video/9876543210",
    }

    # Ensure pagination metadata from the script is not leaked
    assert "cursor" not in item
    assert "hasMore" not in item


def test_html_parser_falls_back_to_dom_extraction() -> None:
    """When scripts are missing, DOM heuristics should produce normalized results."""
    dom_markup = """
    <div id=\"column-item-video-container-10\">
        <a href=\"/@domuser/video/123456\">Video Link</a>
        <div data-e2e=\"search-card-video-caption\">DOM caption text</div>
        <span class=\"css-1i43xsj\">1.5K</span>
        <time>2024-02-02</time>
    </div>
    """
    html = _wrap_html(dom_markup)

    parser = TikTokHtmlParser()
    results = parser.parse(html)

    assert len(results) == 1
    item = results[0]
    assert item == {
        "id": "123456",
        "caption": "DOM caption text",
        "authorHandle": "domuser",
        "likeCount": 1500,
        "uploadTime": "2024-02-02",
        "webViewUrl": "https://www.tiktok.com/@domuser/video/123456",
    }


def test_html_parser_uses_meta_tags_as_last_resort() -> None:
    """Meta tags should provide data when no other strategy matches."""
    html = (
        "<html><head>"
        "<link rel=\"canonical\" href=\"https://www.tiktok.com/@meta/video/444\" />"
        "<meta property=\"og:description\" content=\"Meta caption\" />"
        "</head><body></body></html>"
    )

    parser = TikTokHtmlParser()
    results = parser.parse(html)

    assert len(results) == 1
    item = results[0]
    assert item == {
        "id": "444",
        "caption": "Meta caption",
        "authorHandle": "meta",
        "likeCount": 0,
        "uploadTime": "",
        "webViewUrl": "https://www.tiktok.com/@meta/video/444",
    }


def test_html_parser_handles_invalid_extracted_items_gracefully() -> None:
    """Malformed EXTRACTED_SEARCH_ITEMS payloads should fall back to DOM parsing."""
    html = _wrap_html(
        "<script id=\"EXTRACTED_SEARCH_ITEMS\">{invalid json</script>"
        "<div id=\"column-item-video-container-1\">"
        "  <a href=\"https://www.tiktok.com/@safe/video/321\">Video</a>"
        "  <div data-e2e=\"search-card-video-caption\">Safe caption</div>"
        "</div>"
    )

    parser = TikTokHtmlParser()
    results = parser.parse(html)

    assert len(results) == 1
    item = results[0]
    assert item["id"] == "321"
    assert item["caption"] == "Safe caption"
    assert item["authorHandle"] == "safe"
    assert item["webViewUrl"].endswith("/321")


def test_search_parser_handles_empty_html() -> None:
    """TikTokSearchParser should return an empty list for empty payloads."""
    parser = TikTokSearchParser()
    assert parser.parse("") == []
