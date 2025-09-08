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
The endpoint mimics `/crawl` behavior when configured with:
- `force_headful: true` - Always uses headful mode for interactive browsing
- `force_user_data: true` - Enables persistent user data functionality
- `user_data_mode: "write"` - Uses master profile for updating login/cookies

### User Data Directory Structure
- Uses `CAMOUFOX_USER_DATA_DIR` environment variable (default: `data/camoufox_profiles`)
- Writes to master profile directory: `<CAMOUFOX_USER_DATA_DIR>/master`
- Acquires exclusive lock to ensure single writer session

## Implementation Details

### Integration Points
- Reuses existing `CrawlerEngine` infrastructure
- Uses `WaitForUserCloseAction` for manual browser closure handling
- Leverages existing user data context management from `app/services/crawler/options/user_data.py`
- Utilizes same capability detection and parameter composition as `/crawl`

### Request Flow
1. Validate optional URL parameter
2. Create crawl request with forced headful and user data write mode
3. Acquire exclusive lock for master profile
4. Launch browser with starting URL (if provided)
5. Apply `WaitForUserCloseAction` to keep browser open
6. Wait for user to manually close browser window
7. Release lock and return success status

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
- Test URL validation and parameter handling
- Verify force flags are properly set (`force_headful=true`, `force_user_data=true`, `user_data_mode="write"`)
- Test lock acquisition and release logic
- Verify `WaitForUserCloseAction` is applied

### Integration Tests
- Test successful browser session with manual closure
- Test lock contention handling (multiple browse requests)
- Test with and without starting URL parameter
- Verify user data directory is populated after session

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