from app.schemas.crawl import CrawlRequest


def test_crawl_request_mutes_audio_by_default():
    req = CrawlRequest(url="https://example.com")
    assert req.force_mute_audio is True
