from typing import Optional
from pydantic import BaseModel, AnyUrl, Field
from pydantic.config import ConfigDict


class BrowseRequest(BaseModel):
    """Request body for browse endpoint.

    Enables interactive browsing sessions for user data population.
    """
    model_config = ConfigDict(extra='forbid')

    url: Optional[AnyUrl] = Field(None, description="The URL to browse to (optional)")


class BrowseResponse(BaseModel):
    """Response body for browse endpoint."""

    status: str
    message: str
