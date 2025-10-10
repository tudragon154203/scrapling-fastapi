# One-Shot Import Hoisting (Python, app/)

Purpose: run a single, carefully scoped pass to move clearly safe nested imports to the top of modules under `app/`. This is a one-off cleanup, not a reusable library, config, or CI policy.

## Scope

- Codebase: `app/**/*.py`
- Exclude: `**/__init__.py`, migrations, generated code
- Output: a single PR/commit with changes and a brief summary

## Goals

- Improve import hygiene by hoisting obvious nested imports
- Preserve behavior and avoid performance or circular-import risks
- Keep the work auditable: dry-run, small diffs, easy rollback

## Non-Goals

- No new library/module, no config files, no pre-commit/CI integration
- No cross-file deduping or public API refactors
- No complicated special-cases beyond a handful of pragmatic skips

## Practical Safety Rules (minimal)

Only hoist when all are true:
- The node is `import` or `from ... import ...` not already at module top level.
- Not inside `try/except`, `finally`, loops, `with`, or any conditional block.
- Not guarded by runtime values (e.g., feature flags, env reads, function args).
- Not a star import; not marked with `# no-hoist` on the same line.
- Not obviously part of a circular pattern (maintain a short manual exclude list if needed).

Skip entirely (do not transform):
- Imports under `if TYPE_CHECKING:` or any type-checking paths.
- Optional imports (patterns using `try: import ... except ImportError:`)
- Platform-gated imports (e.g., `if sys.platform == "win32":`)

Rationale: for a one-shot pass, skipping borderline cases is safer and faster than building robust generalized handling.

## Implementation Sketch (throwaway script)

- Location: `scripts/hoist_imports_once.py` (single file, stdlib only)
- Parse each file with `ast` to find nested `Import`/`ImportFrom` nodes.
- Apply the safety rules above; collect unique candidates per file.
- Rebuild a minimal top-of-file import block containing the hoisted imports, grouped as:
  - stdlib
  - third-party
  - local/relative
  Alphabetize within groups (best-effort). Do not attempt perfect comment preservation.
- Remove original nested occurrences.
- Provide `--dry-run` to print a unified diff and a short reason for each skipped import; `--apply` to write changes.

CLI idea (example):
- `python scripts/hoist_imports_once.py --dry-run --include "app/**/*.py" --exclude "**/__init__.py" "app/**/migrations/**"`
- `python scripts/hoist_imports_once.py --apply    --include "app/**/*.py" --exclude "**/__init__.py" "app/**/migrations/**"`

## Runbook

1) Branch: `git checkout -b chore/one-shot-import-hoist`
2) Dry run: run the script and capture the summary
3) Review: skim diffs; if anything looks risky, add the file/path to an exclude list and rerun
4) Apply: run with `--apply` on the agreed include/exclude set
5) Validate: run tests and a smoke-test path; if issues arise, revert affected files
6) Commit/PR: include a short summary of changed files and counts

## Acceptance Criteria

- Tests pass and basic flows behave as before
- Diffs focus on import blocks and removals of nested imports
- Rerunning the script produces no further changes on the PR branch

## Rollback

- To undo specific files: `git restore --source=HEAD~1 -- <paths>`
- To abandon entirely: reset the branch and delete the PR

## Notes

- Keep the script as a historical artifact under `scripts/` (optional), but do not productize.
- If later we need broader coverage (e.g., optional/platform imports), we can plan a separate effort.

