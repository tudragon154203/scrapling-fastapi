# Data Model: Change TikTok Search Headless/Headful Behaviour

## Entities

### SearchRequest
Represents a request to the TikTok search endpoint.

**Attributes:**
- `force_headful` (optional boolean): Controls browser execution mode
  - When `true`: Run in headful mode
  - When `false` or `null`: Run in headless mode (default)
  - When not provided: Run in headless mode (default)

### ExecutionContext
Represents the context in which the application is running.

**Attributes:**
- `is_test_environment` (boolean): Indicates if the application is running in a test context
  - When `true`: Always run in headless mode (overrides force_headful)
  - When `false`: Use force_headful parameter to determine mode

### BrowserMode
Enumeration representing browser execution modes.

**Values:**
- `HEADLESS`: Browser runs without UI
- `HEADFUL`: Browser runs with UI

## Relationships

1. **SearchRequest** → **BrowserMode**: The force_headful parameter in SearchRequest determines the BrowserMode, unless overridden by test context
2. **ExecutionContext** → **BrowserMode**: When is_test_environment is true, forces BrowserMode to HEADLESS
3. **ExecutionContext** + **SearchRequest** → **BrowserMode**: Combined logic determines final browser execution mode

## Validation Rules

1. **force_headful parameter validation**:
   - Must be a boolean value when provided
   - Invalid values should result in a 422 HTTP error

2. **Execution context validation**:
   - is_test_environment is determined at runtime based on environment variables or test framework context

## State Transitions

No state transitions apply as this is a stateless feature that determines execution mode per request.

## Business Rules

1. Default behavior: All searches run in headless mode
2. Parameter override: When force_headful=true, searches run in headful mode
3. Test override: In test environments, all searches run in headless mode regardless of force_headful