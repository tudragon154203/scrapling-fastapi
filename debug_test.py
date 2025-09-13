import sys
import types
import pytest
from app.schemas.auspost import AuspostCrawlRequest
from app.services.crawler.auspost import AuspostCrawler

# Mock scrapling first
class FakeStealthyFetcher:
    adaptive = False
    
    @staticmethod
    def fetch(url, **kwargs):
        print(f"Mock fetch called with URL: {url}")
        resp = types.SimpleNamespace()
        resp.status = 200
        resp.html_content = '<html><h3 id="trackingPanelHeading">Tracking details</h3></html>'
        return resp

fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
sys.modules['scrapling'] = fake_scrapling
sys.modules['scrapling.fetchers'] = fake_fetchers

# Mock settings
class MockSettings:
    max_retries = 3
    camoufox_user_data_dir = None
    proxy_list_file_path = None
    private_proxy_url = None
    proxy_rotation_mode = "sequential"
    retry_backoff_base_ms = 1
    retry_backoff_max_ms = 2
    retry_jitter_ms = 0
    proxy_health_failure_threshold = 2
    proxy_unhealthy_cooldown_minute = 1
    default_headless = True
    default_network_idle = False
    default_timeout_ms = 20000
    min_html_content_length = 1
    camoufox_geoip = True

# Mock get_settings
import app.core.config
app.core.config.get_settings = lambda: MockSettings()

# Now run the test
print("Running test...")
req = AuspostCrawlRequest(tracking_code="36LB4503170001000930309")
crawler = AuspostCrawler()
res = crawler.run(req)
print(f"Result: {res.status}")
print(f"HTML contains trackingPanelHeading: {'trackingPanelHeading' in res.html if res.html else False}")