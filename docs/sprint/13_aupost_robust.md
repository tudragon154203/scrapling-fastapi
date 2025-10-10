Title: Make /crawl/auspost accept full details URL

Summary
- Extend AusPost crawl endpoint to accept either a tracking code or a full details URL (e.g. https://auspost.com.au/mypost/track/details/36LB45032230).
- Keep all additional fields the same (`force_user_data`, `force_headful`).
- Backwards compatible: existing requests with `tracking_code` still work unchanged.

Changes
- Schema update: `app/schemas/auspost.py`
  - `AuspostCrawlRequest.tracking_code` validator now:
    - Trims whitespace
    - Detects full details URLs and extracts the trailing tracking code
    - Validates non-empty result
- Minor docs update: `app/api/routes.py` docstring mentions URL support.
- No changes to crawler logic; the extracted code is entered into the search form as before.

API
- Endpoint: POST `/crawl/auspost`
- Request body fields:
  - `tracking_code`: string — may be either a raw code or a full details URL
  - `force_user_data`: boolean (optional)
  - `force_headful`: boolean (optional)

Examples
1) Using a raw tracking code
```
curl -s -X POST http://localhost:8000/crawl/auspost \
  -H 'Content-Type: application/json' \
  -d '{
        "tracking_code": "36LB45032230"
      }'
```

2) Using a full details URL
```
curl -s -X POST http://localhost:8000/crawl/auspost \
  -H 'Content-Type: application/json' \
  -d '{
        "tracking_code": "https://auspost.com.au/mypost/track/details/36LB45032230"
      }'
```

Behavior
- When a full URL is supplied, the server extracts `36LB45032230` and proceeds identically to a raw code request.
- Response mirrors previous behavior and includes the normalized `tracking_code` value.

Notes
- If an invalid AusPost details URL is provided (cannot extract a code), the request fails validation with a clear error message.
