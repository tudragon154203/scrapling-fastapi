# Quickstart: Change TikTok Search Headless/Headful Behaviour

## Overview
This feature allows users to control whether TikTok searches run in headless or headful browser mode through an optional `force_headful` parameter.

## Prerequisites
- Python 3.11
- FastAPI
- Scrapling library
- pytest (for testing)

## Usage

### Default Behavior (Headless)
By default, all TikTok searches run in headless mode:

```bash
curl -X POST "http://localhost:8000/tiktok/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "funny videos"}'
```

### Force Headful Mode
To run in headful mode, set `force_headful` to `true`:

```bash
curl -X POST "http://localhost:8000/tiktok/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "funny videos", "force_headful": true}'
```

### Explicit Headless Mode
To explicitly request headless mode:

```bash
curl -X POST "http://localhost:8000/tiktok/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "funny videos", "force_headful": false}'
```

## Testing
In test environments, searches will always run in headless mode regardless of the `force_headful` parameter:

```bash
# This will still run in headless mode in test environment
pytest tests/test_tiktok_search.py
```

## Response Format
All requests return a JSON response with the following structure:

```json
{
  "results": [...],
  "execution_mode": "headless",  // or "headful"
  "message": "Search completed successfully"
}
```

## Error Handling
Invalid values for `force_headful` will result in a 422 validation error:

```json
{
  "detail": [
    {
      "loc": ["body", "force_headful"],
      "msg": "value could not be parsed to a boolean",
      "type": "type_error.bool"
    }
  ]
}
```

## Implementation Details
1. The feature maintains backward compatibility - existing integrations continue to work unchanged
2. Test environments always override the `force_headful` parameter to ensure consistent test execution
3. The browser execution mode is determined per request and does not affect other concurrent requests