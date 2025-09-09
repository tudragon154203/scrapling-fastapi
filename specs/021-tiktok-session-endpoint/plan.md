# Implementation Plan: TikTok Session Endpoint

**Branch**: `021-tiktok-session-endpoint` | **Date**: 2025-09-09 | **Spec**: [link](O:/n8n-compose/scrapling-fastapi/docs/sprint/21_tiktok_session_endpoint.md)
**Input**: Feature specification from `/specs/021-tiktok-session-endpoint/spec.md`

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
The TikTok Session endpoint provides interactive browsing capabilities for TikTok with automatic login status checking. Similar to the existing `/browse` endpoint, it includes TikTok-specific login detection using DOM elements, API request interception, and fallback mechanisms. The endpoint returns 409 if the user is not logged in, uses read-only user data directory cloning, and provides full interactive capabilities when logged in.

## Technical Context
**Language/Version**: Python 3.10+  
**Primary Dependencies**: FastAPI, Scrapling, BrowserForge, Pydantic 2.9  
**Storage**: File-based user data management (clones of master directory)  
**Testing**: pytest (integration tests require real browser/network)  
**Target Platform**: Linux server (FastAPI backend)  
**Project Type**: single/web - determines source structure  
**Performance Goals**: Session management, login detection within 8s timeout  
**Constraints**: Read-only user data, 409 response for not logged in, 423 for locked directories  
**Scale/Scope**: Single endpoint with login detection, similar to existing /browse endpoint

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: [1] (api - within max 3)
- Using framework directly? (yes - FastAPI directly, no wrapper classes)
- Single data model? (yes - simple Pydantic models, no DTOs needed)
- Avoiding patterns? (yes - no Repository/UoW patterns, using direct browser automation)

**Architecture**:
- EVERY feature as library? (yes - creating dedicated service in `app/services/tiktok`)
- Libraries listed: [tiktok_service - encapsulates TikTok-specific logic and browsing]
- CLI per library: [not applicable for API feature]
- Library docs: llms.txt format planned? (yes - will be added to CLAUDE.md)

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? (yes - tests will be written first)
- Git commits show tests before implementation? (yes - following constitutional requirements)
- Order: Contract→Integration→E2E→Unit strictly followed? (yes - contract tests already created)
- Real dependencies used? (yes - real browser instances, actual TikTok calls)
- Integration tests for: new libraries, contract changes, shared schemas? (yes - browser integration tests planned)
- FORBIDDEN: Implementation before test, skipping RED phase (compliant)

**Observability**:
- Structured logging included? (yes - proxy values redacted, session tracking)
- Frontend logs → backend? (unified logging stream planned)
- Error context sufficient? (yes - detailed error codes and session info)

**Versioning**:
- Version number assigned? (yes - 1.0.0)
- BUILD increments on every change? (yes - following semantic versioning)
- Breaking changes handled? (yes - parallel tests, migration plan for future changes)

## Project Structure

### Documentation (this feature)
```
specs/021-tiktok-session-endpoint/
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
app/
├── services/
│   ├── tiktok/          # NEW: TikTok service implementation
│   ├── common/         # NEW: Abstract browsing executor
│   └── crawler/
│       └── existing dpd.py
├── api/
│   ├── routes.py        # NEW: TikTok session endpoint
│   └── existing endpoints
├── schemas/
│   ├── tiktok.py       # NEW: TikTok session schemas
│   └── existing schemas
└── main.py             # existing

tests/
├── contract/
│   └── test_tiktok_schema.py  # NEW: Contract tests
├── integration/
│   └── test_tiktok_session.py  # NEW: Integration tests
└── unit/
    └── test_tiktok_service.py   # NEW: Unit tests
```

**Structure Decision**: Option 1 - Single project (existing FastAPI structure)

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved ✓

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `/scripts/update-agent-context.sh [claude|gemini|copilot]` for your AI assistant
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file ✓

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P] 
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

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
| [None - all constitutional requirements met] | | |

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [✓] Phase 0: Research complete (/plan command)
- [✓] Phase 1: Design complete (/plan command)
- [✓] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [✓] Initial Constitution Check: PASS
- [✓] Post-Design Constitution Check: PASS
- [✓] All NEEDS CLARIFICATION resolved
- [✓] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*