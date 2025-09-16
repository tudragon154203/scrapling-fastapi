"""Tests for parsing TikTok SIGI_STATE JSON payloads."""
import json
from typing import Dict, Any

import pytest

from app.services.tiktok.parser.json_parser import _from_sigi_state


def _wrap_sigi_state(data: Dict[str, Any]) -> str:
    """Embed SIGI_STATE JSON into a HTML script tag."""
    return (
        "<html><head>"
        "<script id=\"SIGI_STATE\" type=\"application/json\">"
        f"{json.dumps(data)}"
        "</script>"
        "</head></html>"
    )


@pytest.fixture
def sigi_state_valid_html() -> str:
    """A payload with multiple items and mixed timestamp formats."""
    data = {
        "ItemModule": {
            "123": {
                "id": "123",
                "desc": "Fun video",
                "author": "testAuthor",
                "stats": {"diggCount": 321},
                "createTime": "1700000000",
            },
            "456": {
                "id": "456",
                "desc": "Second clip",
                "authorName": "@AnotherAuthor",
                "stats": {"likeCount": 7},
                "createTime": "2024-05-01",
            },
        },
        "UserModule": {"users": {}},
    }
    return _wrap_sigi_state(data)


@pytest.fixture
def sigi_state_missing_authors_html() -> str:
    """Payload where author information must be resolved from user mappings."""
    data = {
        "ItemModule": {
            "resolve": {
                "id": "resolve",
                "desc": "Resolve via users",
                "authorId": "uid-1",
                "stats": {},
                "createTime": "2024-01-31T10:00:00Z",
            },
            "fallback": {
                "id": "fallback",
                "desc": "No author info",
                "stats": {},
                "createTime": "",
            },
        },
        "UserModule": {
            "users": {
                "uid-1": {
                    "id": "uid-1",
                    "uniqueId": "resolvedUser",
                }
            }
        },
    }
    return _wrap_sigi_state(data)


@pytest.fixture
def sigi_state_malformed_html() -> str:
    """Payload containing malformed JSON."""
    return (
        "<script id=\"SIGI_STATE\" type=\"application/json\">"
        "{invalid json"
        "</script>"
    )


def test_from_sigi_state_parses_valid_payload(sigi_state_valid_html: str) -> None:
    """Valid SIGI_STATE data is converted to structured results."""
    results = _from_sigi_state(sigi_state_valid_html)
    assert {video["id"] for video in results} == {"123", "456"}

    as_dict = {video["id"]: video for video in results}

    first = as_dict["123"]
    assert first["caption"] == "Fun video"
    assert first["authorHandle"] == "testAuthor"
    assert first["likeCount"] == 321
    assert first["uploadTime"] == "2023-11-14"
    assert first["webViewUrl"] == "https://www.tiktok.com/@testAuthor/video/123"

    second = as_dict["456"]
    assert second["caption"] == "Second clip"
    assert second["authorHandle"] == "AnotherAuthor"
    assert second["likeCount"] == 7
    assert second["uploadTime"] == "2024-05-01"
    assert second["webViewUrl"] == "https://www.tiktok.com/@AnotherAuthor/video/456"


def test_from_sigi_state_resolves_missing_authors(sigi_state_missing_authors_html: str) -> None:
    """Author handles are resolved via UserModule or fall back to anonymous URLs."""
    results = _from_sigi_state(sigi_state_missing_authors_html)
    assert {video["id"] for video in results} == {"resolve", "fallback"}

    as_dict = {video["id"]: video for video in results}

    resolved = as_dict["resolve"]
    assert resolved["authorHandle"] == "resolvedUser"
    assert resolved["webViewUrl"] == "https://www.tiktok.com/@resolvedUser/video/resolve"
    assert resolved["uploadTime"] == "2024-01-31T10:00:00Z"

    fallback = as_dict["fallback"]
    assert fallback["authorHandle"] == ""
    assert fallback["webViewUrl"] == "https://www.tiktok.com/video/fallback"
    assert fallback["uploadTime"] == ""


def test_from_sigi_state_handles_malformed_payload(sigi_state_malformed_html: str) -> None:
    """Malformed SIGI_STATE JSON is ignored gracefully."""
    assert _from_sigi_state(sigi_state_malformed_html) == []
