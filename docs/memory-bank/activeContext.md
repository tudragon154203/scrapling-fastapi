# Active Context

## Current Sprint: Sprint 13 - API Rate Limit

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

### Current Focus
- Implementing API rate limiting and concurrency control.
- Specialized crawler endpoints (DPD, potentially others)
- Content quality validation and bot detection heuristics
- Robust error handling and retry strategies

### Next Steps
- Monitor DPD tracking success rates
- Consider additional specialized endpoints if needed
- Evaluate performance impact of HTML validation
- Test rate limiting and concurrency control thoroughly.
- Add `fastapi-limiter` and `redis` to `requirements.txt`.

### Technical Notes
- DPD endpoint reuses generic crawl infrastructure with retry/proxy support
- HTML length validation prevents acceptance of bot-detection placeholder pages
- All new features maintain backward compatibility where specified (Sprint 12 is breaking)
- Comprehensive test coverage for new functionality
- Rate limiting is fail-open if Redis is unavailable.