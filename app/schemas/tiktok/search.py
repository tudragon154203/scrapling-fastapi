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
        default=20,
        ge=1,
        le=100,
        description="Number of videos to return (1-100)",
    )
    force_headful: bool = Field(
        default=False,
        description="Determines search method - True for browser-based search, False for headless URL param search",
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


class SearchMetadata(BaseModel):
    """Metadata about the search execution."""

    executed_path: Literal["browser-based", "headless"] = Field(
        ...,
        description="Method used for search execution"
    )
    execution_time: float = Field(
        ...,
        description="Time taken for search execution in seconds"
    )
    request_hash: str = Field(
        ...,
        description="Unique identifier for this request"
    )


class TikTokSearchResponse(BaseModel):
    """Response schema for TikTok search endpoint."""

    results: List[TikTokVideo] = Field(
        ...,
        description="Array of TikTok content items"
    )
    totalResults: int = Field(
        ...,
        description="Total number of available results"
    )
    query: str = Field(
        ...,
        description="Normalized query string"
    )
    search_metadata: SearchMetadata = Field(
        ...,
        description="Information about the search execution"
    )
    execution_mode: str = Field(
        default="unknown",
        description="Browser execution mode used for this search (deprecated - use search_metadata.executed_path)",
        deprecated=True
    )
