from typing import Optional

from pydantic import AnyUrl, BaseModel, Field
from pydantic.config import ConfigDict


class CrawlRequest(BaseModel):
    """Request body for generic crawling.

    Simplified request model with explicit field names and no legacy compatibility.
    """

    @property
    def force_mute_audio(self) -> bool:
        """Always mute Camoufox audio for crawl flows."""
        return True

    model_config = ConfigDict(
        extra="forbid",  # Reject extra fields to ensure legacy fields are rejected
        json_schema_extra={
            "examples": [
                {
                    "url": "https://example.com",
                    "wait_for_selector": "body",
                    "wait_for_selector_state": "attached",
                    "timeout_seconds": None,
                    "network_idle": False,
                    "force_headful": False,
                    "force_user_data": False,
                }
            ]
        },
    )

    url: AnyUrl = Field(..., description="The URL to crawl (required)")

    # Selector wait fields
    wait_for_selector: Optional[str] = Field(
        default="body",
        description="CSS selector to wait for before capturing HTML (defaults to 'body')",
        json_schema_extra={"example": "body"},
    )
    wait_for_selector_state: Optional[str] = Field(
        default="attached",
        description=(
            "State to wait for the selector: 'attached' (default), 'visible', "
            "'hidden', 'detached', or 'any'"
        ),
        json_schema_extra={"example": "attached"},
    )

    # Timeout and network fields
    timeout_seconds: Optional[int] = Field(
        default=None,
        description=(
            "Timeout in seconds for the crawl operation (optional, defaults to browser configuration)"
        ),
    )
    network_idle: Optional[bool] = Field(
        default=False,
        description="Wait for network to be idle before capturing HTML (defaults to False)",
        json_schema_extra={"default": False, "example": False},
    )

    # Force flags
    force_headful: Optional[bool] = Field(
        default=False,
        description="Force headful browser mode (defaults to False; overrides config when True)",
        json_schema_extra={"default": False, "example": False},
    )
    force_user_data: Optional[bool] = Field(
        default=False,
        description="Force use of persistent user data directory (defaults to False)",
        json_schema_extra={"default": False, "example": False},
    )


class CrawlResponse(BaseModel):
    status: str
    url: AnyUrl
    html: Optional[str] = None
    message: Optional[str] = None
