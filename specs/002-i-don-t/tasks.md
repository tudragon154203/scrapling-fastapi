# Tasks: Refactor Logging for Implementation Detail Hiding

**Input**: Design documents from `/specs/002-i-don-t/`
**Prerequisites**: plan.md (required), research.md, spec.md

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
- [ ] T001 Review and confirm current logging configuration in `app/core/config.py` and `app/core/logging.py` to ensure flexibility for level changes.
- [ ] T002 Configure `flake8` to include checks for `logger.info` usage in sensitive areas (if possible, or rely on manual review).

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

- [ ] T003 [P] Create an integration test `tests/integration/test_logging_debug_sensitive.py` to assert that internal/sensitive log messages are *not* visible at `INFO` level. This test should initially fail.
- [ ] T004 [P] Create an integration test `tests/integration/test_logging_info_public.py` to assert that general user-facing log messages *are* visible at `INFO` level. This test should initially pass.

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T005 Identify all `logger.info` calls in `app/services/` that reveal implementation details or crawling methods.
- [ ] T006 Change identified `logger.info` calls to `logger.debug` in `app/services/`.
- [ ] T007 Identify all `logger.info` calls in `app/api/` that reveal implementation details or crawling methods.
- [ ] T008 Change identified `logger.info` calls to `logger.debug` in `app/api/`.
- [ ] T009 Review `app/main.py` and `app/core/` for any `logger.info` calls that should be `logger.debug`.
- [ ] T010 Modify logging configuration in `app/core/logging.py` to ensure `DEBUG` level messages are only shown when explicitly configured (e.g., via environment variable).

## Phase 3.4: Integration
- [ ] T011 Verify that the application's logging configuration correctly interprets environment variables for setting the logging level.

## Phase 3.5: Polish
- [ ] T012 Run `flake8` linting across the project to ensure no new linting issues were introduced.
- [ ] T013 Run all tests (`pytest`) to ensure no regressions were introduced by logging changes.
- [ ] T014 Manually test the application with `INFO` and `DEBUG` logging levels to confirm expected behavior.

## Dependencies
- T003, T004 must be written and fail/pass before T005-T010.
- T005-T010 must be completed before T011.
- T011 must be completed before T012-T014.

## Parallel Example
```
# Launch T003-T004 together:
Task: "Create integration test tests/integration/test_logging_debug_sensitive.py"
Task: "Create integration test tests/integration/test_logging_info_public.py"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Avoid: vague tasks, same file conflicts

## Task Generation Rules
*Applied during main() execution*

1. **From Data Model**:
   - Each entity → model creation task [P]
   - Relationships → service layer tasks
   
2. **From User Stories**:
   - Each story → integration test [P]
   - Quickstart scenarios → validation tasks

3. **Ordering**:
   - Setup → Tests → Models → Services → Endpoints → Polish
   - Dependencies block parallel execution

## Validation Checklist
*GATE: Checked by main() before returning*

- [ ] All entities have model tasks
- [ ] All tests come before implementation
- [ ] Parallel tasks truly independent
- [ ] Each task specifies exact file path
- [ ] No task modifies same file as another [P] task