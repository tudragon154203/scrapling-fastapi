# Sprint 16 - Global Logging Implementation

## Overview

This sprint implements a comprehensive global logging system for the Scrapling FastAPI service, enabling proper debug-level logging for proxy usage and other critical operations.

## Problem

Previously, the application had several logging-related issues:

1. **No centralized logging configuration** - Each module created loggers independently without proper formatting or level management
2. **Proxy debug logs not visible** - Proxy logs were at debug level but logging wasn't properly configured to show them
3. **Inconsistent log formatting** - No standard format across modules
4. **Missing context information** - Logs lacked function names, line numbers, and proper timestamps
5. **Dotenv logging level not working** - LOG_LEVEL setting in .env was being ignored

## Solution

### 1. Created Global Logging Module (`app/core/logging.py`)

**New file**: `app/core/logging.py` - Centralized logging configuration with:

- **`get_log_level()`** - Reads from `settings.log_level` (supports DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **`setup_logger()`** - Configures loggers with proper formatting and handlers
- **`get_logger()`** - Factory function for getting configured loggers

**Key Features**:
- Automatic handler management (prevents duplicate handlers)
- Standardized format: `%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s`
- Console output with proper timestamps
- Level propagation prevention
- Environment variable support via settings

### 2. Integrated Logging into Application Startup

**Modified**: `app/main.py` - Added logging initialization in `lifespan` context:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize logging
    setup_logger()
    
    # Startup tasks (future: warm-ups, health checks, etc.)
    yield
    # Shutdown tasks (future: cleanup, metrics flush, etc.)
```

### 3. Updated Proxy Logging to Debug Level

**Modified**: `app/services/crawler/adapters/scrapling_fetcher.py` - Changed proxy logs from `logger.info` to `logger.debug`:
- Lines 146, 148: `logger.debug(f"Using proxy: {redacted_proxy}")`
- Lines 148, 150: `logger.debug("No proxy used for this request")`

**Modified**: `app/services/crawler/executors/retry_executor.py` - Changed proxy logs from `logger.info` to `logger.debug`:
- Line 115: `logger.debug(f"Attempt {attempt_count+1} using {mode} connection, proxy: {redacted_proxy}")`
- Lines 144, 152: `logger.debug(f"Proxy {redacted_proxy} recovered")`

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# Available levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=DEBUG
```

### Settings Integration

The logging system reads from `app.core.config.Settings.log_level`, which means:

```python
# In settings.py (existing configuration)
log_level: str = Field(default="INFO")

# Can be overridden by .env
log_level=os.getenv("LOG_LEVEL", "INFO"),
```

## Usage

### Automatic Logger Setup

All modules now get properly configured loggers automatically:

```python
# Instead of basic setup
import logging
logger = logging.getLogger(__name__)

# Now works with proper formatting and levels
logger.debug("This will appear at debug level")
logger.info("This will appear at info level and above")
```

### Module-Level Loggers

All crawler modules now use consistent logging:

- `app.services.crawler.adapters.scrapling_fetcher`
- `app.services.crawler.executors.retry_executor`
- `app.services.crawler.proxy.health`
- `app.services.crawler.auspost`
- `app.services.crawler.dpd`

## Testing

### Log Level Testing

Test different log levels:

```bash
# Set debug level
export LOG_LEVEL=DEBUG

# Run the application
python -m uvicorn app.main:app --reload
```

### Proxy Log Testing

Test proxy logging with AusPost endpoint:

```bash
# Debug logging shows proxy decisions
curl -X POST http://localhost:5699/crawl/auspost \
  -H "Content-Type: application/json" \
  -d '{"tracking_code": "TEST123"}'
```

Expected debug output:
```
2025-01-07 10:30:15 - app.services.crawler.adapters.scrapling_fetcher - DEBUG - fetch:146 - Using proxy: socks5://***:1080
2025-01-07 10:30:15 - app.services.crawler.executors.retry_executor - DEBUG - execute:115 - Attempt 1 using proxy connection, proxy: socks5://***:1080
```

## Benefits

1. **Visible Proxy Debugging** - Proxy decisions now clearly visible at debug level
2. **Consistent Formatting** - All logs use the same format with timestamps and context
3. **Environment Control** - Log level can be changed via .env without code changes
4. **No Duplicate Logging** - Handler management prevents duplicate log messages
5. **Performance** - Debug-level logs only show when explicitly enabled
6. **Better Observability** - Function names and line numbers help trace log sources

## Migration Notes

### Existing Code

All existing code using `logging.getLogger(__name__)` continues to work but now benefits from:
- Proper formatting
- Correct log levels
- Better performance

### New Development

When adding new modules:

```python
from app.core.logging import get_logger

logger = get_logger(__name__)
logger.debug("Debug message")
logger.info("Info message")
```

## Future Enhancements

1. **File logging** - Add file handler for persistent logs
2. **Structured logging** - JSON format for better log aggregation
3. **Log rotation** - Automatic log file rotation and size management
4. **Performance monitoring** - Add timing and metrics logging
5. **Error tracking** - Integration with error monitoring services

## Related Files

- **New**: `app/core/logging.py` - Global logging configuration
- **Modified**: `app/main.py` - Logging initialization
- **Modified**: `app/services/crawler/adapters/scrapling_fetcher.py` - Proxy debug logging
- **Modified**: `app/services/crawler/executors/retry_executor.py` - Proxy debug logging
- **Configuration**: `.env` - LOG_LEVEL setting

## Testing Checklist

- [ ] Debug logging appears when LOG_LEVEL=DEBUG
- [ ] Info logging appears when LOG_LEVEL=INFO
- [ ] Proxy logs are visible at debug level
- [ ] Log format includes timestamps, module names, function names, line numbers
- [ ] No duplicate log messages
- [ ] Log level changes take effect without application restart
- [ ] Both /crawl and /crawl/auspost endpoints show proxy logs
- [ ] Proxy health recovery logs visible at debug level