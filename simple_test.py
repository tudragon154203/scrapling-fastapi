import pytest
import sys
import types

def test_mock_import():
    # Mock scrapling first
    class FakeStealthyFetcher:
        adaptive = False
        
        @staticmethod
        def fetch(url, **kwargs):
            print("Mock fetch called!")
            resp = types.SimpleNamespace()
            resp.status = 200
            resp.html_content = '<html><h3 id="trackingPanelHeading">Tracking details</h3></html>'
            return resp

    fake_fetchers = types.SimpleNamespace(StealthyFetcher=FakeStealthyFetcher)
    fake_scrapling = types.SimpleNamespace(fetchers=fake_fetchers)
    sys.modules['scrapling'] = fake_scrapling
    sys.modules['scrapling.fetchers'] = fake_fetchers
    
    # Now import the module
    from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter
    print("Import successful")
    
    # Test the fetch
    adapter = ScraplingFetcherAdapter()
    result = adapter.fetch("https://test.com", {})
    print(f"Fetch result: {result.status}")