# Tasks: TikTok Search Endpoint

**Input**: Design documents from `/specs/022-tiktok-search-endpoint/`
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
- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 3.1: Setup
- [ ] T001 Add Scrapling and BrowserForge dependencies to requirements.txt
- [ ] T002 Configure pytest for contract, integration, and unit tests
- [ ] T003 [P] Set up linting with flake8 and formatting with black

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Contract test POST /tiktok/search in tests/contract/test_tiktok_search_post.py
- [ ] T005 [P] Contract test TikTok search request validation schema in tests/contract/test_tiktok_search_schema.py
- [ ] T006 [P] Integration test single keyword search in tests/integration/test_tiktok_search_single.py
- [ ] T007 [P] Integration test multiple keyword search in tests/integration/test_tiktok_search_multiple.py
- [ ] T008 [P] Integration test authentication failure in tests/integration/test_tiktok_search_auth.py
- [ ] T009 [P] Integration test result limits and filtering in tests/integration/test_tiktok_search_filtering.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T010 [P] TikTok search request schema in app/schemas/tiktok_search.py
- [ ] T011 [P] TikTok search response schema in app/schemas/tiktok_search.py
- [ ] T012 [P] TikTokVideo model in app/schemas/tiktok_search.py
- [ ] T013 TikTok search service in app/services/tiktok/search_service.py
- [ ] T014 TikTok search executor in app/services/tiktok/search_executor.py
- [ ] T015 POST /tiktok/search endpoint in app/api/routes.py
- [ ] T016 Input validation and error handling for search endpoint

## Phase 3.4: Integration
- [ ] T017 Connect TikTok search to existing TikTok session validation
- [ ] T018 Search result logging and monitoring
- [ ] T019 Rate limiting for TikTok search requests
- [ ] T020 Error handling for TikTok scraping failures

## Phase 3.5: Polish
- [ ] T021 [P] Unit tests for search validation logic in tests/unit/test_tiktok_search_validation.py
- [ ] T022 Performance tests for search endpoint (<500ms response time)
- [ ] T023 [P] Update API documentation for /tiktok/search endpoint
- [ ] T024 Remove code duplication and optimize search performance
- [ ] T025 Integration test with real TikTok session for end-to-end validation

## Dependencies
- Tests (T004-T009) before implementation (T010-T016)
- T010 blocks T013, T015
- T013 blocks T015
- T015 blocks T017, T018, T019, T020
- Implementation before polish (T021-T025)

## Parallel Example
```
# Launch T004-T009 together:
Task: "Contract test POST /tiktok/search in tests/contract/test_tiktok_search_post.py"
Task: "Contract test TikTok search request validation schema in tests/contract/test_tiktok_search_schema.py"
Task: "Integration test single keyword search in tests/integration/test_tiktok_search_single.py"
Task: "Integration test multiple keyword search in tests/integration/test_tiktok_search_multiple.py"
Task: "Integration test authentication failure in tests/integration/test_tiktok_search_auth.py"
Task: "Integration test result limits and filtering in tests/integration/test_tiktok_search_filtering.py"

# Launch T010-T012 together after tests pass:
Task: "TikTok search request schema in app/schemas/tiktok_search.py"
Task: "TikTok search response schema in app/schemas/tiktok_search.py"
Task: "TikTokVideo model in app/schemas/tiktok_search.py"

# Launch T021-T023 together:
Task: "Unit tests for search validation logic in tests/unit/test_tiktok_search_validation.py"
Task: "Performance tests for search endpoint (<500ms response time)"
Task: "Update API documentation for /tiktok/search endpoint"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Avoid: vague tasks, same file conflicts
- Reuse existing TikTok session infrastructure from app/services/tiktok/

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