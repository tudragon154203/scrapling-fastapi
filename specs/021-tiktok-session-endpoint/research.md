# Research: TikTok Session Endpoint

## Technical Context Analysis

**Language/Version**: Python 3.10+ (based on existing codebase)  
**Primary Dependencies**: FastAPI, Scrapling, BrowserForge, Pydantic 2.9  
**Storage**: File-based user data management (clones of master directory)  
**Testing**: pytest (integration tests require real browser/network)  
**Target Platform**: Linux server (FastAPI backend)  
**Project Type**: web API (single project)  
**Performance Goals**: Session management, login detection within 8s timeout  
**Constraints**: Read-only user data, 409 response for not logged in, 423 for locked directories  
**Scale/Scope**: Single endpoint with login detection, similar to existing /browse endpoint

## Research Findings

### 1. TikTok Login Detection Implementation

**Decision**: Implement multi-method login detection with fallback
**Rationale**: TikTok's login detection requires multiple approaches due to dynamic content and potential anti-bot measures
**Alternatives considered**: 
- Single selector approach (rejected - too fragile)
- API-only approach (rejected - may not catch all login states)
- Cookie-based detection (rejected - requires different implementation)

**Implementation Approach**:
1. Primary: DOM element detection (profile avatar or login button)
2. Secondary: API request interception for `/user/info` endpoints
3. Fallback: Soft refresh + retry (max 8s total)

### 2. User Data Management

**Decision**: Clone-based read-only sessions with automatic cleanup
**Rationale**: Ensures isolation and prevents cross-contamination between sessions
**Alternatives considered**:
- Direct master directory usage (rejected - potential data corruption)
- Temporary directory per session (rejected - cleanup complexity)
- Write mode with locking (implemented as future enhancement)

**Implementation Details**:
- Clone `.../master` to `.../clones/<uuid>`
- Use cloned directory as `user_data_dir`
- Cleanup on session end (browser close or timeout)

### 3. Architecture Pattern

**Decision**: Abstract base class for common browsing functionality
**Rationale**: Code reuse between BrowseExecutor and TiktokExecutor
**Alternatives considered**:
- Complete duplication (rejected - maintenance burden)
- Mixin patterns (rejected - complex inheritance hierarchy)

**Common Functionality**:
- Browser lifecycle management
- User data directory handling
- Session timeout management
- Error handling patterns

### 4. Error Handling

**Decision**: Comprehensive error handling with specific HTTP status codes
**Rationale**: Clear API contract for different error scenarios
**Error States**:
- 409: Not logged in to TikTok
- 423: User data directory locked (if write mode enabled)
- 504: Session timeout
- 500: Internal server errors

### 5. Integration Testing Strategy

**Decision**: Three-tier testing approach
**Rationale**: Ensures both API contract and browser automation work correctly
**Test Levels**:
1. Unit tests: Login detection logic, user data management
2. Integration tests: Headless browser sessions, error responses
3. API contract tests: Schema validation, request/response structure

### 6. Security Considerations

**Decision**: Proxy value redaction in logs
**Rationale**: Prevents sensitive configuration leakage
**Implementation**: Ensure all logging functions redact proxy information before output

### 7. Browser Automation Dependencies

**Decision**: Use existing Scrapling + BrowserForge stack
**Rationale**: Consistency with existing /browse endpoint and proven anti-detection capabilities
**Browser Settings**: 
- BrowserForge fingerprinting for TikTok
- User agent rotation capabilities
- Proxy support (with redaction)

## Technologies to Research Further

1. **Scrapling Browser Launch Options**: Best practices for TikTok-specific configuration
2. **BrowserForge Fingerprinting**: TikTok-relevant browser characteristics
3. **TikTok Login Detection Selectors**: Most reliable DOM elements for login state
4. **User Data Directory Cloning**: Efficient implementation for session isolation

## Architecture Research Needs

1. **Abstract Base Class Design**: Determine optimal inheritance structure
2. **Error Handling Patterns**: Consistent error propagation across layers
3. **Session Management**: Integration with existing timeout and cleanup mechanisms

## Key Dependencies to Verify

1. **FastAPI Version**: Ensure compatibility with existing API patterns
2. **Pydantic 2.9**: Schema validation requirements for new request/response models
3. **Browser Forge Integration**: TikTok-specific fingerprinting configuration
4. **Scrapling Version**: Session management capabilities and options

## Testing Infrastructure

1. **Test Isolation**: Ensure tests don't interfere with each other
2. **Browser Cleanup**: Proper browser instance termination
3. **Mock vs Real**: Balance between mocking and real browser integration tests