# Active Context

## Current Sprint: Sprint 06 - Camoufox User Data and Additional Stealth

### Completed Work
- ✅ Implemented `x_force_user_data` flag support for persistent user data
- ✅ Added `CAMOUFOX_USER_DATA_DIR` environment variable configuration
- ✅ Enhanced capability detection for user data parameters (user_data_dir, profile_dir, profile_path, user_data)
- ✅ Added solve_cloudflare stealth option
- ✅ Maintained existing stealth options (geoip, window, locale, disable_coop, virtual_display)
- ✅ Updated tests to cover user data functionality
- ✅ Fixed capability detection order in retry executor

### Current Focus
- User data persistence for session management
- Stealth enhancements for bot detection avoidance
- Capability-safe parameter passing to Camoufox

### Next Steps
- Monitor performance impact of user data persistence
- Consider additional stealth options if needed
- Test with real Camoufox installations

### Technical Notes
- User data directory is created automatically if it doesn't exist
- Fallback gracefully when user data parameters are unsupported
- All stealth options are opt-in via environment variables
- GeoIP spoofing is enabled automatically when using proxies