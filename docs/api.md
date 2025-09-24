# TikTok Search API Documentation

## Overview

The TikTok Search API provides endpoints for searching TikTok content with optional control over browser execution mode. Users can specify whether the search should run in headless or headful mode, with special handling for test environments.

## Endpoints

### POST /tiktok/search

Search TikTok content with optional control over browser execution mode.

#### Request

```http
POST /tiktok/search
Content-Type: application/json
```

**Request Body:**

```json
{
  "query": "funny cats",
  "numVideos": 50,
  "sortType": "RELEVANCE",
  "recencyDays": "ALL",
  "strategy": "multistep",
  "force_headful": true
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string or array | Yes | Search query as string or array of strings |
| numVideos | integer | No | Number of videos to return (1-50, default: 50) |
| sortType | string | No | Sort type for results (only "RELEVANCE" supported, default: "RELEVANCE") |
| recencyDays | string | No | Recency filter for results (default: "ALL") |
| strategy | string | No | Search strategy to use ("direct" or "multistep", default: "multistep") |
| force_headful | boolean | No | Forces headful browser mode if True (optional, defaults to False) |

#### Response

```json
{
  "results": [
    {
      "id": "1234567890",
      "title": "Funny Cat Video",
      "url": "https://www.tiktok.com/@user/video/1234567890",
      "thumbnail": "https://p16-sign.tiktokcdn.com/tos-maliva-avt-0068/...",
      "author": "username",
      "views": 1000000,
      "likes": 50000,
      "comments": 1000,
      "shares": 500,
      "createTime": "2025-09-20T10:30:00Z"
    }
  ],
  "totalResults": 1,
  "query": "funny cats",
  "execution_mode": "headful"
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| results | array | List of TikTok videos |
| totalResults | integer | Total number of results |
| query | string | Normalized query string |
| execution_mode | string | Browser execution mode used for this search ("headless" or "headful") |

#### Browser Execution Mode Control

The API provides flexible control over browser execution mode:

1. **Default Behavior**: All searches run in headless mode by default
2. **Force Headful**: When `force_headful` is set to `true`, searches run in headful mode (optional parameter defaults to False)
3. **Explicit Headless**: When `force_headful` is set to `false`, searches run in headless mode
4. **Test Environment Override**: In test environments, all searches run in headless mode regardless of the `force_headful` parameter

#### Test Environment Detection

The API automatically detects test environments using the following indicators:
- `PYTEST_CURRENT_TEST` environment variable (set by pytest)
- `TESTING=true` environment variable
- `CI=true` environment variable

#### Examples

**Default headless search:**
```bash
curl -X POST "http://localhost:5681/tiktok/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "funny videos"}'
```

**Force headful mode:**
```bash
curl -X POST "http://localhost:5681/tiktok/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "funny videos", "force_headful": true}'
```

**Explicit headless mode:**
```bash
curl -X POST "http://localhost:5681/tiktok/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "funny videos", "force_headful": false}'
```

#### Error Responses

**Invalid parameter validation:**
```json
{
  "detail": [
    {
      "loc": ["body", "force_headful"],
      "msg": "Input should be a valid boolean",
      "type": "bool_parsing"
    }
  ]
}
```
Status: 422 UNPROCESSABLE ENTITY

**Other errors:**
```json
{
  "error": {
    "code": "SCRAPE_FAILED",
    "message": "Browser automation failed: Timeout"
  }
}
```
Status: 500 INTERNAL SERVER ERROR