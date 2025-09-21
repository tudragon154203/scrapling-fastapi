# Research: Change TikTok Search Headless/Headful Behaviour

## Technical Context Clarifications

### Performance Goals
**Decision**: No specific performance goals needed for this feature
**Rationale**: This feature is about controlling browser execution mode, not performance optimization
**Alternatives considered**: Setting specific response time targets, but these would be application-level concerns rather than feature-specific

### Constraints
**Decision**: Minimal constraints - feature should maintain backward compatibility
**Rationale**: The feature should not break existing functionality while adding the new capability
**Alternatives considered**: Adding extensive validation, but this would complicate the implementation unnecessarily

### Scale/Scope
**Decision**: Feature applies to all TikTok search requests
**Rationale**: The feature is a behavioral switch that should work consistently across all requests
**Alternatives considered**: Limiting to specific user tiers, but this would add unnecessary complexity

## Technology Research

### Headless/Headful Browser Control in Scrapling
**Decision**: Use Scrapling's built-in headless parameter control
**Rationale**: Scrapling (based on Playwright) provides native support for controlling browser execution mode
**Alternatives considered**: Custom browser management, but this would duplicate existing functionality

### Parameter Validation in FastAPI
**Decision**: Use FastAPI's Pydantic models for parameter validation
**Rationale**: FastAPI provides built-in validation with clear error responses
**Alternatives considered**: Manual validation, but this would be less maintainable and error-prone

### Test Context Detection in Python
**Decision**: Use environment variables or pytest markers to detect test context
**Rationale**: Standard approach in Python testing frameworks
**Alternatives considered**: Custom context managers, but environment detection is simpler and more reliable

## Implementation Approach

### Browser Mode Control
**Decision**: Pass the headless parameter directly to Scrapling's browser launch function
**Rationale**: Direct integration with the underlying library provides the most reliable control
**Alternatives considered**: Wrapper functions, but direct parameter passing is simpler and more maintainable

### Parameter Handling
**Decision**: Make force_headful an optional boolean parameter with default behavior
**Rationale**: Optional parameters with sensible defaults provide good UX while maintaining backward compatibility
**Alternatives considered**: Required parameters or different data types, but these would break existing integrations

### Test Context Override
**Decision**: Check for test environment at runtime and force headless mode
**Rationale**: Ensures consistent test execution regardless of parameter values
**Alternatives considered**: Compile-time directives, but runtime checking is more flexible