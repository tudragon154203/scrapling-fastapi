from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict


class AuspostCrawlRequest(BaseModel):
    """Request body for AusPost tracking crawling.
    
    Accepts a tracking code and optional force flags.
    """
    # Allow additional fields to be ignored to keep endpoint lenient
    model_config = ConfigDict(extra='allow')
    
    tracking_code: str = Field(..., description="AusPost tracking code (required, non-empty)")
    force_user_data: Optional[bool] = Field(
        default=False, 
        description="Enable Camoufox persistent user data if configured"
    )
    force_headful: Optional[bool] = Field(
        default=False, 
        description="Forces headful mode on Windows; ignored on Linux/Docker"
    )
    
    @field_validator('tracking_code')
    @classmethod
    def validate_tracking_code(cls, v):
        """Ensure tracking code is not empty after trimming."""
        if not v or not v.strip():
            raise ValueError('tracking_code must be a non-empty string')
        return v.strip()


class AuspostCrawlResponse(BaseModel):
    """Response body for AusPost tracking crawling."""
    
    status: str = Field(..., description="Either 'success' or 'failure'")
    tracking_code: str = Field(..., description="Echo of the input tracking code")
    html: Optional[str] = Field(default=None, description="HTML content when status is success")
    message: Optional[str] = Field(default=None, description="Error details when status is failure")
