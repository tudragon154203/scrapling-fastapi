# Tasks: TikTok Search Strategy Removal

**Input**: Design documents from `/specs/feat/remove-strategy-arg-tiktok-search/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `specify_src/`, `tests/` at repository root (constitution compliant)
- **Web app**: `backend/specify_src/`, `frontend/specify_src/`
- **Mobile**: `api/specify_src/`, `ios/specify_src/` or `android/specify_src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 3.1: Setup
- [ ] T001 Create project structure per implementation plan (FastAPI service structure)
- [ ] T002 Initialize Python project with FastAPI, Scrapling, BrowserForge, Pydantic 2.9 dependencies
- [ ] T003 [P] Configure linting and formatting tools (flake8, black, isort)

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Contract test POST /tiktok/search in tests/contract/test_tiktok_search_endpoint.py
- [ ] T005 [P] Integration test browser-based search in tests/integration/test_tiktok_search_browser.py
- [ ] T006 [P] Integration test headless search in tests/integration/test_tiktok_search_headless.py
- [ ] T007 [P] Integration test strategy field rejection in tests/integration/test_tiktok_search_validation.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T008 [P] TikTok search request/response models in specify_src/models/tiktok_search.py
- [ ] T009 [P] TikTok content models in specify_src/models/tiktok_content.py
- [ ] T010 TikTok search service with strategy field removal logic in specify_src/services/tiktok_search_service.py
- [ ] T011 [P] TikTok headless search executor in specify_src/services/executors/headless_executor.py
- [ ] T012 [P] TikTok browser search executor in specify_src/services/executors/browser_executor.py
- [ ] T013 Updated TikTok search API endpoint in specify_src/api/endpoints/tiktok_search.py
- [ ] T014 Force headful parameter validation logic
- [ ] T015 Strategy field rejection error handling
- [ ] T016 Updated request/response schemas in specify_src/schemas/tiktok_search.py

## Phase 3.4: Integration
- [ ] T017 Connect TikTok search service to existing browser automation infrastructure
- [ ] T018 Updated middleware for parameter validation
- [ ] T019 Request/response logging with search metadata
- [ ] T020 Error handling integration with existing API patterns

## Phase 3.5: Polish
- [ ] T021 [P] Unit tests for force_headful validation in tests/unit/test_tiktok_validation.py
- [ ] T022 Performance tests (<200ms response time)
- [ ] T023 [P] Update API documentation in docs/api.md
- [ ] T024 Remove duplicate strategy field references
- [ ] T025 Run quickstart test scenarios from quickstart.md

## Dependencies
- Tests (T004-T007) before implementation (T008-T016)
- T008 blocks T010
- T011, T012 block T013
- T013 blocks T017, T018
- Implementation before polish (T021-T025)

## Parallel Example
```
# Launch T004-T007 together:
Task: "Contract test POST /tiktok/search in tests/contract/test_tiktok_search_endpoint.py"
Task: "Integration test browser-based search in tests/integration/test_tiktok_search_browser.py"
Task: "Integration test headless search in tests/integration/test_tiktok_search_headless.py"
Task: "Integration test strategy field rejection in tests/integration/test_tiktok_search_validation.py"

# Launch T008-T009 together:
Task: "TikTok search request/response models in specify_src/models/tiktok_search.py"
Task: "TikTok content models in specify_src/models/tiktok_content.py"

# Launch T011-T012 together:
Task: "TikTok headless search executor in specify_src/services/executors/headless_executor.py"
Task: "TikTok browser search executor in specify_src/services/executors/browser_executor.py"

# Launch T021-T023 together:
Task: "Unit tests for force_headful validation in tests/unit/test_tiktok_validation.py"
Task: "Update API documentation in docs/api.md"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Avoid: vague tasks, same file conflicts
- Follow TDD: Red-Green-Refactor cycle strictly

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts**:
   - Each contract file → contract test task [P]
   - Each endpoint → implementation task

2. **From Data Model**:
   - Each entity → model creation task [P]
   - Relationships → service layer tasks

3. **From User Stories**:
   - Each story → integration test [P]
   - Quickstart scenarios → validation tasks

4. **Ordering**:
   - Setup → Tests → Models → Services → Endpoints → Polish
   - Dependencies block parallel execution

## Validation Checklist
*GATE: Checked by main() before returning*

- [ ] All contracts have corresponding tests
- [ ] All entities have model tasks
- [ ] All tests come before implementation
- [ ] Parallel tasks truly independent
- [ ] Each task specifies exact file path
- [ ] No task modifies same file as another [P] task

## Constitution Compliance
- TDD Mandatory: Tests written before implementation ✓
- Layered Architecture: Models → Services → Endpoints ✓
- FastAPI-First: Uses existing FastAPI framework ✓
- Test Structure: Proper test directory organization in tests/ ✓
- Flake8 Compliance: Will pass linting checks for specify_src/ and tests/ ✓
- Spec-Driven Code Location: Uses specify_src/ at project root (not .specify/) ✓

## Migration Mapping
- T002: Initialize project with updated dependencies
- T010: Remove strategy field logic from service
- T013: Update endpoint to use force_headful parameter
- T018: Integrate with existing middleware
- T025: Validate quickstart test scenarios pass