# TikTok Search Strategy Removal - Quickstart Guide

**Date**: 2025-09-23 | **Feature**: TikTok Search Strategy Removal

## Quick Overview

This guide helps you quickly understand and test the updated TikTok search functionality with simplified parameter structure.

## What Changed

### Before (Old API)
```json
{
  "query": "funny cats",
  "strategy": "browser", // or "headless", "auto"
  "limit": 10
}
```

### After (New API)
```json
{
  "query": "funny cats",
  "force_headful": true, // Boolean only!
  "limit": 10
}
```

## Quick Test

### Test 1: Browser-Based Search
```bash
curl -X POST "http://localhost:5681/tiktok/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "funny cats",
    "force_headful": true,
    "limit": 5
  }'
```

**Expected**: Response with `"executed_path": "browser-based"`

### Test 2: Headless Search
```bash
curl -X POST "http://localhost:5681/tiktok/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "funny cats",
    "force_headful": false,
    "limit": 5
  }'
```

**Expected**: Response with `"executed_path": "headless"`

### Test 3: Strategy Field Rejection (should fail)
```bash
curl -X POST "http://localhost:5681/tiktok/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "funny cats",
    "force_headful": true,
    "strategy": "browser" // This should cause an error!
  }'
```

**Expected**: 400 Bad Request with error message mentioning strategy parameter

## Key Changes

### Parameter Migration
| Old Strategy | New Force Headful | Description |
|--------------|-------------------|-------------|
| strategy: "browser" | force_headful: true | Browser-based search with full automation |
| strategy: "headless" | force_headful: false | Headless URL parameter search |
| strategy: "auto" | Use force_headful explicitly | Simplified decision logic |

### Force Headful Acceptable Values
The API accepts multiple boolean representations:
- `true`, `false` (recommended)
- `"true"`, `"false"` (case-insensitive)
- `"TRUE"`, `"FALSE"`
- `1`, `0`

### Error Responses
- **Strategy field errors**: 400 Bad Request with message "The strategy parameter is not supported"
- **Invalid force_headful**: 422 Validation Error with specific field details
- **Missing required fields**: 422 Unprocessable Entity

## Integration Steps

### Step 1: Update Your Code
Replace old strategy parameter with force_headful boolean:

```python
# OLD
data = {
    "query": "search term",
    "strategy": "browser",
    "limit": 10
}

# NEW
data = {
    "query": "search term",
    "force_headful": True,  # Boolean only
    "limit": 10
}
```

### Step 2: Test Your Integration
Run your integration tests to ensure:
- Force headful boolean values work correctly
- Strategy field rejection works as expected
- Response structure matches the new contract

### Step 3: Update Documentation
Update any API documentation to:
- Remove strategy parameter references
- Add force_headful parameter with boolean type
- Update migration guidance

## Troubleshooting

### Common Errors

**Error**: `"strategy parameter is not supported"`
**Fix**: Remove any `strategy` parameters from your requests

**Error**: Invalid force_headful value
**Fix**: Use boolean values only (true/false, "true"/"false", 1/0)

**Response**: No `executed_path` field
**Fix**: Check for missing required fields (query, force_headful)

### Migration Checklist

- [ ] Remove all `strategy` parameter usage
- [ ] Replace with `force_headful` boolean parameter
- [ ] Update request validation logic
- [ ] Update error handling for strategy rejection
- [ ] Update API documentation
- [ ] Update test cases
- [ ] Run integration tests

## Testing

### Run Contract Tests
```bash
# Navigate to project root
cd O:/n8n-compose/scrapling-fastapi/feat-remove-strategy-arg-tiktok-search

# Run specific contract tests
python -m pytest specs/feat/remove-strategy-arg-tiktok-search/contracts/test_tiktok_search_endpoint.py -v

# Run all tests
python -m pytest
```

### Validate API Contract
Use the OpenAPI specification to validate your implementation:

```bash
# View OpenAPI docs (when server is running)
open http://localhost:5681/docs

# Or use the spec directly
cat specs/feat/remove-strategy-arg-tiktok-search/contracts/tiktok-search-openapi.yaml
```

## Next Steps

1. **Implementation**: Follow the generated tasks to implement the changes
2. **Testing**: Run the contract tests to verify implementation
3. **Documentation**: Update any user-facing documentation
4. **Deployment**: Deploy changes and monitor for integration issues

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the full specification in `spec.md`
3. Run the contract tests to identify specific problems
4. Consult the research findings in `research.md`

---

**Remember**: The strategy parameter has been completely removed. Only use `force_headful` with boolean values for search method selection.