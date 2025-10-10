# Implementation Plan: Change TikTok Search Headless/Headful Behaviour

**Branch**: `001-change-tiktok-search` | **Date**: Sunday 21 September 2025 | **Spec**: [link](O:\\n8n-compose\\scrapling-fastapi\\main\\specs\\001-change-tiktok-search\\spec.md)
**Input**: Feature specification from `/specs/001-change-tiktok-search/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
This feature modifies the TikTok search functionality to allow users to control whether searches run in headless or headful mode through an optional force_headful parameter. Normal requests will run in headless mode by default, but can be forced to headful mode when force_headful is explicitly set to true. Tests will always run in headless mode, ignoring the force_headful parameter.

## Technical Context
**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, Scrapling  
**Storage**: N/A  
**Testing**: pytest  
**Target Platform**: Linux server  
**Project Type**: web  
**Performance Goals**: NEEDS CLARIFICATION  
**Constraints**: NEEDS CLARIFICATION  
**Scale/Scope**: NEEDS CLARIFICATION

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Based on the constitution, the following principles apply:

1. **Library-First**: The implementation should be structured as a self-contained, independently testable library.
2. **CLI Interface**: Functionality should be exposed via CLI with text in/out protocol.
3. **Test-First (NON-NEGOTIABLE)**: TDD is mandatory with tests written before implementation.
4. **Integration Testing**: Focus areas requiring integration tests include contract changes.
5. **Observability**: Text I/O ensures debuggability with structured logging.

## Project Structure

### Documentation (this feature)
```
specs/001-change-tiktok-search/
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
specify_src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: DEFAULT to Option 1 unless Technical Context indicates web/mobile app

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - Performance Goals: Need to determine expected performance targets
   - Constraints: Need to identify specific constraints for this feature
   - Scale/Scope: Need to understand the expected scale and scope

2. **Generate and dispatch research agents**:
   ```bash
   Task: "Research best practices for implementing headless/headful browser control in Scrapling"
   Task: "Find best practices for parameter validation in FastAPI"
   Task: "Research patterns for test context detection in Python applications"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Search Request entity with force_headful parameter
   - Execution Mode entity representing headless/headful states
   - Test Context entity for identifying test execution

2. **Generate API contracts** from functional requirements:
   - TikTok search endpoint with optional force_headful parameter
   - Output OpenAPI schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - Test for default headless behavior
   - Test for force_headful=true behavior
   - Test for force_headful=false behavior
   - Test for test context override behavior
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each acceptance scenario → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType qwen` for your AI assistant
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, QWEN.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
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
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


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