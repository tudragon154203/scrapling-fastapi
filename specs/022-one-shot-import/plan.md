# Implementation Plan: One-Shot Import Hoisting

**Branch**: 022-one-shot-import | **Date**: 2025-09-12 | **Spec**: specs/022-one-shot-import/spec.md

## Summary
Implement a single-use Python script that moves clearly safe nested imports to the top of modules under `app/`, with dry-run and apply modes. Keep it throwaway and minimal (stdlib only), avoiding any long-term tooling or project restructuring.

## Deliverable
- Script: `scripts/hoist_imports_once.py`
- Modes: `--dry-run`, `--apply`, `--include`, `--exclude`, `--check`
- Output: unified diffs (dry-run), per-import skip reasons, applied changes

## Plan
1) CLI skeleton
- argparse flags: `--dry-run/--apply` (mutually exclusive), `--include` (globs), `--exclude` (globs), `--check`.
- Default include: `app/**/*.py`. Default exclude: `**/__init__.py`, migrations, generated.

2) File discovery
- Resolve glob patterns with pathlib; de-duplicate; respect excludes.
- For each file: read text, track shebang/encoding/docstring boundaries.

3) Analysis (AST)
- Parse with `ast`. On SyntaxError/encoding errors: record skip and continue.
- Find nested `Import`/`ImportFrom` nodes.
- Apply safety rules: skip if inside try/except/finally/with/loop/conditional, star-import, runtime-guarded, `# no-hoist` present, TYPE_CHECKING, platform/optional patterns.

4) Transformation
- Build a top-of-file import block:
  - Group: stdlib, third-party, local/relative (minimal heuristic per spec).
  - Alphabetize within groups and deduplicate.
  - Preserve original shebang, encoding, module docstring; place imports after them.
- Remove original nested import statements.

5) Output
- Dry-run: generate unified diff per file and list skip reasons.
- Apply: write atomically (temp file + replace). Idempotency self-check by re-running transform on the new content (expect no changes).
- Exit codes: if `--check` and any changes would be made, exit non-zero.

6) Validation & PR
- Run repository tests and a quick smoke test path.
- Prepare a small PR/commit with a brief summary of files changed and counts.

## Notes
- Keep minimal; no libraries, no pre-commit, no CI wiring.
- Prefer skipping borderline cases over expanding logic.

