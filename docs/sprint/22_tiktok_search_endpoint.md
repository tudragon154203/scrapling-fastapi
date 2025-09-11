# TikTok Search Endpoint

## Overview
The TikTok Search endpoint provides search functionality for TikTok content including videos, hashtags, and users. This endpoint allows searching for TikTok content using keywords and returns structured data about the search results.

## Endpoint
```
POST /tiktok/search
```

## Authentication
This endpoint requires a valid TikTok session. Users must be logged in to TikTok for search functionality to work properly.

## Request Schema

```json
{
  "query": "string or array of strings",
  "numVideos": 50,
  "sortType": "RELEVANCE",
  "recencyDays": "ALL"
}
```

### Fields

| Field | Type | Required | Description | Default |
|-------|------|----------|-------------|---------|
| `query` | string or array | Yes | One or more keywords to search for | N/A |
| `numVideos` | integer | No | Maximum number of videos to return | 50 |
| `sortType` | string | No | Sorting method for results | "RELEVANCE" |
| `recencyDays` | string | No | Filter results by recency | "ALL" |

### Sort Type Options
- `RELEVANCE` - Sort by relevance to search query
- `MOST_LIKE` - Sort by number of likes (to be implemented)
- `DATE_POSTED` - Sort by date posted (to be implemented)

### Recency Days Options
- `ALL` - No time filter
- `24H` - Last 24 hours
- `7_DAYS` - Last 7 days
- `30_DAYS` - Last 30 days
- `90_DAYS` - Last 90 days
- `180_DAYS` - Last 180 days

## Response Schema

```json
{
  "results": [
    {
      "id": "string",
      "title": "string",
      "authorHandle": "string",
      "likeCount": "integer",
      "uploadTime": "string",
      "webViewUrl": "string"
    }
  ],
  "totalResults": "integer",
  "query": "string"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | Array of search results |
| `results[].id` | string | Unique identifier for the video |
| `results[].title` | string | Title of the video |
| `results[].authorHandle` | string | TikTok handle of the video author |
| `results[].likeCount` | integer | Number of likes on the video |
| `results[].uploadTime` | string | Timestamp when the video was uploaded |
| `results[].webViewUrl` | string | URL to view the video on TikTok |
| `totalResults` | integer | Total number of results found |
| `query` | string | The query used for the search |

## Example Request

```bash
curl -X POST http://localhost:8001/tiktok/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -d '{
    "query": ["funny", "cats"],
    "numVideos": 20,
    "sortType": "RELEVANCE",
    "recencyDays": "7_DAYS"
  }'
```

## Example Response

```json
{
  "results": [
    {
      "id": "7082978387123456789",
      "title": "Funny cat compilation #funny #cats",
      "authorHandle": "@catlover2023",
      "likeCount": 12500,
      "uploadTime": "2023-05-15T14:30:00Z",
      "webViewUrl": "https://www.tiktok.com/@catlover2023/video/7082978387123456789"
    }
  ],
  "totalResults": 1,
  "query": "funny cats"
}
```

## Error Responses

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Valid TikTok session required"
}
```

### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Invalid query parameters"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "Search failed due to internal error"
}
```

## Implementation Notes

1. **Session Requirement**: A valid TikTok session is required for search functionality. Users must be logged in to TikTok.

2. **Rate Limiting**: Search requests may be rate-limited to prevent abuse and comply with TikTok's terms of service.

3. **Search Scope**: Currently supports video search. Hashtag and user search will be implemented in future updates.

4. **Result Limitations**: The number of results returned may be limited by TikTok's API and scraping constraints.

5. **Data Freshness**: Search results reflect the current state of TikTok content and may change over time.

## Future Enhancements

1. **Advanced Sorting**: Implementation of `MOST_LIKE` and `DATE_POSTED` sorting options
2. **Hashtag Search**: Dedicated hashtag search functionality
3. **User Search**: Search for TikTok users by username or display name
4. **Filter Options**: Additional filters for video length, sound, and other attributes
5. **Search Suggestions**: Auto-complete functionality for search queries