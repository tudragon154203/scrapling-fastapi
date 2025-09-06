import re
from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict


class AuspostCrawlRequest(BaseModel):
    """Request body for AusPost tracking crawling.

    Accepts either a raw AusPost tracking code or a full details URL
    (e.g. https://auspost.com.au/mypost/track/details/36LB45032230) and
    optional force flags. When a URL is provided, the tracking code is
    extracted automatically.
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
        """Validate tracking code and support extraction from full URL.

        - Trims whitespace
        - If value looks like an AusPost details URL, extract the code segment
        - Ensures final value is non-empty
        """
        if not v or not isinstance(v, str):
            raise ValueError('tracking_code must be a non-empty string')

        raw = v.strip()
        if not raw:
            raise ValueError('tracking_code must be a non-empty string')

        # If a full URL is provided, attempt to extract the tracking code
        if raw.startswith("http://") or raw.startswith("https://"):
            try:
                parsed = urlparse(raw)
                path = parsed.path or ""
                # Expect path like /mypost/track/details/<CODE>
                m = re.search(r"/mypost/track/details/([A-Za-z0-9]+)", path)
                if m:
                    return m.group(1)
                # Fallback: if path ends with a plausible code segment (alnum)
                tail = path.rstrip("/").split("/")[-1]
                if tail and re.fullmatch(r"[A-Za-z0-9]+", tail):
                    return tail
                raise ValueError("Invalid AusPost details URL: could not extract tracking code")
            except Exception as e:
                # Re-raise as ValueError with consistent message
                raise ValueError(str(e))

        return raw


class AuspostCrawlResponse(BaseModel):
    """Response body for AusPost tracking crawling."""
    
    status: str = Field(..., description="Either 'success' or 'failure'")
    tracking_code: str = Field(..., description="Echo of the input tracking code")
    html: Optional[str] = Field(default=None, description="HTML content when status is success")
    message: Optional[str] = Field(default=None, description="Error details when status is failure")
