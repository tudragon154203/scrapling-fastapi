from typing import Optional
from pydantic import BaseModel, AnyUrl, Field
from pydantic.config import ConfigDict


class CrawlRequest(BaseModel):
    """Request body for generic crawling.

    Simplified request model with explicit field names and no legacy compatibility.
    """
    model_config = ConfigDict(extra='forbid')  # Reject extra fields to ensure legacy fields are rejected

    url: AnyUrl = Field(..., description="The URL to crawl (required)")

    # Selector wait fields
    wait_for_selector: Optional[str] = Field(None, description="CSS selector to wait for before capturing HTML (optional)")
    wait_for_selector_state: Optional[str] = Field(
        default="visible",
        description="State to wait for the selector: 'visible' (default), 'hidden', 'attached', 'detached', or 'any'")

    # Timeout and network fields
    timeout_seconds: Optional[int] = Field(
        None, description="Timeout in seconds for the crawl operation (optional, defaults to browser default)")
    network_idle: Optional[bool] = Field(default=False, description="Wait for network to be idle before capturing HTML (optional)")

    # Force flags
    force_headful: Optional[bool] = Field(None, description="Force headful browser mode (optional, overrides config)")
    force_user_data: Optional[bool] = Field(None, description="Force use of persistent user data directory (optional)")


class CrawlResponse(BaseModel):
    status: str
    url: AnyUrl
    html: Optional[str] = None
    message: Optional[str] = None
