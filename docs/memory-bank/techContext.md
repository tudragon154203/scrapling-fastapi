# Technical Context

## Architecture
- **API Layer**: FastAPI with Pydantic schemas
- **Service Layer**: Modular crawler services with executors
- **Utility Layer**: Fetch capabilities, options resolution, proxy management
- **Configuration**: Environment-based settings with pydantic-settings

## Key Components
- `StealthyFetcher` from Scrapling/Camoufox for browser automation
- Proxy rotation with health tracking
- Retry logic with exponential backoff
- Capability detection for safe parameter passing

## Dependencies
- `scrapling`: Browser automation with stealth features
- `fastapi`: Web framework
- `pydantic`: Data validation
- `pytest`: Testing framework

## Configuration
Environment variables control:
- User data directory (`CAMOUFOX_USER_DATA_DIR`)
- Stealth options (geoip, window, locale, etc.)
- Proxy settings and rotation
- Retry and timeout parameters

## Design Patterns
- Strategy pattern for single vs retry execution
- Factory pattern for proxy selection
- Capability detection for API compatibility
- Configuration as code with environment overrides