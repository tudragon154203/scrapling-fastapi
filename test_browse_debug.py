#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.schemas.browse import BrowseRequest, BrowserEngine
from app.services.browser.browse import BrowseCrawler

def test_browse_conversion():
    """Test that browse requests properly convert to crawl requests with force_headful=True."""

    print("=== Testing Browse Request Conversion ===")

    # Test with Chromium
    print("\n1. Testing Chromium engine:")
    request = BrowseRequest(url='https://example.com/', engine=BrowserEngine.CHROMIUM)
    print(f"   Original request: {request}")
    print(f"   Engine: {request.engine}")

    crawler = BrowseCrawler(browser_engine=BrowserEngine.CHROMIUM)
    crawl_request = crawler._convert_browse_to_crawl_request(request)

    print(f"   Converted crawl request:")
    print(f"     URL: {crawl_request.url}")
    print(f"     Force headful: {crawl_request.force_headful}")
    print(f"     Force user data: {crawl_request.force_user_data}")
    print(f"     Timeout: {crawl_request.timeout_seconds}")

    # Test with Camoufox
    print("\n2. Testing Camoufox engine:")
    request = BrowseRequest(url='https://example.com/', engine=BrowserEngine.CAMOUFOX)
    print(f"   Original request: {request}")
    print(f"   Engine: {request.engine}")

    crawler = BrowseCrawler(browser_engine=BrowserEngine.CAMOUFOX)
    crawl_request = crawler._convert_browse_to_crawl_request(request)

    print(f"   Converted crawl request:")
    print(f"     URL: {crawl_request.url}")
    print(f"     Force headful: {crawl_request.force_headful}")
    print(f"     Force user data: {crawl_request.force_user_data}")
    print(f"     Timeout: {crawl_request.timeout_seconds}")

if __name__ == "__main__":
    test_browse_conversion()