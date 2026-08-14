# Phase 149: Test Suite Triage - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 4 core mechanism files + ~52 test files (grouped by cluster, not enumerated individually — see rationale below) + 1 new doc
**Analogs found:** 4 / 4 core files (all are literally the same file being extended, not a new analog search) + 1 strong ledger-format analog

## Scope note on "files to be created/modified"

Per RESEARCH.md, this phase is disposition-only: it extends two existing files
(`tests/skip_registry.py`, `tests/test_skip_registry.py`), extends `pyproject.toml`'s
`markers` list, adds one new doc (`docs/test-triage-149.md`), and adds
`@pytest.mark.skip`/`@pytest.mark.xfail` decorators to individual test functions across
~52 files. Because the ~52 test files' modifications are all the *same* one-line decorator
insertion pattern (not 52 distinct architectural patterns), this map gives one canonical
excerpt for "how to add a quarantine marker to any test file" rather than 52 near-identical
rows.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tests/skip_registry.py` | config/registry (data table) | CRUD (append rows) | itself (extend `ALLOWED_SKIPS` list, same file) | exact — self-extension |
| `tests/test_skip_registry.py` | test / meta-gate (AST walker) | transform (static analysis) | itself (extend `_is_pytest_skip_call`-style detector functions) | exact — self-extension |
| `pyproject.toml` (`markers` key) | config | CRUD (append list entries) | itself, existing `markers` list (lines 152-155) | exact — self-extension |
| `docs/test-triage-149.md` (new) | doc / ledger | batch (per-test disposition table) | `.planning/audit-2026-05-27/AUDIT-TASKS.md` (ID-keyed status ledger) AND `docs/timeout-retry-audit.md` (docs/-tree markdown audit-table format) | role-match (two analogs, combine both) |
| ~52 test files (e.g. `tests/test_auto_merge_trigger.py`, `tests/test_notify_webhook.py`, `tests/test_jwt_scanner.py`, etc.) | test | request-response / event-driven (per underlying feature) — modification is uniform: add one decorator line | `tests/test_jobs_api.py` lines 44-84 (existing `@pytest.mark.skip`... actually those use `pytest.skip()` calls, see below) — decorator-insertion pattern itself is new to the codebase (RESEARCH.md confirms zero prior `@pytest.mark.skip`/`xfail` usage) | partial — no true decorator analog exists; closest structural analog is the existing `pytest.skip(reason=...)` call-site pattern already registered in `ALLOWED_SKIPS` |

## Pattern Assignments

### `tests/skip_registry.py` (config/registry, CRUD-append)

**Analog:** itself — read in full (45 lines), reproduced here as the exact shape to replicate.

**Full current structure** (`tests/skip_registry.py:1-45`):
```python
"""Phase 41 D-02: Central allowed-skip registry.

Each entry: (file_relative_to_tests_dir, line_number, category, reason)
category in {"optional_extra", "live_infra"}
...
"""

ALLOWED_SKIPS = [
    ("test_broker_scanner_kafka.py",    12,  "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_chaos_storage.py",           41,  "live_infra",     "Requires Docker + MinIO"),
    # Phase 65 Plan 01 stubs — replaced by real implementations in Plans 03/04
    ("test_jobs_api.py",  44, "live_infra", "Phase 65 Plan 03 stub — POST /api/jobs row insert"),
    ...
]
```

**Pattern to copy for the 149 entries:**
1. Update the module docstring's `category in {...}` line to add `"pre_existing_triage_149"`.
2. Append new tuples in the exact 4-field shape `(file, line, category, reason)`, using the
   existing comment-header convention (`# Phase 65 Plan 01 stubs — ...`) to group the 149
   entries under a `# Phase 149 D-02/D-03: test-suite triage quarantines — see docs/test-triage-149.md`
   banner comment, mirroring how the Phase 65 block is set off from the rest.
3. Reason string convention locked by CONTEXT.md D-03/RESEARCH.md's Code Examples section:
   `"TRIAGE-149: <sub-reason>; see docs/test-triage-149.md#<anchor>"`. Example from RESEARCH.md:
   ```python
   ("test_notify_webhook.py", 45, "pre_existing_triage_149",
    "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test-notify-webhookpy-test-no-hmac-when-key-env-not-set"),
   ```
4. Do NOT create a second list or parallel file — one flat `ALLOWED_SKIPS` list, per D-02 and
   the "Don't Hand-Roll" table in RESEARCH.md.

---

### `tests/test_skip_registry.py` (meta-gate, AST walker)

**Analog:** itself — read in full (117 lines).

**Current detector shape** (`tests/test_skip_registry.py:46-68`):
```python
def _is_pytest_skip_call(node: ast.AST) -> bool:
    """True if ``node`` is a Call to ``pytest.skip`` or ``pytest.importorskip``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == "pytest" and func.attr in {"skip", "importorskip"}:
            return True
    return False


def _is_pytest_skipif_decorator(node: ast.AST) -> bool:
    """True if ``node`` is ``@pytest.mark.skipif(...)`` decorator."""
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute) and target.attr == "skipif":
        inner = target.value
        if isinstance(inner, ast.Attribute) and inner.attr == "mark":
            base = inner.value
            if isinstance(base, ast.Name) and base.id == "pytest":
                return True
    return False
```

**Pattern to copy — extending detection to `@pytest.mark.skip` and `@pytest.mark.xfail`**
(per RESEARCH.md's recommended Option 1, D-03 implication section): generalize
`_is_pytest_skipif_decorator` into a parametrized check, e.g.:
```python
def _is_pytest_mark_decorator(node: ast.AST, mark_name: str) -> bool:
    """True if ``node`` is ``@pytest.mark.<mark_name>(...)`` (call or bare attribute)."""
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute) and target.attr == mark_name:
        inner = target.value
        if isinstance(inner, ast.Attribute) and inner.attr == "mark":
            base = inner.value
            if isinstance(base, ast.Name) and base.id == "pytest":
                return True
    return False
```
Then in the main loop (`tests/test_skip_registry.py:97-106`), iterate over
`{"skipif", "skip", "xfail"}` instead of hardcoding `_is_pytest_skipif_decorator`, appending
`(py_file.name, deco.lineno, f"@pytest.mark.{mark_name}")` to `violations` on miss — same
shape already used for the `skipif` violation tuple at line 104-106.

**Non-recursive glob gap (Assumption A3 in RESEARCH.md):** current walk is
`TESTS_DIR.glob("*.py")` (line 80) — does not descend into `tests/scanner/`. Planner/executor
must explicitly decide whether to change this to `TESTS_DIR.rglob("*.py")` (with matching
`EXEMPT_FILES`/registry-key adjustments for subdirectory files, since `_allowed()` matches on
bare `py_file.name` only) or document the exemption as intentional. This is call-out territory,
not a locked pattern — flag to the plan.

**Test declaration pattern** (`tests/test_skip_registry.py:71-72`):
```python
@pytest.mark.skip_registry_gate
def test_no_unregistered_skips() -> None:
```
Note the `skip_registry_gate` marker itself is undeclared in `pyproject.toml`'s `markers` list
(RESEARCH.md's "Minor unrelated finding") — fix in the same `markers` edit as the new
`slow`/`live_infra` entries.

---

### `pyproject.toml` (markers list)

**Analog:** itself, lines 152-157.

**Current shape:**
```toml
markers = [
    "slow: marks tests as slow (deselect with '-m not slow')",
    "live_infra: marks tests requiring live external infrastructure (Docker/cloud/etc)",
]
addopts = "-m 'not slow'"
testpaths = ["tests"]
```

**Pattern to copy:** append one string per new marker actually needed, following the
`"<name>: <one-line description>"` convention exactly. At minimum add
`"skip_registry_gate: marks the skip-registry meta-gate test"` (closes the existing
`PytestUnknownMarkWarning`). If D-03's xfail usage needs its own custom marker name (unlikely —
`@pytest.mark.xfail` is a pytest builtin, no declaration needed), do not add one; only
`skip_registry_gate` is a genuinely custom marker requiring declaration.

---

### `docs/test-triage-149.md` (new ledger doc)

**Analog 1 — status-ledger table shape:** `.planning/audit-2026-05-27/AUDIT-TASKS.md`

**Frontmatter + status-legend pattern** (`AUDIT-TASKS.md:1-19`):
```markdown
---
audit: comprehensive-codebase-2026-05-27
ledger_for: 86 findings across 7 subsystems
status_legend:
  - "[ ] open       — finding present in code, no decision yet"
  - "[x] closed     — fix shipped, verified by phase verification"
  - "[ ] deferred   — explicit decision to push later"
  - "[ ] wont-fix   — explicit decision not to address (with reason)"
---

# Audit Task Ledger — 2026-05-27

Flip rows to `[x] closed` as findings are remediated. ...

> Source for each finding: the `REVIEW.md` in the corresponding subsystem directory.
```

**Grouped-by-cluster table pattern** (`AUDIT-TASKS.md:20-46`):
```markdown
## Critical (go-public blocker list — 7 rows)

| ID | Subsystem | Title | File | Status |
|---|---|---|---|---|
| SP-01 | scanners-protocol | ... | quirk/util/url_allowlist.py | [x] closed (Phase 120/123; ...) |

## Warnings (43)

### scanners-protocol (SP) — 9
| ID | Title | File | Status |
|---|---|---|---|
| SP-02 | ... | quirk/scanner/rest_fuzzer.py | [x] closed (Phase 123 SSRF-01; ...) |
```
This is the direct structural template for `docs/test-triage-149.md`: `##` headings per
failure-cluster (RESEARCH.md's clusters 1-9), a table per cluster with
`Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry?` columns (per
RESEARCH.md's "Recommended Ledger Format" section), and a status legend explaining the
disposition vocabulary (`fixed` / `quarantined-skip` / `quarantined-xfail` / `deleted`) up
front in frontmatter or an intro paragraph, exactly like `AUDIT-TASKS.md`'s
`status_legend` block.

**Analog 2 — narrative audit-doc closing convention:** `docs/timeout-retry-audit.md`

**Header + closing-footer pattern** (`docs/timeout-retry-audit.md:1-9, 63-67`):
```markdown
# Phase 41 Timeout & Retry Audit (ROBUST-04)

This document is the canonical audit trail for QU.I.R.K.'s per-scanner timeout and retry
policy as of v4.5 (Phase 41 — CI Stability & Scanner Robustness). ...

---

*Phase: 41-ci-stability-scanner-robustness*
*Plan: 06*
*Updated: 2026-04-29*
```
Use this exact closing-footer convention (`*Phase:* / *Plan:* / *Updated:*`) at the bottom of
`docs/test-triage-149.md`, and open with a one-paragraph statement of purpose plus the
**exact-count reconciliation line** RESEARCH.md calls for:
`"Built against: pytest -q -m "" → 116 failed, 3107 passed, 17 skipped — 2026-08-11"` so
Success Criterion 2 is mechanically checkable, not eyeballed.

---

### ~52 individual test files (decorator insertion)

**No true analog exists in the codebase** — RESEARCH.md confirms zero prior
`@pytest.mark.skip`/`@pytest.mark.xfail` usage anywhere in `tests/`. The closest existing
precedent is the *call-site* pattern (`pytest.skip(reason=...)` inside a test body, or
`@pytest.mark.skipif(condition, reason=...)` above a test), both already registered in
`ALLOWED_SKIPS`. Use standard pytest decorator syntax directly above the `def test_...` line:

```python
@pytest.mark.skip(reason="TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); "
                          "see docs/test-triage-149.md#test-notify-webhookpy-test-no-hmac-when-key-env-not-set")
def test_no_hmac_when_key_env_not_set():
    ...
```
or, where the test still documents useful intent and should keep running:
```python
@pytest.mark.xfail(reason="TRIAGE-149: outdated-fixture (AUDIT-08 UUID guard); "
                           "see docs/test-triage-149.md#test-auto-merge-triggerpy-test-auto-merge-disabled",
                    strict=False)
def test_auto_merge_disabled():
    ...
```
Every insertion must have a matching `ALLOWED_SKIPS` entry added in the same commit (per D-02
enforcement and the extended AST walker above), and the reason string must cite the ledger
anchor exactly as it appears in `docs/test-triage-149.md`.

## Shared Patterns

### Registry-entry-per-marker enforcement
**Source:** `tests/skip_registry.py` + `tests/test_skip_registry.py`
**Apply to:** every one of the ~52 test files receiving a quarantine marker, and to the
`tests/test_skip_registry.py` extension plan itself (must land first, per RESEARCH.md's
recommended plan order, since it repairs D-04 drift before the 149 entries pile on top).

### Ledger anchor / reason-string convention
**Source:** RESEARCH.md's Code Examples + Recommended Ledger Format sections
**Apply to:** all `ALLOWED_SKIPS` new entries and all decorator `reason=` strings — must be
`"TRIAGE-149: <sub-reason>; see docs/test-triage-149.md#<slugified-test-id>"`, consistent across
every one of the ~52+ insertions so the ledger and the registry stay cross-referenceable.

### Cluster-level batching (not per-test reinvestigation)
**Source:** RESEARCH.md's Failure Clusters table + Pitfall 2
**Apply to:** planning/execution of clusters 1, 2, 3, 6, 7 (64 of 116 failures) — write one
shared disposition rationale per cluster, then one ledger row + one marker per test citing that
shared rationale, rather than re-deriving the explanation per test.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| Decorator insertion into ~52 test files | test | varies by underlying feature | No prior `@pytest.mark.skip`/`xfail` usage exists anywhere in `tests/` to copy from (RESEARCH.md, confirmed via grep) — use standard pytest decorator syntax directly, no project-specific wrapper exists |

## Metadata

**Analog search scope:** `tests/skip_registry.py`, `tests/test_skip_registry.py`, `pyproject.toml`,
`docs/timeout-retry-audit.md`, `.planning/audit-2026-05-27/AUDIT-TASKS.md`
**Files scanned:** 5 read in full + grep confirmation of zero existing `@pytest.mark.skip`/`xfail`
usage (already performed in RESEARCH.md, not re-run here)
**Pattern extraction date:** 2026-08-11
