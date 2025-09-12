# Tasks: One-Shot Import Hoisting

**Input**: specs/022-one-shot-import/spec.md, specs/022-one-shot-import/plan.md

## Minimal Task List
- [ ] T001 Implement `scripts/hoist_imports_once.py` CLI with flags: `--dry-run`, `--apply`, `--include`, `--exclude`, `--check`
- [ ] T002 Add file discovery (include/exclude globs) using pathlib; default to `app/**/*.py`, exclude `**/__init__.py`, migrations, generated
- [ ] T003 Parse with `ast` and detect nested imports; apply safety rules including `# no-hoist`, skip TYPE_CHECKING/optional/platform cases
- [ ] T004 Build top-of-file import block; group (stdlib/third/local) using minimal heuristic; alphabetize; deduplicate
- [ ] T005 Preserve shebang, encoding, and module docstring placement; remove original nested imports
- [ ] T006 Implement dry-run unified diffs and per-import skip reasons; `--check` exit non-zero if changes would be made
- [ ] T007 Apply mode with atomic writes; idempotency self-check (second transform yields no changes)
- [ ] T008 Run repo tests and smoke flows; prepare PR with summary of changed files and counts

## Notes
- Keep it to a single script; stdlib only
- Prefer skipping borderline cases over expanding logic

