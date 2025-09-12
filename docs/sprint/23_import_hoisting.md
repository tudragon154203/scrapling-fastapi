# PRD — Safe Import Hoisting for Python (app/)

## 1) Overview

Create a safe, automated codemod that scans Python files under `app/` for `import` statements nested inside functions, methods, classes, or blocks, and **moves safe candidates to the top of the file** without changing runtime behavior.

## 2) Goals

* Reduce import duplication and improve import hygiene.
* Preserve behavior, side-effects, performance characteristics, and error semantics.
* Provide dry-run reporting and a reversible transformation.
* Enforce via CI and an optional pre-commit hook.

## 3) Non-Goals

* Refactoring cross-package public APIs.
* Deduplicating imports across different modules.
* Rewriting heavy runtime dependency patterns (e.g., plugin loaders).
* Fixing unrelated lint/style issues.

## 4) Key Requirements

### Functional

1. **Scope** : Process all `*.py` files under `app/`.
2. **Detection** : Find `import` and `from … import …` nodes that are **not** at module top level.
3. **Safety Filter** (only hoist when ALL are true):
   * No dependency on **runtime values** in the surrounding scope (e.g., inside `if debug:`).
   * Not inside dynamic control flow that intentionally guards availability (e.g., `try/except ImportError`, platform checks).
   * Will not introduce **circular import** at module import time (basic static detection + allowlist/denylist escape hatches).
   * Import does **not** rely on being executed lazily for performance (honor inline `# no-hoist` pragma and configurable patterns).
   * Names/aliases remain correct (handle `as alias` and star-imports conservatively).
4. **Special Cases Handling** :

* `if TYPE_CHECKING:` imports → keep under a **top-of-file** `if TYPE_CHECKING:` guard (do not import at runtime).
* `try/except ImportError` optional imports → hoist into an equivalent **top-level try/except** block preserving the same exception handling and fallbacks.
* Platform/feature gated imports (e.g., `if sys.platform == "win32":`) → hoist under the same condition  **at top level** .
* Late-binding for circulars (common pattern) →  **skip by default** , require explicit allowlist to hoist.
* Star imports (`from x import *`) → **never hoist** (skip) unless the original is already at top level; nested star imports are left unchanged.
* Relative imports and `__all__` interactions → preserve export lists; do not modify `__all__` automatically.

1. **Transformation** :

* Insert hoisted imports in a canonical block at the file top:
  * 1. stdlib
  * 2. third-party
  * 3. local (relative)

       Group and alphabetize within groups (configurable), keep comments attached.
* Preserve original comments and inline pragmas (attach to moved import).
* Remove the original nested import.

1. **Idempotency** : Re-running produces no further changes.
2. **Reporting** :

* CLI `--dry-run` prints a per-file diff summary and safety reasons for skipped imports.
* Exit non-zero on changes (for CI) when `--check` is used.

1. **Config** :

* `hoist.toml` (repo root) with:
  * `include = ["app/**/*.py"]`, `exclude = ["**/__init__.py", "app/**/migrations/**"]`
  * `denylist_modules = []`, `allowlist_modules = []`
  * `assume_third_party = ["numpy", "pandas", ...]` (for grouping)
  * `respect_no_hoist_comment = true`
  * `max_cyclerisk_depth = 2` (see below)

1. **Performance** :

* Optional `--perf-sensitive` mode: skip imports inside functions named like `handler`, `lambda_`, `endpoint`, or decorated by common web/task runners (`@app.get`, `@celery.task`, etc.).

1. **APIs/UX** :

* CLI: `python -m import_hoister --apply|--dry-run [--check] [--perf-sensitive]`
* Pre-commit hook integration example in docs.

### Non-Functional

* Works with Python 3.9+ syntax (match project target).
* Fast: ≤ 1s per 500 LOC file on average.
* Deterministic output (stable formatting).
* No network access; static analysis only.

## 5) Safety Rules (Detail)

1. **Runtime-Value Guard**

   If an import is inside a conditional depending on non-constant/global values (e.g., env vars read at runtime, function args),  **skip** .
2. **Optional Dependency Semantics**

   Pattern:

   <pre class="overflow-visible!" data-start="4158" data-end="4237"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>try</span><span>:
       </span><span>import</span><span> pkg
   </span><span>except</span><span> ImportError:
       pkg = </span><span>None</span><span>
   </span></span></code></div></div></pre>

   → Hoist as the same `try/except` at top; ensure the same name binding.
3. **Type-Checking**

   <pre class="overflow-visible!" data-start="4339" data-end="4431"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>from</span><span> typing </span><span>import</span><span> TYPE_CHECKING
   </span><span>if</span><span> TYPE_CHECKING:
       </span><span>from</span><span> x </span><span>import</span><span> Y
   </span></span></code></div></div></pre>

   → Ensure `from typing import TYPE_CHECKING` exists; add if missing; hoist under the guard.
4. **Platform/Feature Gates**

   Conditions composed of literals on `sys.platform`, `os.name`, `typing.TYPE_CHECKING`, or `HAS_*` constants defined at module top are allowed to hoist  **with the same guard** .
5. **Circular Import Risk**

   * Build a lightweight import graph (module names only) from `app/`.
   * If hoisting would cause the module to import a sibling that (transitively) imports this module at import time, **skip** unless target is in `allowlist_modules`.
6. **Name & Alias Integrity**

   * Preserve `as alias`.
   * If the nested import shadows an outer name and hoisting changes resolution, **skip** (report “shadowing risk”).
7. **Side-Effect Modules**

   * If the imported module name is in `denylist_modules` or matches patterns like `.*(settings|setup|monkeypatch).*`, skip by default.
8. **Star Imports**

   * Never hoist nested `from x import *`. Skip (too risky for symbol tables).
9. **Inline Opt-Out**

   * Respect `# no-hoist` on the same line or preceding comment block.

## 6) User Stories

* As a developer, I want imports hoisted so files are cleaner and import errors happen early.
* As a reviewer, I want a diff that shows only safe import moves with reasons for skipped ones.
* As a maintainer, I want CI to fail when there are unapplied safe moves.

## 7) Workflow

1. **Discovery**
   * Walk `app/**/*.py` (respect config include/exclude).
   * Parse AST; locate non-module-level `Import`/`ImportFrom`.
2. **Classify & Decide**
   * Tag each with: context (function/class/try/if), guards, aliasing, comments.
   * Evaluate safety rules.
3. **Transform**
   * For safe nodes, construct equivalent top-level statements:
     * Plain import → top import block.
     * Guarded import → replicate guard/try-except at top.
   * Remove original node; deduplicate identical imports.
4. **Format**
   * Sort/group imports (stdlib/third-party/local).
   * Preserve trailing/leading comments with the moved node.
5. **Emit**
   * `--dry-run`: show unified diff per file + reasons for each skipped item.
   * `--apply`: write files; generate a summary report.

## 8) Acceptance Criteria

* ✅ All imports at module level after run, except:
  * Explicit skips per rules above.
  * `TYPE_CHECKING` imports remain guarded.
* ✅ Running tests before vs. after shows  **no failures added** .
* ✅ Idempotent re-run yields zero diffs.
* ✅ CI `--check` fails if any hoistable imports are found.
* ✅ Reports enumerate: file, original location (line), action (hoisted/skipped), and reason.

## 9) Telemetry & Metrics

* Count of imports hoisted vs. skipped (by reason).
* Per-file transformation time.
* Optional: collect perf sentinel timings (import time before/after) in a sampled CI job.

## 10) Rollout Plan

1. **Phase 0** : Dry-run in CI to collect data (no code changes).
2. **Phase 1** : Apply to low-risk directories (e.g., pure utils).
3. **Phase 2** : Full `app/` with `--perf-sensitive`.
4. **Phase 3** : Enable pre-commit hook; keep CI `--check`.

## 11) Risks & Mitigations

* **Circular import introduced** → import graph check + default skip + allowlist.
* **Perf regressions** from eager imports → `--perf-sensitive`, inline opt-out, skip common hotpaths.
* **Behavioral change in optional deps** → keep `try/except` structure verbatim.
* **Comment/doc loss** → attach and move comments with nodes; add tests for preservation.

## 12) Test Plan

### Unit

* Parse/transform for:
  * Plain nested import in function.
  * Guarded by `if TYPE_CHECKING`.
  * Guarded by platform condition.
  * `try/except ImportError` with fallback binding.
  * Aliased imports, multiple names in one line.
  * Star imports (ensure skipped).
  * Shadowing scenarios (ensure skipped).

### Integration

* Snapshot diffs on curated fixture files.
* Run repository test suite before/after codemod on a sample to ensure parity.

### Property-Based

* Random nesting of imports → transformation never changes AST semantics of unaffected code; reparse to ensure valid syntax.

## 13) Deliverables

* `import_hoister/` package:
  * `cli.py` (entry point)
  * `core.py` (AST analysis + transform)
  * `graph.py` (import graph builder)
  * `formatting.py` (grouping/sorting, comment handling)
  * `config.py` (TOML loader with defaults)
* `hoist.toml` example config.
* Pre-commit hook snippet.
* Documentation with examples and troubleshooting.

## 14) Example Transformations

**A) Simple function import**

<pre class="overflow-visible!" data-start="8962" data-end="9026"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>def</span><span></span><span>foo</span><span>():
    </span><span>import</span><span> json
    </span><span>return</span><span> json.loads(</span><span>"[]"</span><span>)
</span></span></code></div></div></pre>

→

<pre class="overflow-visible!" data-start="9029" data-end="9090"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>import</span><span> json

</span><span>def</span><span></span><span>foo</span><span>():
    </span><span>return</span><span> json.loads(</span><span>"[]"</span><span>)
</span></span></code></div></div></pre>

**B) Optional dependency**

<pre class="overflow-visible!" data-start="9119" data-end="9250"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>def</span><span></span><span>load</span><span>():
    </span><span>try</span><span>:
        </span><span>import</span><span> ujson </span><span>as</span><span> json
    </span><span>except</span><span> ImportError:
        </span><span>import</span><span> json
    </span><span>return</span><span> json.loads(</span><span>"[]"</span><span>)
</span></span></code></div></div></pre>

→

<pre class="overflow-visible!" data-start="9253" data-end="9369"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>try</span><span>:
    </span><span>import</span><span> ujson </span><span>as</span><span> json
</span><span>except</span><span> ImportError:
    </span><span>import</span><span> json

</span><span>def</span><span></span><span>load</span><span>():
    </span><span>return</span><span> json.loads(</span><span>"[]"</span><span>)
</span></span></code></div></div></pre>

**C) TYPE_CHECKING**

<pre class="overflow-visible!" data-start="9392" data-end="9468"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>def</span><span></span><span>f</span><span>(</span><span>x: "T"</span><span>): ...
</span><span>if</span><span> condition:
    </span><span>from</span><span> pkg </span><span>import</span><span> T  </span><span># no-hoist</span><span>
</span></span></code></div></div></pre>

→

<pre class="overflow-visible!" data-start="9471" data-end="9621"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>from</span><span> typing </span><span>import</span><span> TYPE_CHECKING
</span><span>if</span><span> TYPE_CHECKING:
    </span><span>from</span><span> pkg </span><span>import</span><span> T

</span><span>def</span><span></span><span>f</span><span>(</span><span>x: "T"</span><span>): ...
</span><span>if</span><span> condition:
    </span><span>from</span><span> pkg </span><span>import</span><span> T  </span><span># no-hoist</span><span>
</span></span></code></div></div></pre>

**D) Platform guard**

<pre class="overflow-visible!" data-start="9645" data-end="9752"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>def</span><span></span><span>win_only</span><span>():
    </span><span>if</span><span> sys.platform == </span><span>"win32"</span><span>:
        </span><span>from</span><span> .win </span><span>import</span><span> api
        </span><span>return</span><span> api()
</span></span></code></div></div></pre>

→

<pre class="overflow-visible!" data-start="9755" data-end="9898"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-py"><span><span>import</span><span> sys
</span><span>if</span><span> sys.platform == </span><span>"win32"</span><span>:
    </span><span>from</span><span> .win </span><span>import</span><span> api

</span><span>def</span><span></span><span>win_only</span><span>():
    </span><span>if</span><span> sys.platform == </span><span>"win32"</span><span>:
        </span><span>return</span><span> api()
</span></span></code></div></div></pre>

## 15) Heuristics for Standard Library vs Third-Party vs Local

* Use `importlib.util.find_spec` when available during development to seed `assume_third_party`.
* Fallback: regex on relative (`.`/`..`) → local; top-level names against a curated stdlib list for the project’s Python version.

## 16) CLI Examples

<pre class="overflow-visible!" data-start="10211" data-end="10429"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span># Dry-run with reasons
python -m import_hoister </span><span>--dry-run</span><span></span><span>--check</span><span>

# Apply changes
python -m import_hoister </span><span>--apply</span><span>

# Perf-sensitive, keep risky imports nested
python -m import_hoister </span><span>--apply</span><span></span><span>--perf-sensitive</span><span>
</span></span></code></div></div></pre>

## 17) Open Assumptions (will proceed with these defaults)

* Target Python **3.10** unless configured otherwise.
* Exclude `**/__init__.py`, migrations, and generated files by default.
* CI runs project tests after codemod to catch regressions.
