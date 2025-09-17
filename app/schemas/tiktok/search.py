"""TikTok search schemas."""

from typing import List, Union, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic.config import ConfigDict

from .models import TikTokVideo


class TikTokSearchRequest(BaseModel):
    """Request schema for TikTok search endpoint."""

    query: Union[str, List[str]] = Field(
        ...,
        description="Search query as string or array of strings",
    )
    numVideos: int = Field(
        default=50,
        ge=1,
        le=50,
        description="Number of videos to return (1-50)",
    )
    sortType: Literal["RELEVANCE"] = Field(
        default="RELEVANCE",
        description="Sort type for results (only RELEVANCE supported in v1)",
    )
    recencyDays: Literal["ALL", "24H", "7_DAYS", "30_DAYS", "90_DAYS", "180_DAYS"] = Field(
        default="ALL",
        description="Recency filter for results (best-effort)",
    )
    strategy: Literal["direct", "multistep"] = Field(
        default="multistep",
        description="Search strategy to use - 'direct' for URL parameters, 'multistep' for browser automation",
    )
    strategy: Literal["direct", "multistep"] = Field(
        default="multistep",
        description="Search strategy: 'direct' for URL parameters, 'multistep' for browser automation",
    )

    @model_validator(mode='after')
    def validate_query(self):
        """Light validation: allow empty strings to defer to service-level errors."""
        if isinstance(self.query, list):
            if not self.query:
                raise ValueError('Query array cannot be empty')
            for q in self.query:
                if not isinstance(q, str):
                    raise ValueError('Query items must be strings')
                if not q.strip():
                    raise ValueError('Query strings cannot be empty')
                if len(q.strip()) > 100:
                    raise ValueError('Query strings must be 100 characters or less')
        elif isinstance(self.query, str):
            if len(self.query.strip()) > 100:
                raise ValueError('Query string must be 100 characters or less')
        return self

    model_config = ConfigDict(extra='forbid')


class TikTokSearchResponse(BaseModel):
    """Response schema for TikTok search endpoint."""

    results: List[TikTokVideo] = Field(..., description="List of TikTok videos")
    totalResults: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Normalized query string")
