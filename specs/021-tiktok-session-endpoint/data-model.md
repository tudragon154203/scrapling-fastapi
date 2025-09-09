# Data Model: TikTok Session Endpoint

## Entities

### 1. TikTokSessionRequest
**Purpose**: Request schema for `/tiktok/session` endpoint  
**Source**: Feature specification - API Specification section

```python
class TikTokSessionRequest(BaseModel):
    """
    Request schema for TikTok session endpoint.
    
    The endpoint expects an empty request body. All necessary parameters 
    are derived from the context (e.g., user_data_dir_path from environment).
    """
    # No fields required - empty request body
    pass
```

**Validation Rules**:
- Accepts empty JSON body
- Rejects unknown fields (strict schema)
- No required fields

### 2. TikTokSessionResponse
**Purpose**: Response schema for `/tiktok/session` endpoint  
**Source**: Feature specification - Response Schema section

```python
class TikTokSessionResponse(BaseModel):
    """
    Response schema for TikTok session endpoint.
    """
    status: str  # "success" or "error"
    message: str  # A descriptive message about the outcome
    error_details: Optional[dict] = None  # Additional error information (only on error)
    
    class Config:
        schema_extra = {
            "examples": {
                "success": {
                    "status": "success",
                    "message": "TikTok session established successfully"
                },
                "error": {
                    "status": "error", 
                    "message": "Not logged in to TikTok",
                    "error_details": {
                        "code": "NOT_LOGGED_IN",
                        "details": "User is not logged in to TikTok"
                    }
                }
            }
        }
```

**Validation Rules**:
- Status must be either "success" or "error"
- Message must be a non-empty string
- error_details only present when status is "error"

### 3. TikTokLoginState
**Purpose**: Internal enum for tracking login detection results  
**Source**: Feature specification - Login-State Detection section

```python
class TikTokLoginState(str, Enum):
    """Enum for TikTok login detection results"""
    LOGGED_IN = "logged_in"
    LOGGED_OUT = "logged_out"
    UNCERTAIN = "uncertain"
```

**State Transitions**:
- UNCERTAIN → LOGGED_IN (if profile avatar detected)
- UNCERTAIN → LOGGED_OUT (if login button detected) 
- UNCERTAIN → UNCERTAIN (after retry, timeout after 8s)

### 4. TikTokSessionConfig
**Purpose**: Configuration for TikTok session execution  
**Source**: Feature specification - Technical Details section

```python
class TikTokSessionConfig(BaseSettings):
    """Configuration for TikTok session execution"""
    # Login detection configuration
    login_detection_timeout: int = 8  # seconds
    login_detection_retries: int = 1
    login_detection_refresh: bool = True
    
    # User data directory configuration
    user_data_master_dir: str = "./user_data/master"
    user_data_clones_dir: str = "./user_data/clones"
    write_mode_enabled: bool = False
    acquire_lock_timeout: int = 30  # seconds
    
    # Browser configuration
    tiktok_url: str = "https://www.tiktok.com/"
    max_session_duration: int = 300  # seconds (5 minutes default)
    
    # Selectors for login detection
    selectors: Dict[str, str] = {
        "logged_in": "[data-e2e='profile-avatar']",  # Example - needs verification
        "logged_out": "[data-e2e='login-button']",   # Example - needs verification
        "uncertain": "body"  # Fallback
    }
    
    # API endpoints for login detection
    api_endpoints: List[str] = ["/user/info", "/api/user/info"]
```

**Validation Rules**:
- Timeout values must be positive integers
- URL must be valid TikTok domain
- Selectors must be non-empty strings

## Relationships

### 1. TikTokSessionRequest → TikTokSessionResponse
- One-to-one mapping in API response
- Request validation determines response structure

### 2. TikTokSessionConfig → TikTokLoginState
- Configuration parameters influence login detection behavior
- Timeout settings affect state transitions

### 3. TikTokLoginState → TikTokSessionResponse
- Login detection result determines success/error response
- UNCERTAIN state results in error after timeout

## Data Flow

1. **Request → Configuration**: 
   - TikTokSessionRequest (empty) → Session configuration lookup
   - Environment/user_data_dir_path resolution

2. **Configuration → Login Detection**:
   - TikTokSessionConfig → TikTokLoginState detection
   - User data directory cloning + user agent setup

3. **Login Detection → Response**:
   - TikTokLoginState → TikTokSessionResponse
   - Success: 200 with session_id
   - Failure: 409 with error details

## Validation Rules

### Request Validation
- Empty JSON body accepted
- Unknown fields rejected (strict=True)

### Response Validation
- Status: "success" | "error" (required)
- Message: non-empty string (required)
- error_details: dict only when status="error"

### Internal Validation
- Login detection timeout: 8 seconds max
- User data directory: must exist and be readable
- Browser configuration: valid TikTok URL

## Error Conditions

### HTTP 409 (Conflict)
- Trigger: TikTokLoginState.LOGGED_OUT
- Message: "Not logged in to TikTok"
- error_details: Login detection method used

### HTTP 423 (Locked)
- Trigger: User data directory locked (write mode)
- Message: "User data directory is locked"
- error_details: Lock acquisition details

### HTTP 504 (Gateway Timeout)
- Trigger: Session timeout
- Message: "Session timed out"
- error_details: Duration and timeout settings

### HTTP 500 (Internal Server Error)
- Trigger: Unexpected errors during execution
- Message: Internal server error
- error_details: Exception details (sanitized)