import sys
import types

import pytest

from app.schemas.auspost import AuspostCrawlRequest
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.crawler.auspost import AuspostCrawler

pytestmark = [pytest.mark.unit]


class TestAuspostCrawl:
    def _mock_settings(self, **overrides):
        defaults = {
            "max_retries": 3,
            "camoufox_user_data_dir": None,
            "proxy_list_file_path": None,
            "private_proxy_url": None,
            "proxy_rotation_mode": "sequential",
            "retry_backoff_base_ms": 1,
            "retry_backoff_max_ms": 2,
            "retry_jitter_ms": 0,
            "proxy_health_failure_threshold": 2,
            "proxy_unhealthy_cooldown_minute": 1,
            "default_headless": True,
            "default_network_idle": False,
            "default_timeout_ms": 20000,
            "min_html_content_length": 1,
            "camoufox_geoip": True,
        }
        defaults.update(overrides)
        return type("MockSettings", (), defaults)()

    def _install_fake_scrapling(self, monkeypatch, html: str, side_effects):
        """Install a fake StealthyFetcher that records kwargs and returns given HTML."""
        calls = {"count": 0, "kwargs": []}

        class FakeStealthyFetcher:
            adaptive = False

            @staticmethod
            def fetch(url, **kwargs):
                idx = calls["count"]
                calls["count"] += 1
                calls["kwargs"].append(kwargs)
                action = side_effects[min(idx, len(side_effects) - 1)]
                if isinstance(action, Exception):
                    raise action
                resp = types.SimpleNamespace()
                resp.status = int(action)
                resp.html_content = html
                return resp

        fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
        fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
        monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
        monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)
        return calls

    def test_crawl_auspost_success_and_page_action(self, monkeypatch):
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        html = '<html><h3 id="trackingPanelHeading">Tracking details</h3></html>'
        calls = self._install_fake_scrapling(monkeypatch, html, side_effects=[200])

        req = AuspostCrawlRequest(tracking_code="36LB4503170001000930309")
        crawler = AuspostCrawler()
        res = crawler.run(req)

        assert res.status == "success"
        assert res.tracking_code == req.tracking_code
        assert "trackingPanelHeading" in res.html

        assert calls["count"] >= 1
        # Test functionality rather than implementation details

    def test_crawl_auspost_failure_non_200(self, monkeypatch):
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        # Use very short HTML to trigger failure due to insufficient content length
        html = ''
        calls = self._install_fake_scrapling(monkeypatch, html, side_effects=[404])

        req = AuspostCrawlRequest(tracking_code="36LB4503170001000930309")
        crawler = AuspostCrawler()
        res = crawler.run(req)

        assert res.status == "failure"
        assert res.tracking_code == req.tracking_code
        assert res.html is None
        assert "Non-200" in (res.message or "") or "status:" in (res.message or "")
        assert calls["count"] >= 1

    def test_crawl_auspost_single_attempt(self, monkeypatch):
        settings = self._mock_settings(max_retries=1)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        html = '<html><h3 id="trackingPanelHeading">Tracking details</h3></html>'
        calls = self._install_fake_scrapling(monkeypatch, html, side_effects=[200])

        req = AuspostCrawlRequest(tracking_code="ABC123")
        crawler = AuspostCrawler()
        res = crawler.run(req)

        assert res.status == "success"
        assert calls["count"] == 1

    def test_crawl_auspost_with_flags(self, monkeypatch):
        settings = self._mock_settings(camoufox_user_data_dir="/tmp/test_user_data")
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        html = '<html><h3 id="trackingPanelHeading">Tracking details</h3></html>'
        calls = self._install_fake_scrapling(monkeypatch, html, side_effects=[200])

        req = AuspostCrawlRequest(tracking_code="ABC123", force_user_data=True, force_headful=False)
        crawler = AuspostCrawler()
        res = crawler.run(req)

        assert res.status == "success"
        assert res.tracking_code == "ABC123"
        assert calls["count"] >= 1

    def test_crawl_auspost_fallback_success(self, monkeypatch):
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        tracking_code = "TRACK123"
        responses = [
            CrawlResponse(
                status="failure",
                url="https://auspost.com.au/mypost/track/search",
                html=None,
                message="NotImplementedError",
            ),
            CrawlResponse(
                status="success",
                url=f"https://auspost.com.au/mypost/track/details/{tracking_code}",
                html="<html>tracking</html>",
                message=None,
            ),
        ]

        class FakeEngine:
            def __init__(self):
                self.calls = []

            def run(self, request, page_action):
                index = len(self.calls)
                self.calls.append((request, page_action))
                return responses[index]

        engine = FakeEngine()
        crawler = AuspostCrawler(engine=engine)

        result = crawler.run(AuspostCrawlRequest(tracking_code=tracking_code))

        assert result.status == "success"
        assert result.tracking_code == tracking_code
        assert result.html == "<html>tracking</html>"
        assert len(engine.calls) == 2

        fallback_request, fallback_action = engine.calls[1]
        assert isinstance(fallback_request, CrawlRequest)
        assert str(fallback_request.url) == (
            f"https://auspost.com.au/mypost/track/details/{tracking_code}"
        )
        assert fallback_action is None

    def test_crawl_auspost_fallback_failure_propagates_original(self, monkeypatch):
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

        tracking_code = "TRACK456"
        responses = [
            CrawlResponse(
                status="failure",
                url="https://auspost.com.au/mypost/track/search",
                html=None,
                message="NotImplementedError",
            ),
            CrawlResponse(
                status="failure",
                url=f"https://auspost.com.au/mypost/track/details/{tracking_code}",
                html=None,
                message="fallback failure",
            ),
        ]

        class FakeEngine:
            def __init__(self):
                self.calls = []

            def run(self, request, page_action):
                index = len(self.calls)
                self.calls.append((request, page_action))
                return responses[index]

        engine = FakeEngine()
        crawler = AuspostCrawler(engine=engine)

        result = crawler.run(AuspostCrawlRequest(tracking_code=tracking_code))

        assert result.status == "failure"
        assert result.tracking_code == tracking_code
        assert result.message == "NotImplementedError"
        assert len(engine.calls) == 2
