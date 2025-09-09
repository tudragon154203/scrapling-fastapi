# TikTok Session API Quickstart

## Overview

The TikTok Session API provides interactive browser sessions for TikTok with automatic login status checking. This quickstart guide helps you understand and test the API functionality.

## Prerequisites

- Development server running on port 5681
- TikTok account logged in for testing
- API authentication credentials
- User data directory configured

## API Request

### Endpoint
```
POST /tiktok/session
```

### Request Body (Empty)
```json
{
    // Empty request body - all configuration derived from context
}
```

### Sample Request (curl)
```bash
curl -X POST http://localhost:5681/tiktok/session \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -H "Cookie: session_token=your-session-token" \
  -d '{}'
```

## Responses

### Success Response (200)
```json
{
    "status": "success",
    "message": "TikTok session established successfully"
}
```

**Headers:**
```
X-Session-Id: 550e8400-e29b-41d4-a716-446655440000
```

### Error Response (409 - Not Logged In)
```json
{
    "status": "error",
    "message": "Not logged in to TikTok",
    "error_details": {
        "code": "NOT_LOGGED_IN",
        "details": "User is not logged in to TikTok",
        "method": "dom_api_combo"
    }
}
```

**Headers:**
```
X-Error-Code: NOT_LOGGED_IN
```

## Test Scenarios

### Test 1: Successful Session Creation
1. Ensure user is logged in to TikTok in the user data directory
2. Send POST request to `/tiktok/session`
3. Verify 200 response with success status
4. Verify `X-Session-Id` header is present
5. Browser session should be available for interaction

### Test 2: Not Logged In
1. Ensure user is NOT logged in to TikTok
2. Send POST request to `/tiktok/session`
3. Verify 409 response with error status
4. Verify error details indicate login failure
5. Verify no browser session is created

### Test 3: Timeout Scenario
1. Start session with user data directory requiring long initialization
2. Wait for timeout (5 minutes default)
3. Verify 504 response with timeout status
4. Verify browser session is properly cleaned up

## Validation Steps

### API Contract Validation
1. **Request Schema**: Empty JSON body should be accepted
2. **Response Schema**: Success/error responses should match schema
3. **Status Codes**: Correct HTTP status codes for each scenario
4. **Headers**: Required headers should be present
5. **Authentication**: API should require authentication

### Login Detection Validation
1. **DOM Detection**: Profile avatar or login button detection
2. **API Detection**: Interception of `/user/info` requests
3. **Fallback**: Refresh and retry mechanism
4. **Timeout**: Login detection should respect 8-second timeout

### Session Management Validation
1. **User Data**: Directory cloning should work correctly
2. **Cleanup**: Session directories should be cleaned up after closure
3. **Locking**: Write mode should handle directory locks properly
4. **Interactive**: Browser should support full interaction capabilities

## First Steps for Implementation

1. **Run Contract Tests**
   ```bash
   pytest specs/021-tiktok-session-endpoint/contracts/test_tiktok_schema.py -v
   ```

2. **Verify API Documentation**
   ```bash
   # Start server
   python -m uvicorn app.main:app --host 0.0.0.0 --port 5681 --reload
   
   # Access OpenAPI docs
   open http://localhost:5681/docs
   ```

3. **Test Login Detection Logic**
   - Create unit tests for login detection
   - Test DOM element selectors
   - Test API request interception
   - Test timeout behavior

## Next Steps

1. **Implement TikTokService** - Encapsulate TikTok-specific logic
2. **Create TiktokExecutor** - Extend browsing executor for TikTok
3. **Implement AbstractBrowsingExecutor** - Common functionality base class
4. **Add Integration Tests** - Real browser session testing
5. **Configure User Data Management** - Directory cloning and cleanup
6. **Add Login Detection** - DOM/API/fallback mechanisms
7. **Handle Error Cases** - All specified error responses
8. **Add Authentication** - API security requirements

## Common Issues

### Port Mismatch
- Development server runs on port 5681 (not 5699)
- Update any hardcoded port references in tests

### Authentication
- API requires authentication (cookie or API key)
- Ensure proper authentication headers in requests

### User Data Directory
- Master user data directory must exist and be configured
- Session directories are cloned from master for isolation

### Proxy Redaction
- Proxy values should be redacted in all logs
- Ensure logging functions properly sanitize proxy info