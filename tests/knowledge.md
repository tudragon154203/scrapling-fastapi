# Testing Knowledge

## Test Organization

### Directory Structure
- **api/**: API endpoint tests (contract and behavior)
- **core/**: Core functionality tests (config, logging)
- **services/**: Business logic tests (crawlers, engines, executors)
- **schemas/**: Pydantic model validation tests
- **integration/**: End-to-end tests with real services

### Test Categories (Markers)
- `@pytest.mark.unit`: Fast tests with mocked dependencies
- `@pytest.mark.integration`: Tests requiring real network/browser
- `@pytest.mark.contract`: API schema validation tests

## Testing Patterns

### Mock Strategy
```python
# Mock external services at the adapter level
@patch('app.api.crawl.crawl')
def test_crawl_endpoint(mock_crawl, client):
    mock_crawl.return_value = CrawlResponse(...)
```

### Fixture Composition
```python
# conftest.py provides shared fixtures
@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture  
def mock_settings():
    return Settings(max_retries=1, ...)
```

### Test Doubles
```python
# Use SimpleNamespace for lightweight test objects
if not isinstance(crawl, FunctionType):
    req_obj = SimpleNamespace(
        url=str(payload.url),
        force_user_data=payload.force_user_data
    )
```

## Service Testing

### Crawler Tests
- Mock `ScraplingFetcherAdapter` for unit tests
- Test crawler-specific logic (URL building, response parsing)
- Verify error handling and retry behavior

### Executor Tests
- Test single vs retry execution strategies
- Mock backoff policies and health tracking
- Verify proxy rotation and failure handling

### Integration Tests
- Use real URLs and browser automation
- Test against actual target websites
- Verify end-to-end crawling functionality

## API Testing

### Contract Tests
```python
# Verify request/response schemas
def test_crawl_request_validation(client):
    resp = client.post("/crawl", json={"invalid": "data"})
    assert resp.status_code == 422
```

### Behavior Tests
```python
# Test API endpoint behavior with mocked services
@patch('app.api.routes.crawl')
def test_crawl_endpoint_success(mock_crawl, client):
    # Test successful crawl flow
```

### Error Response Tests
```python
# Verify HTTP status code mapping
def test_not_logged_in_returns_409(client):
    # Test error scenarios return correct status codes
```

## Configuration Testing

### Settings Validation
```python
def test_settings_from_env():
    # Test environment variable loading
    # Test default values
    # Test type coercion
```

### Capability Detection
```python
def test_capability_detection():
    # Mock Scrapling capabilities
    # Test parameter filtering
    # Test graceful degradation
```

## Test Utilities

### Mock Factories
```python
# Create realistic test data
class MockCrawlResponse:
    def __init__(self, status="success", html="<html></html>"):
        self.status = status
        self.html = html
```

### Test Data
```python
# Reusable test payloads
VALID_CRAWL_REQUEST = {
    "url": "https://example.com",
    "wait_for_selector": "body",
    "timeout_seconds": 30
}
```

### Helper Functions
```python
# Common test operations
def assert_valid_crawl_response(response_data):
    assert "status" in response_data
    assert "url" in response_data
    assert "html" in response_data
```

## Integration Test Strategy

### Real URL Testing
- Test against stable, public websites
- Handle network failures gracefully
- Use timeouts to prevent hanging tests

### Browser Automation
- Test actual Camoufox/Scrapling integration
- Verify stealth features work correctly
- Test user data persistence

### Service Dependencies
- Test proxy rotation with real proxies
- Verify health tracking mechanisms
- Test session management

## Test Configuration

### pytest.ini Settings
```ini
testpaths = ["tests"]
markers = [
    "integration: real network/browser tests",
    "unit: isolated unit tests",
    "contract: API contract tests"
]
```

### Environment Isolation
- Use `PYTEST_CURRENT_TEST` to detect test environment
- Override settings for test scenarios
- Clean up resources after tests

### Parallel Execution
- Unit tests can run in parallel
- Integration tests may need serialization
- Resource cleanup between test runs

## Common Test Patterns

### Mocking External Dependencies
```python
# Mock at the service boundary
@patch('app.services.common.adapters.scrapling_fetcher.ScraplingFetcherAdapter')
def test_with_mocked_fetcher(mock_fetcher):
    # Test internal logic without external dependencies
```

### Testing Error Scenarios
```python
# Test various failure modes
def test_network_timeout():
    # Mock network timeout
def test_invalid_selector():
    # Mock selector not found
def test_proxy_failure():
    # Mock proxy connection failure
```

### Async Testing
```python
# Test async endpoints
@pytest.mark.asyncio
async def test_async_endpoint():
    # Use async test client
```

## Performance Testing

### Load Testing
- Test multiple concurrent requests
- Verify resource cleanup
- Monitor memory usage

### Timeout Testing
- Test various timeout scenarios
- Verify graceful degradation
- Test cleanup on timeout