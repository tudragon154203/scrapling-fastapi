# Sprint 19 — Browse Endpoint (/browse)

## Goal
Provide a dedicated endpoint for free browsing sessions to populate the CAMOUFOX_USER_DATA_DIR with persistent user data, without automatic termination or HTML return requirements.

## Overview
The `/browse` endpoint enables interactive browsing sessions specifically designed for building and maintaining persistent user profiles. Unlike the `/crawl` endpoint which focuses on content extraction, `/browse` focuses on user data accumulation through manual browser interaction.

## API Specification

### Endpoint
- `POST /browse`

### Request Body
```json
{
  "url": "https://example.com"  // optional starting URL
}
```

### Response
```json
{
  "status": "success" | "failure",
  "message": "Browser session completed successfully" | "Error description"
}
```

## Behavior

### Core Functionality
- Launches a headful browser session with persistent user data in write mode
- Navigates to optional starting URL if provided
- Keeps browser open indefinitely until user manually closes the window
- No automatic termination conditions or timeouts
- Does not return HTML content - purely for user data population

### Integration with Existing System
- Uses a dedicated `BrowseExecutor` (no-retry strategy) wired into the engine.
- Always enforces interactive mode:
  - `force_headful: true` - headful browsing for user interaction
  - `force_user_data: true` - persistent user data population
- Applies `WaitForUserCloseAction` to keep the session open until the user closes the window.
- Ensures a long operation timeout for manual sessions (>= 10x default).

### User Data Directory Structure
- Uses `CAMOUFOX_USER_DATA_DIR` environment variable (default: `data/camoufox_profiles`)
- Writes to master profile directory: `<CAMOUFOX_USER_DATA_DIR>/master`
- Acquires exclusive lock to ensure single writer session

## Implementation Details

### Integration Points
- Reuses `CrawlerEngine` with a browse-specific executor:
  - `app/services/crawler/executors/browse_executor.py` → `BrowseExecutor`
  - Never retries after user-led closure; prevents relaunch loops.
- Uses `WaitForUserCloseAction` for manual browser closure handling.
- Leverages user data context management from `app/services/crawler/options/user_data.py` (write mode).
- Shares capability detection and arg composition with `/crawl` via adapters/builders.

### Request Flow
1. Validate optional URL parameter
2. Create crawl request with forced headful and user data write mode
3. Acquire exclusive lock for master profile
4. Launch browser with starting URL (if provided)
5. Apply `WaitForUserCloseAction` and run via `BrowseExecutor`
6. Wait for user to manually close browser window
7. Never retry after close; treat closure as success
8. Release lock and return success status

## Configuration
- Inherits all existing environment configurations from `/crawl`
- No additional configuration required
- Uses same `CAMOUFOX_USER_DATA_DIR` setting

## Error Handling
- **Invalid URL**: Return 422 validation error
- **Lock acquisition failure**: Return 409 conflict error
- **Browser launch failure**: Return 500 internal error with diagnostic message
- **Unsupported user data parameters**: Log warning but continue operation

## Testing Strategy

### Unit Tests
- URL validation and parameter handling
- Force flags are set (`force_headful=true`, `force_user_data=true`)
- Lock acquisition and release logic
- `WaitForUserCloseAction` is applied
- `BrowseExecutor` behavior:
  - Never retries; `should_retry` always false
  - Treats user-led browser close as success (no relaunch)
  - Treats other errors as failure
  - Enforces long timeout for interactive sessions

### Integration Tests
- Successful browser session with manual closure
- Lock contention handling (multiple browse requests)
- With and without starting URL parameter
- User data directory is populated after session
- Master lock creation and cleanup preventing relaunch loops

### Test Scenarios
1. **Happy path**: Valid request → browser launches → user closes → success response
2. **No URL**: Empty request → browser launches with blank page → user closes → success
3. **Lock contention**: Concurrent browse requests → second request receives 409 conflict
4. **Invalid URL**: Malformed URL → 422 validation error

## Acceptance Criteria
- [ ] `POST /browse` endpoint exists and accepts optional URL parameter
- [ ] Always uses headful mode with user data write mode
- [ ] Browser remains open until manually closed by user
- [ ] Returns simple status response without HTML content
- [ ] Properly handles lock acquisition for exclusive write access
- [ ] All existing tests continue to pass
- [ ] New tests cover browse-specific functionality

## Dependencies
- Existing user data infrastructure (Sprint 18)
- `WaitForUserCloseAction` functionality
- Crawler engine and executor patterns

## Out of Scope
- HTML content extraction or return
- Automatic termination conditions
- Complex browsing automation
- Session management beyond user data persistence

## Migration Notes
- This is a net-new endpoint, no breaking changes to existing functionality
- Clients can use `/browse` specifically for user data population
- `/crawl` continues to function as before for content extraction
