# Active Context

## Current Sprint: Sprint 15 - GeoIP Auto Enable

### Completed Work
- ✅ Implemented automatic GeoIP enabling when fetcher supports `geoip` parameter
- ✅ Removed dependency on proxy presence and `camoufox_geoip` setting for GeoIP
- ✅ Added GeoIP database error fallback with automatic retry without geoip
- ✅ Updated `FetchArgComposer` to unconditionally set `geoip=True` when supported
- ✅ Enhanced `ScraplingFetcherAdapter` with `_fetch_with_geoip_fallback()` method
- ✅ Added comprehensive unit tests for GeoIP capability detection and fallback
- ✅ Maintained backward compatibility with existing API contracts
- ✅ All existing tests continue to pass with new GeoIP behavior

### Current Focus
- Sprint 15 completed: GeoIP auto-enablement and fallback implementation
- Monitoring GeoIP success rates and fallback behavior
- Ensuring consistent GeoIP behavior across all endpoints

### Next Steps
- Monitor GeoIP success rates and fallback frequency
- Verify integration with proxy rotation and retry mechanisms
- Consider additional stealth parameter optimizations
- Plan next sprint implementation

### Technical Notes
- GeoIP now enabled automatically when fetcher supports `geoip` parameter
- No environment configuration required for GeoIP enabling
- Automatic fallback when MaxMind database is missing or invalid
- Fallback detects `InvalidDatabaseError` and `GeoLite2-City.mmdb` errors
- Single retry attempt without geoip on database errors
- All endpoints (`/crawl`, `/crawl/auspost`, `/crawl/dpd`) benefit from auto GeoIP
- Comprehensive test coverage for capability detection and error fallback