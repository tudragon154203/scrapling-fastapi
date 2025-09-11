# PRD: TikTok Search Endpoint

Status: Draft (MVP ready for implementation)
Owner: Backend/API
Last Updated: 2025-09-11

## Summary
- Problem: Teams need a reliable way to programmatically search TikTok and retrieve structured video results for analysis and downstream workflows. Today, a working demo exists that automates search in the browser and post-processes the HTML into JSON, but there isn’t a formal API contract or productized endpoint.
- Goal: Ship a stable POST `/tiktok/search` endpoint that uses the existing browser automation approach to perform a search and returns normalized JSON results consistent with the demo’s output.
- Non‑Goals: Official TikTok API integration, hashtag/user search, deep metadata (comments, views, sounds), pagination/infinite scroll, advanced sort/filter beyond relevance in v1.

## Users & Use Cases
- Content researchers: Find relevant videos by keyword(s) to study trends.
- Growth/Marketing: Source examples and inspiration for campaigns.
- Internal automations: Feed downstream pipelines with lightweight, normalized metadata.

## Scope (v1)
- Video search via keywords (single string or array of strings).
- Sorting: RELEVANCE only.
- Result limit: up to 50 items; default 50.
- Recency: accept parameter but treat as best‑effort (no strict guarantee in v1).
- Returns normalized fields aligned with demo post‑processing.
- Requires an active, logged‑in TikTok session (server‑managed).

Multi‑query semantics (arrays)
- When `query` is an array, the system performs a separate search for each child query in provided order, then deduplicates and aggregates results into a single response.
- Deduplication key priority: `id` (preferred) → `webViewUrl` (fallback).
- Aggregation order: preserve child query order; within each child query preserve TikTok’s relevance order; on duplicates keep the first occurrence.
- The `numVideos` limit applies to the aggregated result set (not per child query).

Out of Scope (v1)
- Hashtag and user search endpoints.
- Advanced sorting (MOST_LIKE, DATE_POSTED) and additional filters (length, sound).
- Pagination and guaranteed total counts beyond what’s parsed from the first results page.

## Assumptions & Dependencies
- Session: Server manages TikTok sessions via `/tiktok/session` (FastAPI, `TiktokService`). Logged‑in state is a prerequisite.
- Scraping: Uses Scrapling/Camoufox with humanized actions where needed; DOM may change.
- Post‑processing: HTML parsing via BeautifulSoup as in `demo/browsing_tiktok_post_process.py`.
- Settings: Uses `CAMOUFOX_USER_DATA_DIR` and app config (`app/core/config.py`).

## Success Metrics
- Reliability: ≥ 97% of calls return schema‑valid JSON.
- Robustness: ≤ 3% 5xx over rolling 7 days (excluding upstream outages/blocks).
- Utility: For top 100 “popular” queries internally defined, ≥ 95% return ≥ 1 result.

## Functional Requirements
- FR‑001: Accept `query` as string or array of strings; server normalizes to a single search string (space‑joined).
- FR‑002: Require an active, logged‑in TikTok session; otherwise return 409 with structured error.
- FR‑003: Return up to `numVideos` results (cap 50) from the initial results page after deterministic load + short scroll.
- FR‑004: Support `sortType=RELEVANCE` only in v1; reject others with 422.
- FR‑005: Accept `recencyDays` in request; treat as best‑effort hint (no strict filtering guarantees in v1).
- FR‑006: Normalize video objects to: `id`, `caption`, `authorHandle` (no leading `@`), `likeCount` (int), `uploadTime` (string), `webViewUrl` (absolute URL).
- FR‑007: Return `totalResults` (count of parsed items) and `query` (normalized string) at the top level as well.
- FR‑008: Validate input and return 422 for schema violations.
- FR‑009: Provide clear error codes/messages for session, scraping, and parsing failures.
- FR‑010: If `query` is an array, run searches for each child query sequentially, deduplicate by `id` or `webViewUrl`, aggregate into one list, and cap to `numVideos` total.

## Non‑Functional Requirements
- NFR‑Rate‑Limit: Soft throttle to minimize detection; default 1 concurrent search per process, configurable.
- NFR‑Observability: Structured logs for start/finish, durations, counts, failure reasons; basic metrics.
- NFR‑Security: No storage of PII; do not persist scraped bodies beyond processing; leverage existing session sandboxing.
- NFR‑Resilience: DOM‑selector fallbacks; tolerant parsing for likes and timestamps.

## API Contract
- Method/Path: POST `/tiktok/search`
- Authentication: Server‑managed TikTok session must be logged in via `/tiktok/session`. If not logged in: HTTP 409 with structured error.

Request Body
```
{
  "query": "string | string[]",   // required
  "numVideos": 50,                 // optional, int, 1..50 (default 50)
  "sortType": "RELEVANCE",        // optional, enum: RELEVANCE (v1 only)
  "recencyDays": "ALL"            // optional, enum: ALL | 24H | 7_DAYS | 30_DAYS | 90_DAYS | 180_DAYS (best‑effort)
}
```

Validation
- `query`: required; if array, non‑empty elements; trim length 1..100 each; normalize by space‑joining.
- `numVideos`: integer 1..50; default 50; values >50 → 422.
- `sortType`: must be `RELEVANCE` in v1; others → 422.
- `recencyDays`: one of listed enums; best‑effort only in v1.

Response Body
```
{
  "results": [
    {
      "id": "string",
      "caption": "string",          // normalized caption/title text
      "authorHandle": "string",     // no leading '@'
      "likeCount": 12345,            // integer; K/M suffixes parsed
      "uploadTime": "string",       // ISO8601 when parseable; else raw/relative label
      "webViewUrl": "string"        // absolute URL to video
    }
  ],
  "totalResults": 1,
  "query": "normalized query string"
}
```

Error Responses (shape)
```
// 409 Not Logged In
{
  "error": {
    "code": "NOT_LOGGED_IN",
    "message": "TikTok session is not logged in",
    "details": {"method": "dom_api_combo", "timeout": 8}
  }
}

// 422 Validation
{
  "error": {"code": "VALIDATION_ERROR", "message": "...", "fields": {...}}
}

// 429 Rate Limited
{
  "error": {"code": "RATE_LIMITED", "message": "Too many requests"}
}

// 500 Internal / 503 Upstream
{
  "error": {"code": "SCRAPE_FAILED", "message": "...", "details": {...}}
}
```

## Behavior Details (Implementation‑Aligned)
- Session Gate: Reuse `TiktokService` to ensure a valid, logged‑in session; return 409 if not.
- Navigation: Load TikTok, perform search, wait for a deterministic signal (URL contains `/search`), then short humanized scroll (≈10s) to let content render; capture HTML.
- Parsing: Replicate `demo/browsing_tiktok_post_process.py` heuristics:
  - Containers: `div[id^="column-item-video-container-"]`
  - Extract `webViewUrl` via `a[href*="/video/"]` etc.; derive `id` from last path segment
  - Caption: prefer `.search-card-video-caption`, fallbacks with text‑based filters
  - Author handle: regex capture from URL path (`/@{handle}/`), stored without `@`
  - Likes: parse `K`/`M` to integers
  - Upload time: attempt full dates, partial dates, then relative tokens (e.g., `6d`, `ago`)
- Result Count: `totalResults` equals parsed array length; no pagination in v1.
- Multi‑query execution: For array inputs, repeat the above navigation+parsing per child query, merge results in child‑query order, dedupe on `id` then `webViewUrl`, keep first occurrence, then truncate to `numVideos`.

## Examples
Request
```
POST /tiktok/search
Content-Type: application/json

{
  "query": ["funny", "cats"],
  "numVideos": 20,
  "sortType": "RELEVANCE",
  "recencyDays": "7_DAYS"
}
```

Response
```
{
  "results": [
    {
      "id": "7515379584414633238",
      "caption": "Funny cat compilation #funny #cats",
      "authorHandle": "catlover2023",
      "likeCount": 12500,
      "uploadTime": "2023-05-15",
      "webViewUrl": "https://www.tiktok.com/@catlover2023/video/7515379584414633238"
    }
  ],
  "totalResults": 1,
  "query": "funny cats"
}
```

## Observability & Telemetry
- Logs: `search.started`, `search.loaded`, `search.parsed`, `search.failed` with durations, result counts, and key parameters (query length, limit).
- Metrics: request count, success/error rates by code, p50/p95/p99 latencies, average parsed results.
- Sampling: Capture limited HTML snapshots on failures (size‑capped, redacted) for debugging.

## Risks & Mitigations
- DOM changes: Maintain a prioritized selector list; add integration tests using recorded fixtures; fail gracefully with `SCRAPE_FAILED`.
- Rate limiting / detection: Humanized actions, soft concurrency caps, jittered waits.
- Localization/encoding: UTF‑8 throughout; retain raw `uploadTime` strings if normalization fails.
- Inconsistent fields: Standardize on `caption` (not `title`) and `authorHandle` without `@` to match demo and reduce ambiguity.

## Open Questions
- Should `uploadTime` be strictly normalized to ISO8601 (requiring additional page fetch/parsing) or remain best‑effort with raw labels in v1?
- Do we need to expose pagination/cursor now, or wait until v2?
- Is a client‑visible “session token” required, or is server‑managed login state sufficient for our deployment model?
- Should we include optional fields like `authorUrl`, `thumbnailUrl` if cheaply derivable?

## Release Plan
- Dev: Implement endpoint + schema + post‑processing service; verify with demo HTML and live session.
- Staging: Enable soft rate limit; monitor errors, adjust selectors.
- Prod: Roll out with alerting; document operational runbooks.

## References (Repo)
- Demo automation: `demo/browsing_tiktok_search.py`
- Demo HTML fixture: `demo/browsing_tiktok_search.html`
- Demo post‑processor: `demo/browsing_tiktok_post_process.py`
- Demo JSON sample: `demo/browsing_tiktok_search.json`
- Session service: `app/api/routes.py:176`, `app/services/tiktok/service.py`
