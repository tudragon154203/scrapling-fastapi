<!-- 
Sync Impact Report:
- Version change: 1.4.0 → 1.4.1 (PATCH - updated spec-related code location from .specify/src/ to specify_src/)
- Modified principles: Spec-Driven Code Location
- No added/removed sections
- Templates requiring updates: ✅ .specify/templates/plan-template.md, ✅ .specify/templates/tasks-template.md
- No follow-up TODOs - all requirements specified
-->

# Scrapling FastAPI Constitution

## Core Principles

### I. Layered Architecture
Every feature must follow the layered architecture principle (API/Core/Middleware/Schemas/Services). Services must be organized by domain specificity (browser, common, crawler, tiktok). Clear separation of concerns required - no mixing of layers.

### II. FastAPI-First Design  
Use FastAPI as the primary web framework with automatic OpenAPI documentation. Target environment: Python 3.10.8 on Windows. Leverage Pydantic 2.9 for data validation with Python 3.13 compatibility. Implement type hints throughout the application. Support both development and production deployment patterns.

### III. Test-Driven Development (NON-NEGOTIABLE)
TDD mandatory: Tests written → Implementation → Tests pass → Refactor. Red-Green-Refactor cycle strictly enforced. Parallel test execution via pytest-xdist. Minimize the number of integration tests, focusing on critical paths and external interactions. All new tests MUST adhere to the established test directory structure. All integration tests MUST be explicitly marked with `pytest.mark.integration` at the module level.

### IV. Scrapling-Centric Automation
Default to Scrapling/Camoufox for browser automation tasks. Implement anti-detection measures (fingerprinting, humanized actions). Support persistent user sessions and proxy rotation. Specialized handling for different targets (websites, APIs, social platforms).

### V. Environment-Driven Configuration
All configuration through environment variables (.env files). Pydantic-settings for type-safe configuration management. Development vs production deployment modes clearly defined. No hardcoded configuration values.

### VI. Spec-Driven Code Location
Spec-related code, including the main source code folder (`specify_src/`), MUST be located within the project root directory. It MUST NOT be placed within the `.specify/` directory.

## Security & Anti-Detection Requirements

Browser fingerprinting integration (BrowserForge). User session persistence and management. Proxy support for distributed crawling. Rate limiting and bot detection avoidance measures. GDPR compliance considerations for data processing.

## Quality Gates & Review Process

All PRs must include test coverage and pass CI checks. Code review required for all schema changes. Integration tests must pass for web scraping endpoints. Security review required for any anti-detection features. Performance benchmarks for scraping operations. All code MUST pass `flake8` linting checks for `app/` and `tests/` directories. Post-Implementation Cleanup: All intermediate files/folders created during implementation MUST be removed.

## Governance

Constitution is the supreme governance document. All code must comply with layered architecture principles. Amendments require documentation and migration planning. Versioning follows semantic versioning with impact assessment. Use GEMINI.md as runtime development guidance reference.

**Version**: 1.4.1 | **Ratified**: 2025-09-21 | **Last Amended**: 2025-09-22