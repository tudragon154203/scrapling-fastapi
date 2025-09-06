# Active Context

## Current Sprint: Sprint 14 - DPD Base URL Update

### Completed Work
- ✅ Implemented DPD tracking endpoint (`/crawl/dpd`) with legacy compatibility
- ✅ Added HTML length validation with configurable minimum threshold
- ✅ Integrated HTML validation into both single and retry executors
- ✅ Enhanced proxy health tracking for short content responses
- ✅ Added comprehensive tests for DPD crawling and HTML validation
- ✅ Maintained backward compatibility with existing API contracts
- ✅ Cleaned up duplicate headless parameters in `/crawl` endpoint
- ✅ Removed `headless` field, kept only `x_force_headful` with .env fallback
- ✅ Simplified `/crawl` endpoint: removed legacy `x_*` fields (except renamed force flags), renamed `wait_selector` to `wait_for_selector`, `wait_selector_state` to `wait_for_selector_state`, `timeout_ms` to `timeout_seconds`. `x_force_headful` renamed to `force_headful`, `x_force_user_data` to `force_user_data`. This was a breaking change.
- ✅ API Rate Limiting: Introduced consistent rate limiting using `fastapi-limiter` and Redis. Applied global limits for `/crawl/*` (15 rpm), `/health` (60 rpm), and per `(IP, base_url)` for `/crawl/*` (4 rpm). Implemented concurrency limiting (max 4 concurrent requests per container). Configurable via environment variables. Graceful disable behavior if Redis URL is missing or unreachable.
- ✅ Updated DPD base URL from DHL to official DPD tracking domain (`https://tracking.dpd.de/status/en_US/parcel/{normalized_code}`)
- ✅ Added tracking code normalization (strip whitespace, remove spaces/hyphens, URL-encode special characters)
- ✅ Updated DPD service implementation in `app/services/crawler/dpd.py`
- ✅ Added unit tests for URL construction and normalization in `tests/services/test_dpd_crawl.py`
- ✅ All existing DPD tests continue to pass with new URL pattern

### Current Focus
- Sprint 14 completed: DPD URL correction and normalization
- Monitoring DPD tracking success rates with new URL pattern
- Preparing for next sprint (Sprint 15)

### Next Steps
- Monitor DPD tracking success rates with corrected URL
- Verify integration with proxy rotation and retry mechanisms
- Consider additional specialized endpoints (AusPost, others)
- Plan Sprint 15 implementation

### Technical Notes
- DPD endpoint reuses generic crawl infrastructure with retry/proxy support
- DPD URL now uses official `tracking.dpd.de` domain with locale-specific path
- Tracking code normalization: strip whitespace, remove spaces/hyphens, URL-encode special characters
- HTML length validation prevents acceptance of bot-detection placeholder pages
- All new features maintain backward compatibility where specified (Sprint 12 is breaking)
- Comprehensive test coverage for DPD URL construction and normalization
- Rate limiting is fail-open if Redis is unavailable.