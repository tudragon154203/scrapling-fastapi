import pytest
from types import SimpleNamespace

from app.services.tiktok.search_service import TikTokSearchService


class _DummyService:
    def __init__(self):
        self.settings = SimpleNamespace(
            tiktok_url="https://www.tiktok.com/",
            private_proxy_url=None,
        )


@pytest.fixture
def search_service(monkeypatch):
    service = TikTokSearchService(_DummyService())
    monkeypatch.setattr(
        TikTokSearchService, "_prepare_fetch", lambda self: {"user_data_cleanup": None}
    )
    return service


@pytest.mark.asyncio
async def test_search_stops_after_reaching_target(monkeypatch, search_service):
    fetch_calls = []

    def fake_fetch(self, query, ctx):
        fetch_calls.append(query)
        return (
            [
                {
                    "id": "111",
                    "webViewUrl": "https://www.tiktok.com/@user/video/111",
                },
                {
                    "id": "111",
                    "webViewUrl": "https://www.tiktok.com/@user/video/111",
                },
                {
                    "id": "222",
                    "webViewUrl": "https://www.tiktok.com/@user/video/222",
                },
            ],
            True,
        )

    monkeypatch.setattr(TikTokSearchService, "_fetch_query", fake_fetch)

    result = await search_service.search(["foo", "bar"], num_videos=2)

    assert fetch_calls == ["foo"]
    assert result["totalResults"] == 2
    assert [item["id"] for item in result["results"]] == ["111", "222"]
    assert result["query"] == "foo bar"


@pytest.mark.asyncio
async def test_search_handles_items_without_ids(monkeypatch, search_service):
    def fake_fetch(self, query, ctx):
        return (
            [
                {
                    "id": "",
                    "webViewUrl": "https://www.tiktok.com/@user/video/abc",
                },
                {
                    "id": None,
                    "webViewUrl": "https://www.tiktok.com/@user/video/abc",
                },
                {
                    "webViewUrl": "https://www.tiktok.com/@user/video/xyz",
                },
            ],
            True,
        )

    monkeypatch.setattr(TikTokSearchService, "_fetch_query", fake_fetch)

    result = await search_service.search("foo", num_videos=5)

    urls = [item["webViewUrl"] for item in result["results"]]
    assert result["totalResults"] == 2
    assert urls == [
        "https://www.tiktok.com/@user/video/abc",
        "https://www.tiktok.com/@user/video/xyz",
    ]
