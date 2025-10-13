# Tasks: Change TikTok Search Headless/Headful Behaviour

**Input**: Design documents from `/specs/001-change-tiktok-search/`
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
- **Single project**: `specify_src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 3.1: Setup
- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Python project with FastAPI and Scrapling dependencies
- [ ] T003 [P] Configure linting and formatting tools (flake8, black, isort)

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

- [ ] T004 [P] Contract test for default headless behavior in tests/contract/test_default_headless.py
- [ ] T005 [P] Contract test for force headful mode in tests/contract/test_force_headful.py
- [ ] T006 [P] Contract test for explicit headless mode in tests/contract/test_explicit_headless.py
- [ ] T007 [P] Contract test for test environment override in tests/contract/test_test_override.py
- [ ] T008 [P] Contract test for invalid parameter validation in tests/contract/test_invalid_parameter.py
- [ ] T009 [P] Integration test for default search behavior in tests/integration/test_default_search.py
- [ ] T010 [P] Integration test for headful search behavior in tests/integration/test_headful_search.py
- [ ] T011 [P] Integration test for test environment behavior in tests/integration/tiktok/test_environment_search_behavior.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T012 [P] BrowserMode enum in specify_src/models/browser_mode.py
- [ ] T013 [P] ExecutionContext model in specify_src/models/execution_context.py
- [ ] T014 [P] SearchRequest model with force_headful parameter in specify_src/models/search_request.py
- [ ] T015 [P] ExecutionContext service for test detection in specify_src/services/execution_context_service.py
- [ ] T016 [P] Browser mode determination service in specify_src/services/browser_mode_service.py
- [ ] T017 TikTok search service with mode control in specify_src/services/tiktok_search_service.py
- [ ] T018 POST /tiktok/search endpoint implementation
- [ ] T019 Input validation for force_headful parameter
- [ ] T020 Error handling for invalid parameters

## Phase 3.4: Integration
- [ ] T021 Connect browser mode service to Scrapling
- [ ] T022 Implement test environment detection using environment variables
- [ ] T023 Add logging for browser mode decisions
- [ ] T024 Update TikTok search endpoint to use new services

## Phase 3.5: Polish
- [ ] T025 [P] Unit tests for browser mode service in tests/unit/test_browser_mode_service.py
- [ ] T026 [P] Unit tests for execution context service in tests/unit/test_execution_context_service.py
- [ ] T027 Performance tests for search endpoint
- [ ] T028 [P] Update docs/api.md with new parameter
- [ ] T029 [P] Update README.md with usage examples
- [ ] T030 Remove any code duplication
- [ ] T031 Run manual testing using quickstart examples

## Dependencies
- Tests (T004-T011) before implementation (T012-T020)
- T012-T014 block T015-T017
- T015-T017 block T018-T020
- T018-T020 block T021-T024
- Implementation before polish (T025-T031)

## Parallel Example
```
# Launch T004-T008 together:
Task: "Contract test for default headless behavior in tests/contract/test_default_headless.py"
Task: "Contract test for force headful mode in tests/contract/test_force_headful.py"
Task: "Contract test for explicit headless mode in tests/contract/test_explicit_headless.py"
Task: "Contract test for test environment override in tests/contract/test_test_override.py"
Task: "Contract test for invalid parameter validation in tests/contract/test_invalid_parameter.py"

# Launch T009-T011 together:
Task: "Integration test for default search behavior in tests/integration/test_default_search.py"
Task: "Integration test for headful search behavior in tests/integration/test_headful_search.py"
Task: "Integration test for test environment behavior in tests/integration/tiktok/test_environment_search_behavior.py"

# Launch T012-T014 together:
Task: "BrowserMode enum in specify_src/models/browser_mode.py"
Task: "ExecutionContext model in specify_src/models/execution_context.py"
Task: "SearchRequest model with force_headful parameter in specify_src/models/search_request.py"

# Launch T015-T017 together:
Task: "ExecutionContext service for test detection in specify_src/services/execution_context_service.py"
Task: "Browser mode determination service in specify_src/services/browser_mode_service.py"
Task: "TikTok search service with mode control in specify_src/services/tiktok_search_service.py"

# Launch T025-T026 together:
Task: "Unit tests for browser mode service in tests/unit/test_browser_mode_service.py"
Task: "Unit tests for execution context service in tests/unit/test_execution_context_service.py"

# Launch T028-T029 together:
Task: "Update docs/api.md with new parameter"
Task: "Update README.md with usage examples"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Avoid: vague tasks, same file conflicts

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

- [x] All contracts have corresponding tests
- [x] All entities have model tasks
- [x] All tests come before implementation
- [x] Parallel tasks truly independent
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task