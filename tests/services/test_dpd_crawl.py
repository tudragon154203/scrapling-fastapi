import sys
import types
from unittest import mock

import pytest

from app.schemas.dpd import DPDCrawlRequest, DPDCrawlResponse
from app.services.crawler.dpd import build_dpd_url, crawl_dpd


class TestBuildDpdUrl:
    """Test DPD URL building functionality."""

    def test_build_dpd_url_basic(self):
        """Test basic URL building with tracking code."""
        url = build_dpd_url("12345678901234")
        assert url == "https://tracking.dpd.de/parcelstatus?query=12345678901234"

    def test_build_dpd_url_with_special_chars(self):
        """Test URL building with special characters in tracking code."""
        url = build_dpd_url("123/456")
        assert url == "https://tracking.dpd.de/parcelstatus?query=123%2F456"

    def test_build_dpd_url_with_spaces(self):
        """Test URL building with spaces in tracking code."""
        url = build_dpd_url("123 456")
        assert url == "https://tracking.dpd.de/parcelstatus?query=123+456"


class TestDPDCrawl:
    """Test DPD crawl service functionality."""

    def _mock_settings(self, **overrides):
        """Create mock settings with default values and overrides."""
        defaults = {
            "max_retries": 3,
            "camoufox_user_data_dir": None,
            "proxy_list_file_path": None,
            "private_proxy_url": None,
            "proxy_rotation_mode": "sequential",
            "retry_backoff_base_ms": 500,
            "retry_backoff_max_ms": 5000,
            "retry_jitter_ms": 250,
            "proxy_health_failure_threshold": 2,
            "proxy_unhealthy_cooldown_minute": 30,
            "default_headless": True,
            "default_network_idle": False,
            "default_timeout_ms": 20000,
            "min_html_content_length": 1,
        }
        defaults.update(overrides)
        return type("MockSettings", (), defaults)()

    def _install_fake_scrapling(self, monkeypatch, side_effects):
        """Install a fake scrapling.fetchers.StealthyFetcher with programmable behavior."""
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
                # treat action as HTTP status
                resp = types.SimpleNamespace()
                resp.status = int(action)
                resp.html_content = f"<html>DPD tracking for {url}</html>"
                return resp

        fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
        fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
        monkeypatch.setitem(sys.modules, "scrapling", fake_scrapling)
        monkeypatch.setitem(sys.modules, "scrapling.fetchers", fake_fetchers)
        return calls

    def test_crawl_dpd_success(self, monkeypatch):
        """Test successful DPD crawl."""
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
        
        calls = self._install_fake_scrapling(monkeypatch, side_effects=[200])

        request = DPDCrawlRequest(tracking_code="12345678901234")
        response = crawl_dpd(request)

        assert response.status == "success"
        assert response.tracking_code == "12345678901234"
        assert "<html>DPD tracking for https://tracking.dpd.de/parcelstatus?query=12345678901234</html>" in response.html
        assert response.message is None
        assert calls["count"] == 1

    def test_crawl_dpd_failure_non_200(self, monkeypatch):
        """Test DPD crawl with non-200 status."""
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
        
        calls = self._install_fake_scrapling(monkeypatch, side_effects=[404])

        request = DPDCrawlRequest(tracking_code="12345678901234")
        response = crawl_dpd(request)

        assert response.status == "failure"
        assert response.tracking_code == "12345678901234"
        assert response.html is None
        assert "status: 404" in response.message
        assert calls["count"] >= 1  # May retry

    def test_crawl_dpd_failure_exception(self, monkeypatch):
        """Test DPD crawl with exception."""
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
        
        exception = RuntimeError("Network error")
        calls = self._install_fake_scrapling(monkeypatch, side_effects=[exception])

        request = DPDCrawlRequest(tracking_code="12345678901234")
        response = crawl_dpd(request)

        assert response.status == "failure"
        assert response.tracking_code == "12345678901234"
        assert response.html is None
        assert "RuntimeError: Network error" in response.message
        assert calls["count"] >= 1  # May retry

    def test_crawl_dpd_single_attempt_mode(self, monkeypatch):
        """Test DPD crawl in single attempt mode (max_retries <= 1)."""
        settings = self._mock_settings(max_retries=1)
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
        
        calls = self._install_fake_scrapling(monkeypatch, side_effects=[200])

        request = DPDCrawlRequest(tracking_code="12345678901234")
        response = crawl_dpd(request)

        assert response.status == "success"
        assert response.tracking_code == "12345678901234"
        assert calls["count"] == 1

    def test_crawl_dpd_with_user_data_flag(self, monkeypatch):
        """Test DPD crawl with x_force_user_data=True."""
        settings = self._mock_settings(camoufox_user_data_dir="/tmp/test_user_data")
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
        
        calls = self._install_fake_scrapling(monkeypatch, side_effects=[200])

        request = DPDCrawlRequest(
            tracking_code="12345678901234",
            x_force_user_data=True
        )
        response = crawl_dpd(request)

        assert response.status == "success"
        assert response.tracking_code == "12345678901234"
        assert calls["count"] == 1

    def test_crawl_dpd_with_headful_flag(self, monkeypatch):
        """Test DPD crawl with x_force_headful=True."""
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
        
        calls = self._install_fake_scrapling(monkeypatch, side_effects=[200])

        request = DPDCrawlRequest(
            tracking_code="12345678901234",
            x_force_headful=True
        )
        response = crawl_dpd(request)

        assert response.status == "success"
        assert response.tracking_code == "12345678901234"
        assert calls["count"] == 1

    def test_crawl_dpd_url_construction(self, monkeypatch):
        """Test that DPD crawl constructs the correct URL."""
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
        
        calls = self._install_fake_scrapling(monkeypatch, side_effects=[200])

        request = DPDCrawlRequest(tracking_code="ABC123DEF456")
        response = crawl_dpd(request)

        assert response.status == "success"
        assert calls["count"] == 1
        
        # Check that the correct URL was passed to fetch
        fetch_url = None
        if calls["kwargs"]:
            # URL should be the first argument to fetch, but it's passed positionally
            # We can check the URL from the response HTML which includes it
            expected_url = "https://tracking.dpd.de/parcelstatus?query=ABC123DEF456"
            assert expected_url in response.html

    def test_crawl_dpd_exception_handling(self, monkeypatch):
        """Test DPD crawl handles unexpected exceptions gracefully."""
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
        
        # Mock the entire service to raise an exception
        def raise_exception(*args, **kwargs):
            raise ValueError("Unexpected error")
        
        monkeypatch.setattr("app.services.crawler.dpd.crawl_single_attempt", raise_exception)
        monkeypatch.setattr("app.services.crawler.dpd.execute_crawl_with_retries", raise_exception)

        request = DPDCrawlRequest(tracking_code="12345678901234")
        response = crawl_dpd(request)

        assert response.status == "failure"
        assert response.tracking_code == "12345678901234"
        assert response.html is None
        assert "Exception during DPD crawl: ValueError: Unexpected error" in response.message

    def test_crawl_dpd_tracking_code_in_response(self, monkeypatch):
        """Test that tracking code is properly echoed in response."""
        settings = self._mock_settings()
        monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
        
        calls = self._install_fake_scrapling(monkeypatch, side_effects=[200])

        tracking_codes = ["12345678901234", "ABC123DEF456", "XYZ-789-123"]
        
        for code in tracking_codes:
            request = DPDCrawlRequest(tracking_code=code)
            response = crawl_dpd(request)
            
            assert response.tracking_code == code
