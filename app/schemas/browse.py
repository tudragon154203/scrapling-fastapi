from typing import Optional
from pydantic import BaseModel, AnyUrl
from pydantic.config import ConfigDict


class BrowseRequest(BaseModel):
    """Request body for browse endpoint.

    Enables interactive browsing sessions for user data population.
    """
    model_config = ConfigDict(extra='forbid')

    url: Optional[AnyUrl] = None


class BrowseResponse(BaseModel):
    """Response body for browse endpoint."""

    status: str
    message: str