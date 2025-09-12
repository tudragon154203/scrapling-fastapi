# Feature Specification: One-Shot Import Hoisting

**Feature Branch**: 022-one-shot-import  
**Created**: 2025-09-12  
**Status**: Draft

## Summary
Run a single, carefully scoped pass to move clearly safe nested imports to the top of modules under `app/`. This is a one-off cleanup, not a reusable library, config, or CI policy.

## Scope

- Codebase: `app/**/*.py`
- Exclude: `**/__init__.py`, migrations, generated code
- Output: a single PR/commit with changes and a brief summary

## Goals

- Improve import hygiene by hoisting obvious nested imports
- Preserve behavior and avoid circular-import risks
- Keep the work auditable: dry-run, small diffs, easy rollback

## Non-Goals

- No new library/module, no config files, no pre-commit/CI integration
- No cross-file deduping or public API refactors
- No complex special-cases beyond pragmatic skips

## Practical Safety Rules (minimal)

Only hoist when all are true:
- Node is `import` or `from ... import ...` not already at module top level.
- Not inside `try/except`, `finally`, loops, `with`, or any conditional block.
- Not guarded by runtime values (e.g., feature flags, env reads, function args).
- Not a star import; respect inline pragma `# no-hoist` to skip.
- Not obviously part of a circular pattern (keep a short manual exclude list if needed).

Skip entirely (do not transform):
- Imports under `if TYPE_CHECKING:` or any type-checking paths.
- Optional imports (patterns using `try: import ... except ImportError:`)
- Platform-gated imports (e.g., `if sys.platform == "win32":`)

Rationale: for a one-shot pass, skipping borderline cases is safer and faster than implementing generalized handling.

## User Scenarios & Acceptance

1. Given a file with safe nested imports, when the tool runs, then those imports move to the top grouped by stdlib, third-party, local, and duplicates are removed.
2. Given dry-run mode, when the tool analyzes the codebase, then it shows unified diffs and per-import skip reasons without modifying files.
3. Given imports in try/except or conditional blocks, when processed, then they are skipped with a reason.
4. Given the tool is run twice, when the second run completes, then it reports no changes (idempotent).
5. Given changes are applied, when project tests run, then they still pass and basic flows work.

## Requirements

### Functional
- FR-001: Identify Python files in `app/` (excluding `__init__.py`, migrations, generated files).
- FR-002: Detect nested `Import`/`ImportFrom` statements not at module top.
- FR-003: Apply safety rules; skip guarded or risky imports.
- FR-004: Respect `# no-hoist` pragma on the same line as an import.
- FR-005: Group hoisted imports by category: stdlib, third-party, local/relative.
- FR-006: Alphabetize within groups and deduplicate identical imports.
- FR-007: Preserve module shebang, encoding declaration, and top-level docstring order.
- FR-008: Provide dry-run output as unified diffs and list per-import skip reasons.
- FR-009: Apply changes on request using atomic writes; leave non-import code unchanged.
- FR-010: Handle files with no nested imports gracefully (no-ops).
- FR-011: Idempotency: rerunning produces no further changes.
- FR-012: Exit codes: in `--check` mode (or `--dry-run --check`), exit non-zero when changes would be made; zero otherwise.
- FR-013: On parse/encoding errors, skip the file with a clear message, do not crash.

### Non-Functional
- Deterministic output (stable formatting and grouping).
- Minimal, throwaway implementation (single script, stdlib only).

### Minimal Grouping Heuristic
- Relative imports (starting with `.`) are local.
- A small, hardcoded stdlib set is recognized as stdlib; everything else is third-party.
- Maintain exactly one blank line between groups; integrate with any existing top-level imports if present.

