# TikTok API Documentation

## Overview

The TikTok API provides endpoints for searching TikTok content and downloading TikTok videos. The API supports configurable browser execution modes and strategy selection for different use cases.

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
  "force_headful": true
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string or array | Yes | Search query as string or array of strings |
| numVideos | integer | No | Number of videos to return (1-50, default: 50) |
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

### POST /tiktok/download

Download TikTok videos by resolving direct MP4 URLs. The endpoint supports different download strategies configurable via environment variables.

#### Request

```http
POST /tiktok/download
Content-Type: application/json
```

**Request Body:**

```json
{
  "url": "https://www.tiktok.com/@username/video/1234567890"
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| url | string | Yes | Full TikTok video URL |

#### Response

```json
{
  "status": "success",
  "message": "Video found and resolved successfully",
  "download_url": "https://example.com/video.mp4",
  "video_info": {
    "id": "1234567890",
    "description": "Amazing video caption",
    "author": "username",
    "duration": 15.5,
    "view_count": 1000000,
    "like_count": 50000,
    "share_count": 1000,
    "comment_count": 500
  },
  "execution_time": 3.24
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| status | string | Operation status ("success" or "error") |
| message | string | Human-readable status message |
| download_url | string | Direct MP4 URL for downloading the video |
| video_info | object | Video metadata including engagement metrics |
| execution_time | number | Time taken to resolve the video (seconds) |

#### Download Strategies

The TikTok download endpoint supports multiple strategies for resolving video URLs. The strategy is selected using the `TIKTOK_DOWNLOAD_STRATEGY` environment variable:

| Strategy | Environment Value | Description | Browser Engine |
|----------|-------------------|-------------|----------------|
| Camoufox | `camoufox` | Uses Camoufox with StealthyFetcher for enhanced anti-detection | Camoufox (Firefox-based) |
| Chromium | `chromium` | Uses DynamicFetcher with Playwright's Chromium engine | Chromium (Chrome-based) |

**Environment Configuration:**

```bash
# Use Camoufox strategy (default for enhanced stealth)
export TIKTOK_DOWNLOAD_STRATEGY=camoufox

# Use Chromium strategy (Chrome-based browser)
export TIKTOK_DOWNLOAD_STRATEGY=chromium
```

If no environment variable is set, the system defaults to `chromium`.

#### Strategy Selection Behavior

- **Case Insensitive**: Strategy names are case-insensitive (`CAMOUFOX`, `Camoufox`, and `camoufox` all work)
- **Default Fallback**: If an invalid strategy is specified, the system will raise a `ValueError`
- **Runtime Selection**: The strategy is selected once at application startup and remains consistent for all requests

#### Examples

**Basic download request:**
```bash
curl -X POST "http://localhost:5681/tiktok/download" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.tiktok.com/@username/video/1234567890"}'
```

**Using with environment variable:**
```bash
# Set strategy before starting the application
export TIKTOK_DOWNLOAD_STRATEGY=camoufox
python -m uvicorn app.main:app --host 0.0.0.0 --port 5681 --reload

# Then make requests normally
curl -X POST "http://localhost:5681/tiktok/download" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.tiktok.com/@username/video/1234567890"}'
```

#### Error Responses

**Invalid TikTok URL:**
```json
{
  "status": "error",
  "message": "Invalid TikTok URL format"
}
```
Status: 400 BAD REQUEST

**Video not found or private:**
```json
{
  "status": "error",
  "message": "Video not found or access restricted"
}
```
Status: 404 NOT FOUND

**Resolution failed:**
```json
{
  "status": "error",
  "message": "Failed to resolve video URL after retries",
  "execution_time": 30.0
}
```
Status: 500 INTERNAL SERVER ERROR

**Invalid strategy configuration:**
```json
{
  "detail": "Unsupported TikTok download strategy: invalid_strategy. Supported strategies: camoufox, chromium"
}
```
Status: 500 INTERNAL SERVER ERROR (occurs at startup)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TIKTOK_DOWNLOAD_STRATEGY` | `chromium` | Download strategy to use (`camoufox` or `chromium`) |
| `TIKVID_BASE` | `https://tikvid.io/vi` | Base URL for TikVid resolver service |

### Strategy-Specific Notes

#### Camoufox Strategy
- **Advantages**: Enhanced anti-detection capabilities, better at bypassing bot detection
- **Use Cases**: When target TikTok content has strong anti-bot measures
- **Dependencies**: Requires `camoufox` package to be installed

#### Chromium Strategy
- **Advantages**: Faster performance, wider compatibility
- **Use Cases**: General purpose downloading, performance-critical applications
- **Dependencies**: Uses Playwright's built-in Chromium engine