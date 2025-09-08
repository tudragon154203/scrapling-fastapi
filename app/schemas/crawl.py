from typing import Optional
from pydantic import BaseModel, AnyUrl, Field, field_validator
from pydantic.config import ConfigDict


class CrawlRequest(BaseModel):
    """Request body for generic crawling.
    
    Simplified request model with explicit field names and no legacy compatibility.
    """
    model_config = ConfigDict(extra='forbid')  # Reject extra fields to ensure legacy fields are rejected

    url: AnyUrl

    # Selector wait fields
    wait_for_selector: Optional[str] = None
    wait_for_selector_state: Optional[str] = Field(default="visible")

    # Timeout and network fields
    timeout_seconds: Optional[int] = None
    network_idle: Optional[bool] = Field(default=False)

    # Force flags
    force_headful: Optional[bool] = None
    force_user_data: Optional[bool] = None
    user_data_mode: Optional[str] = Field(default="read")

    @field_validator('user_data_mode')
    @classmethod
    def validate_user_data_mode(cls, v):
        if v is not None and v not in ['read', 'write']:
            raise ValueError("user_data_mode must be either 'read' or 'write'")
        return v


class CrawlResponse(BaseModel):
    status: str
    url: AnyUrl
    html: Optional[str] = None
    message: Optional[str] = None

