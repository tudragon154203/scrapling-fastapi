from typing import Optional
from pydantic import BaseModel, AnyUrl, Field
from pydantic.config import ConfigDict
from enum import Enum


class BrowserEngine(str, Enum):
    """Supported browser engines for browsing."""
    CAMOUFOX = "camoufox"
    CHROMIUM = "chromium"


class BrowseRequest(BaseModel):
    """Request body for browse endpoint.

    Enables interactive browsing sessions for user data population.
    """
    model_config = ConfigDict(extra='forbid')

    url: Optional[AnyUrl] = Field(None, description="The URL to browse to (optional)")
    engine: BrowserEngine = Field(
        BrowserEngine.CAMOUFOX,
        description="Browser engine to use (defaults to camoufox)"
    )


class BrowseResponse(BaseModel):
    """Response body for browse endpoint."""

    status: str
    message: str
