# Product Context

## Problem Space
Web scraping services need to avoid detection by modern websites that employ various anti-bot measures including:
- Browser fingerprinting
- Behavioral analysis
- IP blocking and geo-fencing
- Cloudflare and similar protection services

## Solution
Scrapling FastAPI Service provides:
- Stealthy browser automation via Camoufox
- Proxy rotation and health management
- Session persistence for complex workflows
- Configurable stealth options
- Clean API for integration

## User Journey
1. Configure environment with desired stealth settings
2. Send POST request to `/crawl` with target URL and options, or `/crawl/dpd` with tracking code
3. Service handles proxy selection, retries, and stealth
4. Receive HTML response with success/failure status

## Key Differentiators
- **Minimal API**: Simple request/response without complex configuration
- **Capability Detection**: Automatically adapts to available Scrapling features
- **Safe Fallbacks**: Graceful degradation when features are unsupported
- **Comprehensive Testing**: High test coverage for reliability

## Success Metrics
- Successful crawl rate under various conditions
- Detection avoidance effectiveness
- Response time and reliability
- Ease of integration and configuration