# TikTok Search Strategy Removal - Data Model

**Date**: 2025-09-23 | **Feature**: TikTok Search Strategy Removal

## Entities

### TikTok Search Request
**Purpose**: API request for TikTok search content
**Fields**:
- `query` (string, required): Search query terms
- `force_headful` (boolean, required): Determines search method - True for browser-based, False for headless
- `search_url` (string, optional): Direct search URL for headless mode (removed strategy dependency)
- `limit` (integer, optional): Maximum number of results (default: 20)
- `offset` (integer, optional): Result offset for pagination (default: 0)

**Validation Rules**:
- `force_headful` must be boolean (accepts: True/false, TRUE/FALSE, 1/0)
- `query` must be non-empty string
- `search_url` must be valid URL when force_headful=False
- `limit` must be positive integer (max: 100)
- `offset` must be non-negative integer

**State Transitions**:
- Request validation → Route selection (browser vs headless path)
- Processing → Search execution
- Completion → Response generation

### TikTok Search Response
**Purpose**: API response containing TikTok search results
**Fields**:
- `results` (array, required): Array of TikTok content items
- `total_count` (integer, required): Total number of available results
- `search_metadata` (object, required): Information about the search execution
- `executed_path` (string, required): Method used for search ("browser-based" or "headless")
- `execution_time` (float, required): Time taken for search execution in seconds
- `request_hash` (string, required): Unique identifier for this request

**Validation Rules**:
- `results` must contain valid TikTok content objects
- `total_count` must match actual result count
- `executed_path` must be "browser-based" or "headless"
- `execution_time` must be positive number

**State Transitions**:
- Generated → Sent to client
- Received → Consumed by API consumer

### Force Headful Parameter
**Purpose**: Boolean flag determining search execution method
**Fields**:
- Value (boolean): True for browser-based search, False for headless search
- Acceptable formats: True/false, TRUE/FALSE, 1/0

**Validation Rules**:
- Strict boolean logic enforcement
- Lenient string parsing support
- Error response for invalid values

**State Transitions**:
- Input → Validation → Path Selection → Execution

### API Consumer
**Purpose**: External systems using the TikTok search endpoint
**Fields**:
- `client_id` (string): Unique identifier for the client system
- `access_timestamp` (datetime): Last successful access time
- `search_history` (array): Previous search requests for analytics

**Validation Rules**:
- Client identification for rate limiting
- Access tracking for monitoring

## Data Relationships

### TikTok Search Request → TikTok Search Response
**Relationship**: One-to-one
- Each request generates exactly one response
- Response contains results specific to the request parameters

### Force Headful Parameter → TikTok Search Request
**Relationship**: Many-to-one
- Multiple requests can use the same force_headful value
- Value determines which search method is used

### API Consumer → TikTok Search Request
**Relationship**: One-to-many
- API consumer can make multiple search requests
- Each request is logged against the consumer

## Constraints

### Data Volume Assumptions
- Typical search requests: 1-10 parameters
- Result sets: 1-100 items per request
- Request frequency: Moderate (typical web scraping usage)

### Performance Considerations
- Response validation must be fast (<50ms)
- Parameter validation cannot impact search performance
- Error response generation must be efficient

### Integration Constraints
- Existing consumers must update their request format
- Error responses must follow existing API patterns
- Response structure must remain backward compatible where possible

## Schema Updates Required

### Request Schema Changes
1. **Remove**: `strategy` parameter
2. **Update**: `force_headful` parameter validation rules
3. **Modify**: Error messages for strategy field rejection
4. **Update**: Parameter validation logic

### Response Schema Changes
1. **Remove**: All strategy-related fields
2. **Add**: `executed_path` field indicating method used
3. **Update**: Any strategy references in metadata
4. **Modify**: Error response structure for invalid parameters

## Migration Path

### Strategy Field Migration
1. **Phase 1**: Add validation to reject strategy field immediately
2. **Phase 2**: Update documentation to reflect new parameters
3. **Phase 3**: Provide migration guidance for existing integrations
4. **Phase 4**: Remove any remaining strategy references (if any)

### Force Headful Parameter Migration
1. **Strategy "browser"** → `force_headful: True`
2. **Strategy "headless"** → `force_headful: False`
3. **Strategy "auto"** → Remove logic, rely solely on force_headful

## Validation Rules Matrix

| Entity | Field | Valid Values | Error Response |
|--------|-------|--------------|----------------|
| TikTok Search Request | force_headful | True/false, TRUE/FALSE, 1/0 | "Invalid force_headful value" |
| TikTok Search Request | query | Non-empty string | "Query parameter is required" |
| TikTok Search Request | strategy | [REJECTED] | "Strategy parameter is not supported" |
| TikTok Search Response | executed_path | "browser-based", "headless" | Auto-validated |
| TikTok Search Response | results | Array of TikTok items | Auto-validated |

## Future Considerations

### Scalability
- Parameter validation must handle high request volumes
- Error response generation must be efficient
- Schema serialization must not impact performance

### Extensibility
- New search parameters can be added without breaking changes
- Response structure allows for additional metadata
- Error patterns are standardized and extensible