# Implementation Plan: One-Shot Import Hoisting

**Branch**: 022-one-shot-import | **Date**: 2025-09-12 | **Spec**: O:\n8n-compose\scrapling-fastapi\specs\022-one-shot-import\spec.md
**Input**: Feature specification from `O:\n8n-compose\scrapling-fastapi\specs\022-one-shot-import\spec.md`

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
Create a single-use Python script that moves safe nested imports to the top of modules under `app/`. The script will use AST parsing to identify nested imports, apply safety rules to avoid problematic cases (try/except blocks, conditional imports, etc.), group imports by category (stdlib, third-party, local), alphabetize within groups, and provide dry-run and apply modes with test validation.

## Technical Context
**Language/Version**: Python 3.10+ (based on existing codebase)  
**Primary Dependencies**: ast (stdlib), argparse (stdlib), pathlib (stdlib)  
**Storage**: N/A (file transformation only)  
**Testing**: pytest (existing test framework)  
**Target Platform**: Linux server (development environment)  
**Project Type**: single/web/mobile - determines source structure  
**Performance Goals**: Process all app/**/*.py files efficiently (<30 seconds)  
**Constraints**: Safe only - no circular import risks, no runtime behavior changes  
**Scale/Scope**: ~100 Python files in app/ directory excluding __init__.py and migrations

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: [1] (single throwaway script, no new libraries)
- Using framework directly? (yes - using ast module directly)
- Single data model? (no DTOs - simple AST nodes)
- Avoiding patterns? (no complex patterns - straightforward parsing)

**Architecture**:
- EVERY feature as library? (NO - this is explicitly a one-off script, not a reusable library)
- Libraries listed: N/A (single script for cleanup)
- CLI per library: [script with --dry-run, --apply, --include, --exclude flags]
- Library docs: N/A (throwaway script, no documentation needed)

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? (YES - tests will be written first)
- Git commits show tests before implementation? (YES)
- Order: Contract→Integration→E2E→Unit strictly followed? (YES)
- Real dependencies used? (YES - actual file parsing, not mocks)
- Integration tests for: new libraries, contract changes, shared schemas? (N/A - no new libraries)
- FORBIDDEN: Implementation before test, skipping RED phase (ENFORCED)

**Observability**:
- Structured logging included? (YES - clear diff output and error messages)
- Frontend logs → backend? (N/A - no frontend)
- Error context sufficient? (YES - specific file and line information)

**Versioning**:
- Version number assigned? (N/A - throwaway script)
- BUILD increments on every change? (N/A)
- Breaking changes handled? (N/A - one-time cleanup)

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
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

**Structure Decision**: Option 1 (Single project) - This is a simple one-off script transformation tool

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - No NEEDS CLARIFICATION found - all requirements are clear from spec
   - Research best practices for AST import manipulation in Python
   - Research existing patterns in the codebase for import organization

2. **Generate and dispatch research agents**:
   ```
   Task: "Research AST ImportFrom and Import node patterns in Python"
   Task: "Find best practices for safe import hoisting without breaking behavior"
   Task: "Analyze existing codebase import patterns under app/"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Python Module: Individual .py files containing import statements
   - Import Statement: Standard Python import or from...import declarations
   - Import Category: Classification as stdlib, third-party, or local/relative
   - Nested Import: Import statements inside conditional blocks, functions, etc.

2. **Generate API contracts** from functional requirements:
   - This is a CLI tool, not a web API - focus on script interface
   - Contract: Script must accept --dry-run, --apply, --include, --exclude flags
   - Contract: Output must show unified diffs for changes
   - Contract: Script must validate all tests pass after apply

3. **Generate contract tests** from contracts:
   - Test script accepts correct CLI arguments
   - Test script outputs correct diff format in dry-run mode
   - Test script makes no changes in dry-run mode
   - Test script makes expected changes in apply mode

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario with real files
   - Quickstart test = script validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `/scripts/update-agent-context.sh [claude|gemini|copilot]` for your AI assistant
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

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
| [Not a library] | Explicitly specified as one-off cleanup in requirements | Would violate core requirement of being a single scoped pass |
| [No versioning] | Throwaway script with no long-term maintenance | No users to maintain version compatibility for |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*