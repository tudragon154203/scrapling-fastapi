from typing import Optional
from pydantic import BaseModel, AnyUrl, Field


class CrawlRequest(BaseModel):
    """Request body for generic crawling.

    Supports both the new fields and a minimal compatibility layer with
    earlier x_* fields described in the legacy project summary.
    """

    url: AnyUrl

    # New-style optional fields
    wait_selector: Optional[str] = None
    wait_selector_state: Optional[str] = Field(default="visible")
    timeout_ms: Optional[int] = None
    headless: Optional[bool] = None
    network_idle: Optional[bool] = None

    # Back-compat (legacy summary)
    x_wait_for_selector: Optional[str] = None
    x_wait_time: Optional[int] = None  # seconds
    x_force_headful: Optional[bool] = None
    x_force_user_data: Optional[bool] = None  # reserved for future


class CrawlResponse(BaseModel):
    status: str
    url: AnyUrl
    html: Optional[str] = None
    message: Optional[str] = None

