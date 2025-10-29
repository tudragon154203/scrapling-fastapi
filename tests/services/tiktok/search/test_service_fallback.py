import asyncio
from typing import Any, Dict, Iterable, List, Optional

import pytest

from app.services.tiktok.search.service import TikTokSearchService


class _DummySearchImplementation:
    def __init__(self, result: Dict[str, Any]) -> None:
        self._result = result
        self.calls: List[Dict[str, Any]] = []

    async def search(self, query: Any, num_videos: int) -> Dict[str, Any]:
        self.calls.append({"query": query, "num_videos": num_videos})
        await asyncio.sleep(0)
        return self._result


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: Optional[Dict[str, Any]] = None,
        json_exc: Optional[Exception] = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self._json_exc = json_exc

    def json(self) -> Dict[str, Any]:
        if self._json_exc is not None:
            raise self._json_exc
        return self._payload


class _FakeAsyncClient:
    def __init__(self, responses: Iterable[_FakeResponse]) -> None:
        self._responses = list(responses)
        self.requests: List[Dict[str, Any]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    async def get(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> _FakeResponse:
        if not self._responses:
            raise AssertionError("No more fake responses configured")
        response = self._responses.pop(0)
        self.requests.append({"url": url, "params": params or {}})
        await asyncio.sleep(0)
        return response


@pytest.mark.asyncio
async def test_search_without_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    service = TikTokSearchService()
    dummy = _DummySearchImplementation({"results": ["primary"], "totalResults": 1})
    monkeypatch.setattr(service, "_build_search_implementation", lambda: dummy)

    async def _unexpected_fallback(**_: Any) -> Dict[str, Any]:
        raise AssertionError("Fallback should not be invoked for successful primary results")

    monkeypatch.setattr(service, "_fallback_http_search", _unexpected_fallback)

    result = await service.search("widgets", num_videos=5)

    assert result == {"results": ["primary"], "totalResults": 1}
    assert dummy.calls == [{"query": "widgets", "num_videos": 5}]


@pytest.mark.asyncio
async def test_search_with_fallback_success(monkeypatch: pytest.MonkeyPatch) -> None:
    primary_result: Dict[str, Any] = {"results": [], "totalResults": 0}
    fallback_result = {"results": ["fallback"], "totalResults": 1}

    service = TikTokSearchService()
    dummy = _DummySearchImplementation(primary_result)
    monkeypatch.setattr(service, "_build_search_implementation", lambda: dummy)

    async def _fake_fallback(*, query: Any, num_videos: int) -> Dict[str, Any]:
        return fallback_result

    monkeypatch.setattr(service, "_fallback_http_search", _fake_fallback)

    result = await service.search(["one", "two"], num_videos=7)

    assert result is fallback_result
    assert dummy.calls == [{"query": ["one", "two"], "num_videos": 7}]


@pytest.mark.asyncio
async def test_search_with_fallback_none(monkeypatch: pytest.MonkeyPatch) -> None:
    primary_result: Dict[str, Any] = {"results": [], "totalResults": 0}

    service = TikTokSearchService()
    dummy = _DummySearchImplementation(primary_result)
    monkeypatch.setattr(service, "_build_search_implementation", lambda: dummy)

    calls: List[Dict[str, Any]] = []

    async def _fake_fallback(*, query: Any, num_videos: int) -> Optional[Dict[str, Any]]:
        calls.append({"query": query, "num_videos": num_videos})
        return None

    monkeypatch.setattr(service, "_fallback_http_search", _fake_fallback)

    result = await service.search("widgets", num_videos=3)

    assert result == primary_result
    assert calls == [{"query": "widgets", "num_videos": 3}]


@pytest.mark.asyncio
async def test_fallback_http_search_aggregates_and_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _FakeResponse(
            status_code=200,
            payload={
                "data": {
                    "videos": [
                        {
                            "video_id": "111",
                            "title": "First",
                            "digg_count": 5,
                            "create_time": 111,
                            "author": {"unique_id": "@user_one"},
                        },
                        {
                            "video_id": "111",
                            "title": "Duplicate",
                            "digg_count": 6,
                            "create_time": 222,
                            "author": {"id": "should_not_duplicate"},
                        },
                        {
                            "video_id": "222",
                            "title": "Second",
                            "digg_count": 7,
                            "create_time": 333,
                            "author": {"sec_uid": "user_two"},
                        },
                    ]
                }
            },
        )
    ]

    created_clients: List[_FakeAsyncClient] = []

    def _fake_async_client_factory(*args: Any, **kwargs: Any) -> _FakeAsyncClient:
        client = _FakeAsyncClient(responses)
        created_clients.append(client)
        return client

    monkeypatch.setattr(
        "app.services.tiktok.search.service.httpx.AsyncClient",
        _fake_async_client_factory,
    )

    service = TikTokSearchService()
    result = await service._fallback_http_search(query=[" cat ", "", "dog"], num_videos=2)

    assert result is not None
    assert result["totalResults"] == 2
    assert [item["id"] for item in result["results"]] == ["111", "222"]
    assert result["results"][0]["webViewUrl"] == "https://www.tiktok.com/@user_one/video/111"
    assert result["results"][1]["webViewUrl"] == "https://www.tiktok.com/@user_two/video/222"
    assert result["query"] == "cat dog"

    assert created_clients, "Async client should be instantiated"
    request = created_clients[0].requests[0]
    assert request["params"]["keywords"] == "cat"
    assert request["params"]["count"] == 10  # limit < 10 should upscale to 10


@pytest.mark.asyncio
async def test_fallback_http_search_returns_none_for_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [_FakeResponse(status_code=500)]

    def _fake_async_client_factory(*args: Any, **kwargs: Any) -> _FakeAsyncClient:
        return _FakeAsyncClient(responses)

    monkeypatch.setattr(
        "app.services.tiktok.search.service.httpx.AsyncClient",
        _fake_async_client_factory,
    )

    service = TikTokSearchService()
    result = await service._fallback_http_search(query="cats", num_videos=5)

    assert result is None


@pytest.mark.asyncio
async def test_fallback_http_search_returns_none_for_json_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _FakeResponse(status_code=200, json_exc=ValueError("boom")),
    ]

    def _fake_async_client_factory(*args: Any, **kwargs: Any) -> _FakeAsyncClient:
        return _FakeAsyncClient(responses)

    monkeypatch.setattr(
        "app.services.tiktok.search.service.httpx.AsyncClient",
        _fake_async_client_factory,
    )

    service = TikTokSearchService()
    result = await service._fallback_http_search(query="cats", num_videos=5)

    assert result is None


def test_normalize_query_payload_filters_list_entries() -> None:
    service = TikTokSearchService()
    assert service._normalize_query_payload(["foo", "", None, "  bar  "]) == ["foo", "bar"]


def test_normalize_query_payload_accepts_scalar_string() -> None:
    service = TikTokSearchService()
    assert service._normalize_query_payload("  widgets  ") == ["widgets"]


def test_normalize_query_payload_rejects_whitespace_only() -> None:
    service = TikTokSearchService()
    assert service._normalize_query_payload("   ") == []
