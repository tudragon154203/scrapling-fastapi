# System Patterns

## Request Flow
1. API receives crawl request
2. Resolve effective options from payload + defaults
3. Detect StealthyFetcher capabilities
4. Build Camoufox arguments with stealth options
5. Execute crawl (single attempt or with retries)
6. Return response with status and HTML

## Error Handling
- Graceful fallback when features are unsupported
- INFO logging for missing configurations
- WARNING logging for capability mismatches
- Exception handling with meaningful error messages

## Configuration Patterns
- Environment variables with sensible defaults
- Optional features that don't break when disabled
- Capability detection for API compatibility
- Settings validation with Pydantic

## Testing Patterns
- Mock Scrapling for unit tests
- Fake StealthyFetcher with programmable responses
- Capability signature mocking for parameter testing
- Integration tests for end-to-end flows

## Code Organization
- Modular services in `app/services/`
- Utility functions in `utils/` submodules
- Configuration centralized in `app/core/config.py`
- Tests mirroring application structure