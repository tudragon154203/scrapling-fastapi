# Tasks: One-Shot Import Hoisting

**Input**: Design documents from `O:\n8n-compose\scrapling-fastapi\specs\022-one-shot-import\`
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
- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Python project with ast, argparse, pathlib dependencies
- [ ] T003 [P] Configure linting and formatting tools

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Contract test CLI --dry-run mode in tests/unit/test_cli_dry_run.py
- [ ] T005 [P] Contract test CLI --apply mode in tests/unit/test_cli_apply.py
- [ ] T006 [P] Contract test script accepts --include, --exclude flags in tests/unit/test_cli_flags.py
- [ ] T007 [P] Integration test nested import detection in tests/integration/test_nested_import_detection.py
- [ ] T008 [P] Integration test import grouping and alphabetizing in tests/integration/test_import_grouping.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T009 [P] AST parser module in scripts/ast_parser.py
- [ ] T010 [P] Import analyzer for detecting nested imports in scripts/import_analyzer.py
- [ ] T011 [P] Import categorization (stdlib, third-party, local) in scripts/import_categorizer.py
- [ ] T012 [P] Import grouping and alphabetizing logic in scripts/import_organizer.py
- [ ] T013 [P] AST transformer for safe import hoisting in scripts/transformer.py
- [ ] T014 [P] CLI interface with argparse in scripts/hoist_imports_once.py
- [ ] T015 [P] File discovery and filtering logic in scripts/file_finder.py
- [ ] T016 [P] Diff generation for dry-run mode in scripts/diff_generator.py
- [ ] T017 [P] Safety rules implementation (skip try/except, conditional imports) in scripts/safety_checker.py
- [ ] T018 Main script integration combining all components in scripts/hoist_imports_once.py

## Phase 3.4: Integration
- [ ] T019 Connect AST parser to import analyzer
- [ ] T020 Connect import analyzer to transformer
- [ ] T021 Connect transformer to CLI interface
- [ ] T022 Connect CLI to file discovery and diff generation
- [ ] T023 Test validation against real codebase files

## Phase 3.5: Polish
- [ ] T024 [P] Unit tests for safety rules in tests/unit/test_safety_rules.py
- [ ] T025 [P] Performance tests for large files in tests/performance/test_hoisting_performance.py
- [ ] T026 Error handling and logging improvements
- [ ] T027 [P] Update script usage documentation in scripts/README.md
- [ ] T028 Run comprehensive test suite against app/ directory

## Dependencies
- Tests (T004-T008) before implementation (T009-T023)
- T009 blocks T012, T019
- T010 blocks T011, T020
- T011 blocks T012, T021
- T022 blocks T023, T028
- Implementation before polish (T024-T028)

## Parallel Example
```
# Launch T004-T008 together:
Task: "Contract test CLI --dry-run mode in tests/unit/test_cli_dry_run.py"
Task: "Contract test CLI --apply mode in tests/unit/test_cli_apply.py"
Task: "Contract test script accepts --include, --exclude flags in tests/unit/test_cli_flags.py"
Task: "Integration test nested import detection in tests/integration/test_nested_import_detection.py"
Task: "Integration test import grouping and alphabetizing in tests/integration/test_import_grouping.py"
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

- [ ] All contracts have corresponding tests
- [ ] All entities have model tasks
- [ ] All tests come before implementation
- [ ] Parallel tasks truly independent
- [ ] Each task specifies exact file path
- [ ] No task modifies same file as another [P] task

## Parallel Execution Guide

### Phase 3.2 Tests (All can run in parallel)
```
T004: tests/unit/test_cli_dry_run.py
T005: tests/unit/test_cli_apply.py  
T006: tests/unit/test_cli_flags.py
T007: tests/integration/test_nested_import_detection.py
T008: tests/integration/test_import_grouping.py
```

### Phase 3.3 Core Implementation (Mostly parallel)
```
T009: scripts/ast_parser.py
T010: scripts/import_analyzer.py
T011: scripts/import_categorizer.py
T012: scripts/import_organizer.py
T013: scripts/transformer.py
T014: scripts/hoist_imports_once.py (CLI)
T015: scripts/file_finder.py
T016: scripts/diff_generator.py
T017: scripts/safety_checker.py
```

### Phase 3.5 Polish (Some parallel)
```
T024: tests/unit/test_safety_rules.py
T025: tests/performance/test_hoisting_performance.py
T027: scripts/README.md
```