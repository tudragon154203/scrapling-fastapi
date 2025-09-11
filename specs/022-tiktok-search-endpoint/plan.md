# Implementation Plan: TikTok Search Endpoint

**Branch**: 022-tiktok-search-endpoint | **Date**: 2025-09-11 | **Spec**: link
**Input**: Feature specification from `/specs/022-tiktok-search-endpoint/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
4. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
5. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, or `GEMINI.md` for Gemini CLI).
6. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
7. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
8. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Extract from feature spec: primary requirement + technical approach from research

The TikTok search endpoint provides search functionality for TikTok content including videos, hashtags, and users. Users can search using single or multiple keywords, filter by recency, and control result limits. The endpoint requires a valid TikTok session for authentication and returns structured metadata about search results.

Based on existing TikTok session research, the implementation will leverage the current Scrapling-based browser automation framework with Camoufox for anti-detection, extend the existing TikTokService class, and reuse the TikTokSession infrastructure for authentication validation.

## Technical Context
**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, Scrapling, BrowserForge, Camoufox, Pydantic 2.9  
**Storage**: N/A (real-time web scraping)  
**Testing**: pytest (contract, integration, unit tests)  
**Target Platform**: Linux server (production), Windows (development)  
**Project Type**: web (backend only)  
**Performance Goals**: 100ms response time for search execution, handle 10 concurrent searches  
**Constraints**: <500ms API response time, reuse existing TikTok session infrastructure, TikTok rate limiting compliance  
**Scale/Scope**: Single endpoint for video search, extendable to hashtag/user search in future

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: [1] (max 3 - api, cli, tests) 
- Using framework directly? (no wrapper classes) ✓ - Using FastAPI directly
- Single data model? (no DTOs unless serialization differs) ✓ - Pydantic schemas handle validation
- Avoiding patterns? (no Repository/UoW without proven need) ✓ - Direct API service approach

**Architecture**:
- EVERY feature as library? (no direct app code) ✓ - app.services.tiktok.search library
- Libraries listed: [tiktok_search + purpose: TikTok search functionality]
- CLI per library: [Not required for API endpoint]
- Library docs: llms.txt format planned? ✓ - Will include service dependencies

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? (test MUST fail first) ✓ - Will implement failing tests first
- Git commits show tests before implementation? ✓ - Will follow this pattern
- Order: Contract→Integration→E2E→Unit strictly followed? ✓ - Will implement in this order
- Real dependencies used? (actual DBs, not mocks) ✓ - Real TikTok scraping via Scrapling
- Integration tests for: new libraries, contract changes, shared schemas? ✓ - TikTok API integration tests
- FORBIDDEN: Implementation before test, skipping RED phase ✓ - Will follow strictly

**Observability**:
- Structured logging included? ✓ - Will add logging using standard logging library
- Frontend logs → backend? (unified stream) ✓ - N/A for backend-only
- Error context sufficient? ✓ - Will include TikTok session context in errors

**Versioning**:
- Version number assigned? (MAJOR.MINOR.BUILD) ✓ - Will increment BUILD on changes
- BUILD increments on every change? ✓ - Will implement version tracking
- Breaking changes handled? (parallel tests, migration plan) ✓ - Will follow API versioning

## Project Structure

### Documentation (this feature)
```
specs/022-tiktok-search-endpoint/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: Option 1 (single project) - Backend-only API endpoint extending existing FastAPI service structure

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - NEEDS CLARIFICATION: session format and validation not specified - research existing TikTok session mechanism
   - Performance targets: 100ms response time may be challenging for web scraping operations
   - Rate limiting compliance: TikTok's scraping terms need research for safe operation

2. **Generate and dispatch research agents**:
   - Research existing TikTokSession authentication mechanism and session management
   - Research TikTok web scraping approaches and rate limiting considerations
   - Research Scrapling best practices for search result extraction
   - Research existing service patterns in the codebase

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - SearchQuery: Single string or array of keywords
   - TikTokVideo: ID, title, authorHandle, likeCount, uploadTime, webViewUrl
   - SearchResult: Array of TikTokVideo, totalResults, query
   - SearchRequest: query, numVideos, sortType, recencyDays

2. **Generate API contracts** from functional requirements:
   - POST /tiktok/search endpoint
   - OpenAPI schema for request/response validation
   - Error handling for authentication, validation, and scraping errors

3. **Generate contract tests** from contracts:
   - Test request validation schema
   - Test response structure validation
   - Test error scenarios (auth errors, parameter validation)
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Single keyword search integration test
   - Multiple keyword search integration test
   - Authentication failure integration test
   - Quickstart test = basic search workflow validation

5. **Update agent file incrementally** (O(1) operation):
   - Add TikTok search service documentation
   - Preserve existing service patterns
   - Keep under 150 lines for token efficiency

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Contract tests for search endpoint schema validation
- Entity creation for search request/response models
- Integration tests for search functionality
- Implementation tasks following TDD order

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Models → Service → API endpoint
- Parallel tasks where possible (independent components)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | All constitutional requirements satisfied | N/A |

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [ ] Phase 0: Research complete (/plan command)
- [ ] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [ ] Initial Constitution Check: PASS
- [ ] Post-Design Constitution Check: PASS
- [ ] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*