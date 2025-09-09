# Tasks: TikTok Session Endpoint

**Input**: Design documents from `/specs/021-tiktok-session-endpoint/`
**Prerequisites**: research.md, data-model.md, contracts/, quickstart.md

## Execution Flow (main)
```
1. Load and analyze available design documents
   → research.md: Technical decisions and architecture patterns
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → quickstart.md: Test scenarios and validation steps
2. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests (TDD)
   → Core: models, services, endpoints
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
3. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
4. Number tasks sequentially (T001, T002...)
5. Generate dependency graph
6. Create parallel execution examples
7. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
8. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Existing project**: Use current codebase structure
- **FastAPI service**: app/src/ structure already exists
- **Test locations**: tests/ directory at repository root
- Paths shown below assume existing FastAPI project structure

## Phase 3.1: Setup
- [ ] T001 Ensure existing dependencies (FastAPI, Scrapling, BrowserForge, Pydantic 2.9) are installed
- [ ] T002 [P] Configure pytest testing framework with integration test support
- [ ] T003 [P] Set up linting and formatting tools (ruff, black)

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Contract test TikTokSessionRequest schema validation in tests/test_tiktok_session_request.py
- [ ] T005 [P] Contract test TikTokSessionResponse schema validation in tests/test_tiktok_session_response.py
- [ ] T006 [P] Contract test API endpoint responses (200, 409, 423, 504, 500) in tests/test_tiktok_api_contract.py
- [ ] T007 [P] Contract test login detection behavior in tests/test_tiktok_login_detection.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T008 [P] TikTokSessionRequest model in app/schemas/tiktok.py
- [ ] T009 [P] TikTokSessionResponse model in app/schemas/tiktok.py
- [ ] T010 [P] TikTokLoginState enum in app/schemas/tiktok.py
- [ ] T011 [P] TikTokSessionConfig settings in app/core/config.py
- [ ] T012 [P] AbstractBrowsingExecutor base class in app/services/common/executor.py
- [ ] T013 [P] TiktokExecutor browsing executor in app/services/tiktok/executor.py
- [ ] T014 [P] TiktokService business logic in app/services/tiktok/service.py
- [ ] T015 TikTok login detection utilities in app/services/tiktok/utils/login_detection.py
- [ ] T016 TikTok endpoint in app/api/routes.py
- [ ] T017 Input validation and request handling

## Phase 3.4: Integration
- [ ] T018 Connect TiktokService to browser automation framework
- [ ] T019 User data directory cloning and cleanup mechanisms
- [ ] T020 Error handling with proper HTTP status codes (409, 423, 504, 500)
- [ ] T021 Authentication and security middleware
- [ ] T022 Logging with proxy value redaction
- [ ] T023 Session timeout management

## Phase 3.5: Polish
- [ ] T024 [P] Unit tests for login detection logic in tests/unit/test_login_detection.py
- [ ] T025 Unit tests for user data management in tests/unit/test_user_data_management.py
- [ ] T026 Integration tests for browser sessions in tests/integration/test_tiktok_sessions.py
- [ ] T027 Performance tests (<200ms response time)
- [ ] T028 [P] Update API documentation in app/docs/api.md
- [ ] T029 Run manual testing scenarios from quickstart.md

## Dependencies
- Tests (T004-T007) before implementation (T008-T023)
- T012 AbstractBrowsingExecutor blocks T013 TiktokExecutor
- T013 TiktokExecutor blocks T014 TiktokService
- T014 TiktokService blocks T016 endpoint implementation
- T015 Login detection utilities block T014 TiktokService
- Implementation before polish (T024-T029)

## Parallel Example
```
# Launch T004-T007 together:
Task: "Contract test TikTokSessionRequest schema validation in tests/test_tiktok_session_request.py"
Task: "Contract test TikTokSessionResponse schema validation in tests/test_tiktok_session_response.py"
Task: "Contract test API endpoint responses in tests/test_tiktok_api_contract.py"
Task: "Contract test login detection behavior in tests/test_tiktok_login_detection.py"
```

```
# Launch T008-T013 together after tests are failing:
Task: "TikTokSessionRequest model in app/schemas/tiktok.py"
Task: "TikTokSessionResponse model in app/schemas/tiktok.py"
Task: "TikTokLoginState enum in app/schemas/tiktok.py"
Task: "TikTokSessionConfig settings in app/core/config.py"
Task: "AbstractBrowsingExecutor base class in app/services/common/executor.py"
Task: "TiktokExecutor browsing executor in app/services/tiktok/executor.py"
```

```
# Launch T024-T025 after core implementation:
Task: "Unit tests for login detection logic in tests/unit/test_login_detection.py"
Task: "Unit tests for user data management in tests/unit/test_user_data_management.py"
Task: "Unit tests for error handling in tests/unit/test_error_handling.py"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Avoid: vague tasks, same file conflicts
- Use existing project structure and dependencies

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