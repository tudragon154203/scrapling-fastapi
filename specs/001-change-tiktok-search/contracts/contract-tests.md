# Contract Tests: TikTok Search API

## Test: Default Headless Behavior
**Description**: Verify that searches run in headless mode by default when force_headful is not provided.

**Test Steps**:
1. Send a POST request to /tiktok/search with a query but no force_headful parameter
2. Verify the response includes execution_mode: "headless"

**Expected Result**: 
```json
{
  "results": [...],
  "execution_mode": "headless",
  "message": "Search completed successfully"
}
```

## Test: Force Headful Mode
**Description**: Verify that searches run in headful mode when force_headful is explicitly set to true.

**Test Steps**:
1. Send a POST request to /tiktok/search with a query and force_headful: true
2. Verify the response includes execution_mode: "headful"

**Expected Result**:
```json
{
  "results": [...],
  "execution_mode": "headful",
  "message": "Search completed successfully"
}
```

## Test: Headless Multistep Fallback
**Description**: Verify that multistep requests automatically fall back to the direct strategy when the browser runs in headless mode.

**Test Steps**:
1. Send a POST request to /tiktok/search with strategy: "multistep" and force_headful: false (or omit the flag)
2. Verify the response includes execution_mode: "headless" and returns results without error

**Expected Result**:
```json
{
  "results": [...],
  "execution_mode": "headless",
  "message": "Search completed using headless-safe direct strategy"
}
```

## Test: Explicit Headless Mode
**Description**: Verify that searches run in headless mode when force_headful is explicitly set to false.

**Test Steps**:
1. Send a POST request to /tiktok/search with a query and force_headful: false
2. Verify the response includes execution_mode: "headless"

**Expected Result**: 
```json
{
  "results": [...],
  "execution_mode": "headless",
  "message": "Search completed successfully"
}
```

## Test: Test Environment Override
**Description**: Verify that in test environments, searches always run in headless mode regardless of force_headful parameter.

**Test Steps**:
1. Set test environment context
2. Send a POST request to /tiktok/search with a query and force_headful: true
3. Verify the response includes execution_mode: "headless" (override)

**Expected Result**: 
```json
{
  "results": [...],
  "execution_mode": "headless",
  "message": "Search completed in test environment"
}
```

## Test: Invalid Parameter Validation
**Description**: Verify that invalid values for force_headful result in validation errors.

**Test Steps**:
1. Send a POST request to /tiktok/search with a query and force_headful: "invalid"
2. Verify the response is a 422 validation error

**Expected Result**: 
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