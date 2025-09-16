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


def test_from_sigi_state_handles_empty_item_module() -> None:
    """An empty or missing ItemModule should yield no results."""
    empty_html = _wrap_sigi_state({"ItemModule": {}, "UserModule": {}})
    missing_html = _wrap_sigi_state({"UserModule": {"users": {}}})

    assert _from_sigi_state(empty_html) == []
    assert _from_sigi_state(missing_html) == []


def test_from_sigi_state_handles_missing_user_module() -> None:
    """Items are parsed even when the UserModule block is absent."""
    html = _wrap_sigi_state(
        {
            "ItemModule": {
                "789": {
                    "id": 789,
                    "desc": "Direct author",  # ensure non-string id is converted
                    "author": "directAuthor",
                    "stats": {"diggCount": 12},
                    "createTime": "1700000001",
                }
            }
        }
    )

    results = _from_sigi_state(html)
    assert len(results) == 1
    video = results[0]
    assert video["id"] == "789"
    assert video["authorHandle"] == "directAuthor"
    assert video["likeCount"] == 12
    assert video["webViewUrl"] == "https://www.tiktok.com/@directAuthor/video/789"


def test_from_sigi_state_handles_empty_users_dictionary() -> None:
    """Missing author mappings fall back to anonymous video URLs."""
    html = _wrap_sigi_state(
        {
            "ItemModule": {
                "needUser": {
                    "id": "needUser",
                    "desc": "Requires user lookup",
                    "authorId": "ghost",
                    "stats": {},
                }
            },
            "UserModule": {"users": {}},
        }
    )

    results = _from_sigi_state(html)
    assert len(results) == 1
    video = results[0]
    assert video["authorHandle"] == ""
    assert video["webViewUrl"] == "https://www.tiktok.com/video/needUser"


def test_from_sigi_state_handles_nonexistent_author_ids() -> None:
    """Unknown authorId references should not cause errors."""
    html = _wrap_sigi_state(
        {
            "ItemModule": {
                "ghost": {
                    "id": "ghost",
                    "authorId": "missing",
                    "stats": {},
                    "createTime": "1700000300",
                }
            },
            "UserModule": {"users": {"someone": {"id": "other", "uniqueId": "otherUser"}}},
        }
    )

    results = _from_sigi_state(html)
    assert results[0]["authorHandle"] == ""
    assert results[0]["webViewUrl"] == "https://www.tiktok.com/video/ghost"


def test_from_sigi_state_skips_invalid_video_ids() -> None:
    """Items with blank identifiers are ignored."""
    html = _wrap_sigi_state(
        {
            "ItemModule": {
                "  ": {"id": "", "desc": "bad id", "stats": {}},
                "valid": {"id": "valid", "desc": "ok", "stats": {}},
            }
        }
    )

    results = _from_sigi_state(html)
    assert {video["id"] for video in results} == {"valid"}


def test_from_sigi_state_handles_non_positive_like_counts() -> None:
    """Negative and zero like counts are preserved from stats."""
    html = _wrap_sigi_state(
        {
            "ItemModule": {
                "neg": {
                    "id": "neg",
                    "author": "tester",
                    "stats": {"diggCount": -5},
                },
                "zero": {
                    "id": "zero",
                    "author": "tester",
                    "stats": {"likeCount": 0},
                },
            }
        }
    )

    results = {video["id"]: video for video in _from_sigi_state(html)}
    assert results["neg"]["likeCount"] == -5
    assert results["zero"]["likeCount"] == 0


def test_from_sigi_state_handles_missing_create_time_and_stats() -> None:
    """Missing optional fields default to empty strings and zero counts."""
    html = _wrap_sigi_state(
        {
            "ItemModule": {
                "nocreate": {
                    "id": "nocreate",
                    "author": "tester",
                    "desc": "No timestamp",
                }
            }
        }
    )

    results = _from_sigi_state(html)
    assert results[0]["uploadTime"] == ""
    assert results[0]["likeCount"] == 0


def test_from_sigi_state_preserves_unhandled_timestamp_formats() -> None:
    """Non-numeric timestamps are returned verbatim for troubleshooting."""
    html = _wrap_sigi_state(
        {
            "ItemModule": {
                "odd": {
                    "id": "odd",
                    "author": "tester",
                    "createTime": "May 1, 2024 10:00",
                }
            }
        }
    )

    results = _from_sigi_state(html)
    assert results[0]["uploadTime"] == "May 1, 2024 10:00"


def test_from_sigi_state_handles_json_missing_required_fields() -> None:
    """Items missing several fields are still processed safely with defaults."""
    html = _wrap_sigi_state({"ItemModule": {"partial": {}}})
    results = _from_sigi_state(html)
    assert len(results) == 1
    video = results[0]
    assert video["id"] == "partial"
    assert video["caption"] == ""
    assert video["authorHandle"] == ""
    assert video["likeCount"] == 0



def test_from_sigi_state_handles_multiple_sigi_state_tags() -> None:
    """Only the first SIGI_STATE script tag is parsed when duplicates exist."""
    first = {"ItemModule": {"first": {"id": "first", "author": "a", "stats": {}}}}
    second = {"ItemModule": {"second": {"id": "second", "author": "b", "stats": {}}}}
    html = (
        "<html><head>"
        "<script id=\"SIGI_STATE\" type=\"application/json\">"
        f"{json.dumps(first)}"
        "</script>"
        "<script id=\"SIGI_STATE\" type=\"application/json\">"
        f"{json.dumps(second)}"
        "</script>"
        "</head></html>"
    )

    results = _from_sigi_state(html)
    assert {video["id"] for video in results} == {"first"}


def test_from_sigi_state_handles_assignment_pattern() -> None:
    """window.SIGI_STATE assignments are parsed as a fallback pattern."""
    html = "window.SIGI_STATE = " + json.dumps(
        {
            "ItemModule": {
                "assignment": {
                    "id": "assignment",
                    "author": "classPattern",
                    "stats": {},
                }
            }
        }
    ) + ";"

    results = _from_sigi_state(html)
    assert {video["id"] for video in results} == {"assignment"}


def test_from_sigi_state_handles_additional_script_attributes() -> None:
    """SIGI_STATE script tags with extra attributes (e.g., class) are supported."""
    html = (
        "<script class=\"lazy-data\" id=\"SIGI_STATE\" type=\"application/json\">"
        + json.dumps(
            {
                "ItemModule": {
                    "extra": {
                        "id": "extra",
                        "author": "withClass",
                        "stats": {},
                    }
                }
            }
        )
        + "</script>"
    )

    results = _from_sigi_state(html)
    assert {video["id"] for video in results} == {"extra"}


def test_from_sigi_state_handles_html_without_sigi_state() -> None:
    """HTML documents without SIGI_STATE content return no videos."""
    html = "<html><body><p>No scripts here</p></body></html>"
    assert _from_sigi_state(html) == []
