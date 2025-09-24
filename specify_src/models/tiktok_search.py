from typing import List, Optional, Union, Literal

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from specify_src.models.tiktok_content import TikTokContentItem


class TikTokSearchMetadata(BaseModel):
    """Metadata surfaced alongside TikTok search results."""

    executed_path: Literal["browser-based", "headless"] = Field(
        ...,
        description="Path executed by the service",
        example="headless",
    )
    execution_time: float = Field(
        ...,
        description="Execution duration in seconds",
        example=1.234,
    )
    request_hash: str = Field(
        ...,
        description="Deterministic hash of the validated request payload",
        example="c0ffee6f572b4f54b16b5a8c5e1a9c42",
    )


class TikTokSearchRequest(BaseModel):
    """Request schema for TikTok search calls."""

    query: Union[str, List[str]] = Field(
        ...,
        description="Search query as a single string or list of strings",
        example=["funny", "cats"],
    )
    numVideos: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of videos to retrieve",
        example=25,
    )
    sortType: Literal["RELEVANCE"] = Field(
        default="RELEVANCE",
        description="Sorting strategy (RELEVANCE only)",
    )
    recencyDays: Literal["ALL", "24H", "7_DAYS", "30_DAYS", "90_DAYS", "180_DAYS"] = Field(
        default="ALL",
        description="Recency filter applied to results",
    )
    force_headful: bool = Field(
        ...,
        description="True to run browser-based search, False for headless URL path",
    )
    search_url: Optional[str] = Field(
        default=None,
        description="Optional direct TikTok search URL used for headless flows",
        example="https://www.tiktok.com/search/funny%20cats",
    )
    limit: Optional[int] = Field(
        default=20,
        ge=1,
        le=100,
        description="Additional limit applied to normalized results",
    )
    offset: Optional[int] = Field(
        default=0,
        ge=0,
        description="Pagination offset for normalized results",
    )

    model_config = ConfigDict(extra="allow")


class TikTokSearchResponse(BaseModel):
    """Response schema for TikTok search calls."""

    results: List[TikTokContentItem] = Field(
        ...,
        description="Ordered collection of TikTok content items",
    )
    totalResults: int = Field(
        ...,
        description="Total number of results reported by upstream",
        example=150,
    )
    query: str = Field(
        ...,
        description="Normalized search query echo",
        example="funny cats",
    )
    search_metadata: TikTokSearchMetadata = Field(
        ...,
        description="Execution metadata describing how the search ran",
    )
    execution_mode: str = Field(
        default="unknown",
        description="Raw browser execution mode (deprecated in favor of search_metadata.executed_path)",
    )

    model_config = ConfigDict(extra="forbid")

