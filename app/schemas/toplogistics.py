from typing import Optional
from urllib.parse import urlparse, parse_qs
from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict


class TopLogisticsCrawlRequest(BaseModel):
    """Request body for TopLogistics tracking crawling.

    Accepts either a raw tracking code (e.g., 33EVH0319358) or a full
    search URL (e.g., https://toplogistics.com.au/?s=33EVH0319358) and
    optional force flags. When a URL is provided, the tracking code is
    extracted automatically from the 's' query parameter.
    """
    model_config = ConfigDict(extra='forbid')

    tracking_code: str = Field(..., description="TopLogistics tracking code or search URL (required, non-empty)")
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
        """Validate tracking code and support extraction from search URL.

        - Trims whitespace
        - If value looks like a TopLogistics search URL, extract the 's' parameter
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
                query_params = parse_qs(parsed.query or "")
                s_params = query_params.get('s', [])
                if s_params and s_params[0].strip():
                    return s_params[0].strip()
                raise ValueError("Invalid TopLogistics search URL: could not extract 's' parameter")
            except Exception as e:
                # Re-raise as ValueError with consistent message
                raise ValueError(str(e))

        return raw


class TopLogisticsCrawlResponse(BaseModel):
    """Response body for TopLogistics tracking crawling."""

    status: str = Field(..., description="Either 'success' or 'failure'")
    tracking_code: str = Field(..., description="Echo of the input tracking code")
    html: Optional[str] = Field(default=None, description="HTML content when status is success")
    message: Optional[str] = Field(default=None, description="Error details when status is failure")
