"""TikTok session schemas."""

from typing import Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic.config import ConfigDict


class TikTokSessionRequest(BaseModel):
    """
    Request schema for TikTok session endpoint.

    The endpoint expects an empty request body. All necessary parameters
    are derived from the context (e.g., user_data_dir_path from environment).
    """

    # No fields required - empty request body
    model_config = ConfigDict(extra='forbid')  # Reject unknown fields


class TikTokSessionResponse(BaseModel):
    """
    Response schema for TikTok session endpoint.
    """

    status: Literal["success", "error"]  # Only "success" or "error" allowed
    message: str  # A descriptive message about the outcome
    error_details: Optional[Dict[str, Any]] = None  # Additional error information (only on error)

    @model_validator(mode='after')
    def validate_error_details(self):
        """Validate that error_details is only present when status is 'error'"""
        if self.status == 'success' and self.error_details is not None:
            raise ValueError('error_details should not be present when status is success')
        if self.status == 'error' and self.error_details is None:
            raise ValueError('error_details is required when status is error')
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "message": "TikTok session established successfully"
                },
                {
                    "status": "error",
                    "message": "Not logged in to TikTok",
                    "error_details": {
                        "code": "NOT_LOGGED_IN",
                        "details": "User is not logged in to TikTok",
                    }
                }
            ]
        },
        "exclude_none": True  # Exclude None values from serialization
    }


class TikTokLoginState(str):
    """Enum for TikTok login detection results"""

    LOGGED_IN = "logged_in"
    LOGGED_OUT = "logged_out"
    UNCERTAIN = "uncertain"


class TikTokSessionConfig(BaseModel):
    """Configuration for TikTok session execution"""

    # Login detection configuration
    login_detection_timeout: int = Field(default=8, description="Login detection timeout in seconds")
    login_detection_retries: int = Field(default=1, description="Number of login detection retries")
    login_detection_refresh: bool = Field(default=True, description="Enable refresh on uncertain state")

    # User data directory configuration
    user_data_master_dir: str = Field(
        default="./user_data/master", description="User data directory (uses CAMOUFOX_USER_DATA_DIR)"
    )
    user_data_clones_dir: str = Field(
        default="./user_data/clones", description="User data directory clones (uses CAMOUFOX_USER_DATA_DIR)"
    )
    write_mode_enabled: bool = Field(default=False, description="Enable write mode for user data directory")
    acquire_lock_timeout: int = Field(default=30, description="Lock acquisition timeout in seconds")

    # Browser configuration
    tiktok_url: str = Field(default="https://www.tiktok.com/", description="TikTok base URL")
    max_session_duration: int = Field(default=300, description="Maximum session duration in seconds")
    headless: bool = Field(default=False, description="Run browser in headless mode")

    # Selectors for login detection
    selectors: Dict[str, str] = Field(
        default_factory=lambda: {
            "logged_in": "[data-e2e='profile-avatar']",  # Example - needs verification
            "logged_out": "[data-e2e='login-button']",   # Example - needs verification
            "uncertain": "body"  # Fallback
        },
        description="CSS selectors for login detection"
    )

    # API endpoints for login detection
    api_endpoints: list = Field(
        default_factory=lambda: ["/user/info", "/api/user/info"],
        description="API endpoints to check for login status",
    )
