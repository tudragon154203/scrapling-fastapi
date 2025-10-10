"""Service for handling TikTok search operations."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from app.services.tiktok.search.interfaces import TikTokSearchInterface
from app.services.tiktok.search.multistep import TikTokMultiStepSearchService
from app.services.tiktok.search.url_param import TikTokURLParamSearchService

try:
    import httpx
except Exception:  # pragma: no cover - httpx is provided by test dependencies
    httpx = None


class TikTokSearchService(TikTokSearchInterface):
    """Main TikTok search service that orchestrates different search strategies."""

    def __init__(
        self,
        force_headful: bool = False,
    ) -> None:
        from app.core.config import get_settings
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self._force_headful = force_headful

    async def search(
        self,
        query: Union[str, List[str]],
        num_videos: int = 50,
    ) -> Dict[str, Any]:
        """Execute a TikTok search using the configured strategy."""
        self.logger.debug(
            "[TikTokSearchService] search called - query: %s, num_videos: %s",
            query,
            num_videos,
        )

        try:
            search_impl = self._build_search_implementation()
            result = await search_impl.search(
                query,
                num_videos=num_videos,
            )
            if self._should_attempt_fallback(result):
                self.logger.info(
                    "[TikTokSearchService] Primary search returned no results; attempting HTTP fallback"
                )
                fallback_result = await self._fallback_http_search(
                    query=query,
                    num_videos=num_videos,
                )
                if fallback_result is not None:
                    result = fallback_result
            self.logger.debug(
                "[TikTokSearchService] Search completed successfully - total results: %s",
                len(result.get("results", [])),
            )
            return result
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("[TikTokSearchService] Exception in search: %s", exc, exc_info=True)
            return {"error": f"Search failed: {exc}"}

    def _build_search_implementation(self) -> TikTokSearchInterface:
        """Instantiate the configured search implementation based on force_headful parameter."""
        # Use force_headful to determine the search implementation
        # True = browser-based search (multistep)
        # False = headless search (url param)
        if not self._force_headful:
            return TikTokURLParamSearchService()

        user_data_dir = getattr(self.settings, "camoufox_user_data_dir", None)
        if not user_data_dir:
            self.logger.warning(
                "[TikTokSearchService] camoufox_user_data_dir not configured; running without persistent user data"
            )

        else:
            master_dir = Path(user_data_dir) / "master"
            master_ready = False
            try:
                master_ready = master_dir.exists() and any(master_dir.iterdir())
            except Exception:
                master_ready = False
            if not master_ready:
                self.logger.warning(
                    "[TikTokSearchService] camoufox master profile missing or empty; running with ephemeral user data"
                )

        return TikTokMultiStepSearchService(force_headful=getattr(self, '_force_headful', False))

    def _should_attempt_fallback(self, result: Dict[str, Any]) -> bool:
        """Return True when the HTTP fallback should be attempted."""
        if not isinstance(result, dict):
            return False

        if result.get("error"):
            return False

        total_raw = result.get("totalResults")
        try:
            total = int(total_raw)
        except (TypeError, ValueError):
            total = 0

        if total > 0:
            return False

        results = result.get("results")
        if isinstance(results, list) and results:
            return False

        return True

    async def _fallback_http_search(
        self,
        *,
        query: Union[str, List[str]],
        num_videos: int,
    ) -> Optional[Dict[str, Any]]:
        """Perform a lightweight HTTP search when browser automation fails."""

        if httpx is None:
            self.logger.warning(
                "[TikTokSearchService] httpx is unavailable; cannot execute HTTP fallback"
            )
            return None

        queries = self._normalize_query_payload(query)
        if not queries:
            return None

        aggregated: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        limit = max(0, min(int(num_videos or 0), 50))
        if limit == 0:
            limit = 10

        timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=5.0)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            for normalized_query in queries:
                try:
                    response = await client.get(
                        "https://www.tikwm.com/api/feed/search",
                        params={"keywords": normalized_query, "count": max(limit, 10)},
                    )
                except Exception as exc:  # pragma: no cover - network flakiness
                    self.logger.warning(
                        "[TikTokSearchService] HTTP fallback request failed for %s: %s",
                        normalized_query,
                        exc,
                    )
                    continue

                if response.status_code != 200:
                    self.logger.warning(
                        "[TikTokSearchService] HTTP fallback received status %s for %s",
                        response.status_code,
                        normalized_query,
                    )
                    continue

                try:
                    payload = response.json()
                except Exception as exc:  # pragma: no cover - defensive against HTML responses
                    self.logger.warning(
                        "[TikTokSearchService] HTTP fallback could not decode JSON for %s: %s",
                        normalized_query,
                        exc,
                    )
                    continue
                videos = (
                    payload.get("data", {}).get("videos")
                    if isinstance(payload, dict)
                    else None
                )
                if not videos:
                    self.logger.warning(
                        "[TikTokSearchService] HTTP fallback returned no videos for %s",
                        normalized_query,
                    )
                    continue

                for item in videos:
                    if not isinstance(item, dict):
                        continue
                    video_id = str(item.get("video_id") or "")
                    author = item.get("author") or {}
                    if not isinstance(author, dict):
                        author = {}
                    author_handle = str(
                        author.get("unique_id")
                        or author.get("id")
                        or author.get("sec_uid")
                        or ""
                    ).lstrip("@")
                    if video_id and video_id in seen_ids:
                        continue
                    if not video_id:
                        continue

                    seen_ids.add(video_id)
                    web_url = ""
                    if author_handle:
                        web_url = f"https://www.tiktok.com/@{author_handle}/video/{video_id}"

                    aggregated.append(
                        {
                            "id": video_id,
                            "caption": str(item.get("title") or ""),
                            "authorHandle": author_handle,
                            "likeCount": int(item.get("digg_count") or 0),
                            "uploadTime": str(item.get("create_time") or ""),
                            "webViewUrl": web_url,
                        }
                    )

                    if len(aggregated) >= limit:
                        break

                if len(aggregated) >= limit:
                    break

        if not aggregated:
            return None

        normalized_query = " ".join(queries)
        final_results = aggregated[:limit]
        return {
            "results": final_results,
            "totalResults": len(final_results),
            "query": normalized_query,
        }

    def _normalize_query_payload(self, query: Union[str, List[str]]) -> List[str]:
        """Normalize query payload into a non-empty list of search strings."""

        if isinstance(query, list):
            return [str(item).strip() for item in query if str(item or "").strip()]

        value = str(query or "").strip()
        return [value] if value else []
