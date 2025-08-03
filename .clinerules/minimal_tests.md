# Minimal Testing Strategy

## Test Philosophy
- Write only essential tests that verify core functionality
- Focus on integration tests over unit tests where appropriate
- Use mocks to avoid external dependencies

## Test Structure
- Create minimal test files that mirror the application structure
- Include basic imports and setup in each test file
- Add placeholder test functions with descriptive names

## Test Implementation Guidelines
- Test only critical paths and edge cases
- Skip exhaustive testing of all code paths
- Use fixtures for common setup and teardown
- Implement basic smoke tests for API endpoints
- Mock external services like Playwright browser

## Example Test Structure

```python
# Basic test file structure
import pytest
from unittest.mock import patch, MagicMock

# Import the module to test
from app.module import function_to_test

# Fixture for common setup
@pytest.fixture
def setup_fixture():
    # Minimal setup code
    return MagicMock()

# Simple test function
def test_basic_functionality(setup_fixture):
    # Arrange
    # Act
    # Assert
    pass  # Implement only when needed
```

## Test Coverage Goals
- Ensure basic API contract is tested
- Verify error handling for critical paths
- Test configuration loading
- Skip exhaustive browser automation testing

## Test Execution Requirements
- Always run tests after writing them to verify they pass
- Adjust the codebase and tests if they fail
- A test writing task can only be marked as completed when all tests pass
- Use `python -m pytest` to run tests with appropriate flags