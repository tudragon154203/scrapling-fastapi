import hashlib
import json

import pytest
from fastapi.responses import JSONResponse

from app.api.tiktok import tiktok_search_endpoint
from app.schemas.tiktok.search import TikTokSearchRequest, TikTokSearchResponse
from app.services.tiktok.search.service import TikTokSearchService


@pytest.mark.asyncio
async def test_tiktok_search_endpoint_rejects_strategy_extra(monkeypatch):
    payload = TikTokSearchRequest.model_construct(
        query="dance",
        numVideos=5,
        force_headful=False,
    )
    object.__setattr__(
        payload,
        "__pydantic_extra__",
        {"strategy": "fast", "bogus": "value"},
    )

    async def fail_search(*args, **kwargs):
        pytest.fail("search service should not be invoked when extras are present")

    monkeypatch.setattr(TikTokSearchService, "search", fail_search, raising=False)

    response = await tiktok_search_endpoint(payload)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 400

    body = json.loads(response.body.decode())
    assert body == {
        "error": {
            "code": "INVALID_PARAMETER",
            "message": (
                "The strategy parameter is not supported. Please use the force_headful parameter instead."
            ),
            "field": "strategy",
            "details": {"accepted_values": ["force_headful"]},
        }
    }


@pytest.mark.asyncio
async def test_tiktok_search_endpoint_rejects_unknown_extras(monkeypatch):
    payload = TikTokSearchRequest.model_construct(
        query="dance",
        numVideos=5,
        force_headful=False,
    )
    object.__setattr__(
        payload,
        "__pydantic_extra__",
        {"bogus": "value", "unexpected": 1},
    )

    async def fail_search(*args, **kwargs):
        pytest.fail("search service should not be invoked when extras are present")

    monkeypatch.setattr(TikTokSearchService, "search", fail_search, raising=False)

    response = await tiktok_search_endpoint(payload)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 400

    body = json.loads(response.body.decode())
    assert body == {
        "error": {
            "code": "INVALID_PARAMETER",
            "message": "Unknown parameter(s) provided: bogus, unexpected",
            "field": "bogus, unexpected",
            "details": {
                "accepted_parameters": sorted(TikTokSearchRequest.model_fields.keys()),
            },
        }
    }


@pytest.mark.asyncio
async def test_tiktok_search_endpoint_normalizes_service_payload(monkeypatch):
    captured_calls = {}

    async def fake_search(self, query, num_videos):
        captured_calls["query"] = query
        captured_calls["num_videos"] = num_videos
        return {
            "results": [
                {
                    "id": 123,
                    "caption": "Clip A",
                    "authorHandle": "@creator_one",
                    "likeCount": "17",
                    "uploadTime": "2024-01-01",
                    "webViewUrl": "https://example.com/a",
                },
                "not-a-dict",
                {
                    "id": "456",
                    "title": "Clip B",
                    "author": "@creator_two",
                    "likes": "25",
                    "createTime": 1712345678,
                    "url": "https://example.com/b",
                },
            ],
            "totalResults": "not-a-number",
        }

    monkeypatch.setattr(TikTokSearchService, "search", fake_search, raising=False)

    payload = TikTokSearchRequest(
        query=["  foo", "bar  "],
        numVideos=7,
        force_headful=True,
    )

    response = await tiktok_search_endpoint(payload)

    assert isinstance(response, TikTokSearchResponse)
    assert captured_calls == {"query": payload.query, "num_videos": payload.numVideos}

    assert len(response.results) == 2
    first, second = response.results

    assert first.authorHandle == "creator_one"
    assert first.likeCount == 17
    assert second.authorHandle == "creator_two"
    assert second.likeCount == 25

    assert response.totalResults == 2
    assert response.query == "foo, bar"

    assert response.execution_mode == "headless"
    metadata = response.search_metadata
    assert metadata.executed_path == "headless"
    assert metadata.execution_time >= 0
    expected_hash = hashlib.md5(
        json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    assert metadata.request_hash == expected_hash
