# Phase 151: Phase-Completion Artifact Gates - Pattern Map

**Mapped:** 2026-08-13
**Files analyzed:** 5 (2 new source files, 1 new hook wrapper, 1 test file, 1 doc update)
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `scripts/verify_phase_gates.py` | utility (guard/gate script) | file-I/O + event-driven (git-hook trigger) | `scripts/release_tag_hygiene.py` | exact (same role, same repo convention; different trigger — hook vs. scheduled CI — but identical pure-function/CLI-glue split) |
| `.githooks/pre-commit` | config (hook entrypoint, shell wrapper) | event-driven | `.github/workflows/release-tag-hygiene.yml` (invocation wrapper role) | role-match (both are "thin trigger wrapper that shells out to the Python script and propagates its exit code"; different trigger mechanism — git hook vs. GH Actions workflow) |
| `tests/test_verify_phase_gates.py` | test | CRUD (pure-function unit tests) + config-static-guard | `tests/test_release_tag_hygiene.py` | exact |
| `tests/test_verify_phase_gates.py` (static/meta-gate portions, if any AST-style convention checks are added) | test | transform (structural walk) | `tests/skip_registry.py` + its test `tests/test_skip_registry.py` | role-match (design reference only — "meta-gate over a convention" concept, not a literal shape to copy) |
| `CONTRIBUTING.md` (hook install section) | config/docs | request-response (developer-facing instructions) | `CONTRIBUTING.md` itself (existing "Running the test suite" / "Why some tests are quarantined" sections) | exact (same file, same voice/structure to extend) |

## Pattern Assignments

### `scripts/verify_phase_gates.py` (utility, file-I/O + event-driven)

**Analog:** `scripts/release_tag_hygiene.py` (237 lines, read in full)

**Module docstring + imports pattern** (lines 1-27):
```python
#!/usr/bin/env python3
"""Scheduled guard: catch a release-like tag that never produced a successful
`release.yml` run (RELEASE-03).

Why this exists: ...

Run modes:
    python scripts/release_tag_hygiene.py

Lives under scripts/ -- NOT imported by any runtime code.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / ".github" / "tag-hygiene-baseline.txt"
```
Copy this shape directly: module docstring explaining *why* (cite the three v5.11 incidents +
the ARCHIVE-MANIFEST.md incident), `from __future__ import annotations`, `REPO_ROOT` computed via
`pathlib.Path(__file__).resolve().parent.parent`, module-level path constants for
`.planning/phases`, `.planning/milestones`, `.planning/STATE.md`, `.planning/ROADMAP.md`,
`docs/UAT-SERIES.md`.

**Pure decision-function pattern** (lines 94-148, `evaluate_tags`):
```python
def evaluate_tags(
    tags: list[str],
    released_tags: set[str],
    baseline: dict[str, str],
) -> tuple[list[str], list[str], str]:
    """... Pure: no subprocess, no network, no env reads."""
    release_like = [t for t in tags if LOOSE_RELEASE_TAG_RE.match(t)]
    ok: list[str] = []
    exempted: list[str] = []
    flagged: list[str] = []
    for tag in release_like:
        if tag in released_tags:
            ok.append(tag)
        elif tag in baseline:
            exempted.append(tag)
        else:
            flagged.append(tag)
    lines = ["## Release Tag Hygiene", ""]
    ...
    summary_markdown = "\n".join(lines)
    return flagged, exempted, summary_markdown
```
Apply this exact shape to `check_phase_close()` and `check_destructive_archive()`: each takes
plain Python data (parsed strings, sets, dicts — never a live subprocess call or disk read inside
the function body) and returns a plain tuple `(blocked: bool, reasons: list[str], summary: str)`
or similar. This is what makes both functions directly unit-testable with `tests/skip_registry.py`
-style literal fixtures, with zero mocking.

**File-loading/parsing helper pattern** (lines 36-53, `load_baseline`):
```python
def load_baseline(path: pathlib.Path) -> dict[str, str]:
    """Parse `.github/tag-hygiene-baseline.txt`. ..."""
    baseline: dict[str, str] = {}
    if not path.exists():
        return baseline
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        ...
    return baseline
```
Use this same "missing file → empty result, never raise" defensive shape for reading
`<N>-VERIFICATION.md`, `<N>-VALIDATION.md`, and `docs/UAT-SERIES.md` — a missing file is itself
often the failure condition being tested for (ARTIFACT-01), so the loader must distinguish
"file absent" (a legitimate blocking condition) from "file present but unparseable" (a hard
error), matching `_run_gh_json`'s hard-error-on-bad-data philosophy below.

**Subprocess invocation pattern** (lines 151-170, `_run_gh_json`, applies to any `git diff --cached`
calls the hook needs):
```python
def _run_gh_json(args: list[str]) -> list[dict]:
    """... Hard error on non-zero exit or unparseable JSON — never treated as
    "everything is backed" (T-148-09)."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command {args!r} exited {result.returncode}: {result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(...) from exc
```
Copy this list-form-argv + `check=False` + explicit-raise pattern for the `git diff --cached
--name-only` call the phase-close-detection trigger needs (D-03). Never use `shell=True` with
interpolated strings (security note in RESEARCH.md's V5 row).

**`main()` / exit-code convention** (lines 173-234):
```python
def main(argv: list[str] | None = None) -> int:
    import os
    try:
        ...
    except RuntimeError as exc:
        sys.stderr.write(f"release_tag_hygiene: hard error: {exc}\n")
        return 2
    ...
    if flagged:
        sys.stderr.write(f"release_tag_hygiene: {len(flagged)} flagged tag(s): {flagged}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
Adopt the same three-tier exit-code convention: `0` = clean/proceed, `1` = a real gate violation
(block the commit), `2` = a hard/unexpected error (e.g., unparseable `STATE.md`) — both `1` and
`2` must cause the wrapping `.githooks/pre-commit` shell script to abort the commit; only the
codes' *meaning* to a human differs. Error text goes to `sys.stderr`, never stdout (stdout is
reserved for a human-readable summary, matching `GITHUB_STEP_SUMMARY` vs. `print()` fallback
above — this script's analogous fallback is printing to the terminal since there's no CI summary
file in a git-hook context).

---

### `.githooks/pre-commit` (config, event-driven)

**No direct analog file exists in this repo** (no `.githooks/` directory, no prior git-hook
infrastructure — confirmed absent during discussion, RESEARCH.md "Reusable Assets"). The closest
structural analog for "thin trigger wrapper that shells out to the Python script and respects its
exit code" is `.github/workflows/release-tag-hygiene.yml`'s invocation step, but that file is YAML
CI config, not shell. Compose the hook from first principles as a small POSIX shell script:

```sh
#!/bin/sh
# .githooks/pre-commit
# Installed via: git config core.hooksPath .githooks
# Bypass (documented, not prevented): git commit --no-verify
set -eu
python3 "$(git rev-parse --show-toplevel)/scripts/verify_phase_gates.py" --pre-commit
exit $?
```
Reference `scripts/release_tag_hygiene.py`'s `if __name__ == "__main__": sys.exit(main())` pattern
for the Python-side exit code the shell wrapper propagates. Keep all real logic in the Python
script (testable); the shell file should be near-zero-logic, matching the "workflow YAML has
almost no logic, the script has all of it" split already used for `release-tag-hygiene.yml`.

---

### `tests/test_verify_phase_gates.py` (test, CRUD/unit)

**Analog:** `tests/test_release_tag_hygiene.py` (239 lines, read in full)

**Module-loading pattern for a non-package `scripts/*.py` file** (lines 1-33 — this is the
canonical, must-copy-verbatim-shape pattern, also confirmed independently in RESEARCH.md):
```python
"""... Exercises `evaluate_tags`, `load_baseline`, and `collect_backed_tags` from
`scripts/release_tag_hygiene.py` directly with literal inputs — no subprocess, no network.
`scripts/` is not an importable package, so the module is loaded via
`importlib.util.spec_from_file_location`.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "release_tag_hygiene.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "release_tag_hygiene", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rth():
    return _load_module()
```
For `tests/test_verify_phase_gates.py`: rename `SCRIPT_PATH` to point at
`scripts/verify_phase_gates.py`, rename the loader name string and fixture (e.g. `vpg`), otherwise
copy verbatim.

**Pure-function unit test pattern** (lines 46-76 — literal-input, no mocking, one behavior per
test):
```python
def test_backed_tag_not_flagged(rth):
    flagged, exempted, _summary = rth.evaluate_tags(["v5.8.0"], {"v5.8.0"}, {})
    assert flagged == []
    assert exempted == []


def test_new_drift_flagged(rth):
    flagged, _exempted, _summary = rth.evaluate_tags(["v5.12.0"], set(), {})
    assert flagged == ["v5.12.0"]
```
Apply the same shape to `check_phase_close()`/`check_destructive_archive()`: one test per gate
condition (missing VERIFICATION.md, `nyquist_compliant: false`, a `⬜ pending` table row, legend
line false-positive per Pitfall 4, missing UAT-SERIES.md entry for a user-facing phase, untracked
phase-dir deletion per Pitfall 1) — construct fixture strings/dicts literally in each test, no
subprocess/network/`tmp_path` git repo required except for the optional hook-integration test.

**tmp_path-based file-loader test pattern** (lines 95-113, `load_baseline` tests):
```python
def test_load_baseline_ignores_comments_and_blanks(rth, tmp_path):
    path = tmp_path / "baseline.txt"
    path.write_text(
        "# comment header\n"
        "\n"
        "v5.9 malformed two-component tag\n"
        "v5.10.0 never pushed\n"
        "# another comment\n"
    )
    result = rth.load_baseline(path)
    assert result == {...}


def test_load_baseline_missing_file_returns_empty(rth, tmp_path):
    result = rth.load_baseline(tmp_path / "does-not-exist.txt")
    assert result == {}
```
Use this exact `tmp_path`-fixture-writes-then-loader-reads shape to test the VERIFICATION.md /
VALIDATION.md / UAT-SERIES.md readers: write a synthetic file to `tmp_path`, call the loader, and
assert on parsed output — never touch real `.planning/` files from unit tests except where
explicitly using real on-disk fixtures as literal content (see next pattern).

**Static/real-fixture guard pattern** (lines 167-239 — reusing a real committed file's content as
a fixture, not synthesizing it):
```python
def _load_workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_workflow_file_exists():
    assert WORKFLOW_PATH.exists(), f"{WORKFLOW_PATH} does not exist"


def test_workflow_is_valid_yaml():
    wf = _load_workflow()
    assert isinstance(wf, dict)
```
RESEARCH.md's Wave-0-Gaps section explicitly recommends reusing the real
`.planning/milestones/v5.11-phases/147-backlog-drain-lifecycle-ledger-tail/147-VALIDATION.md` and
the real `docs/UAT-SERIES.md` `## Series 150: ...` heading as literal fixture content (verified
on-disk, see Shared Patterns below) rather than inventing synthetic YAML/markdown shapes that
might drift from the real format. Mirror this "read a real committed file into a test fixture"
approach for at least one green-path test of `check_phase_close()`.

---

### `CONTRIBUTING.md` (docs update — hook install section)

**Analog:** `CONTRIBUTING.md`'s own existing "Running the test suite" section (verified via direct
read, no hook-setup instructions currently present — confirmed by RESEARCH.md and independently
in this pass).

**Voice/structure pattern** (existing file, top of "Running the test suite"):
```markdown
## Running the test suite

To reproduce exactly what CI runs, use:

```bash
pytest -q -m ""
```

The empty `-m ""` matters: ...
```
Add a new `## Installing the pre-commit artifact gate` section immediately after "Running the
test suite" (or before "CI"), following the same terse imperative voice + fenced-code-block
pattern:
```markdown
## Installing the pre-commit artifact gate

QUIRK enforces phase-completion artifact hygiene (VERIFICATION.md presence, VALIDATION.md
freshness, UAT-SERIES.md coverage, and a destructive-deletion guard for `.planning/phases/`) via
a local git hook — CI cannot see `.planning/` on this public repo (it's gitignored), so this
check only runs if you install it:

```bash
git config core.hooksPath .githooks
```

This is a one-time, per-clone setup step. `git commit --no-verify` bypasses this hook entirely —
by design, git's own escape hatch — so it is a safety net, not a hard guarantee.
```
This documentation-only note about `--no-verify` matches the "Why some tests are quarantined"
section's honest-about-limitations tone already established in this file.

---

## Shared Patterns

### Pure-function / CLI-glue split
**Source:** `scripts/release_tag_hygiene.py` lines 94-148 (`evaluate_tags`) vs. lines 173-234
(`main`)
**Apply to:** `scripts/verify_phase_gates.py` — both `check_phase_close()` and
`check_destructive_archive()` must be pure (take parsed data, return a verdict tuple); all
`subprocess`/disk-reading lives in thin wrapper functions called from `main()`. This is what makes
`tests/test_verify_phase_gates.py` mockless and fast, matching `tests/test_release_tag_hygiene.py`.

### `importlib.util.spec_from_file_location` module loading
**Source:** `tests/test_release_tag_hygiene.py` lines 13-33
**Apply to:** `tests/test_verify_phase_gates.py` — mandatory, since `scripts/` has no
`__init__.py` and is not on `sys.path` by repo convention.

### Exit-code convention (0/1/2)
**Source:** `scripts/release_tag_hygiene.py` lines 173-234
**Apply to:** `scripts/verify_phase_gates.py`'s `main()` — 0 = clean, 1 = gate violation (block
commit), 2 = hard/unexpected error (e.g., malformed STATE.md); the `.githooks/pre-commit` wrapper
must treat both 1 and 2 as "abort the commit."

### `yaml.safe_load()` only, never bare `yaml.load()`
**Source:** RESEARCH.md Security Domain V5 row; existing use in
`tests/test_release_tag_hygiene.py` line 168 (`yaml.safe_load(WORKFLOW_PATH.read_text(...))`)
**Apply to:** Any YAML frontmatter parsing in `scripts/verify_phase_gates.py` for
VALIDATION.md's `nyquist_compliant:` field.

### Real on-disk fixture content, verified in this session
- `147-VALIDATION.md` legend line (verified, line 47 of
  `.planning/milestones/v5.11-phases/147-backlog-drain-lifecycle-ledger-tail/147-VALIDATION.md`):
  `*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*` — the exact false-positive trap from
  Pitfall 4; this is the only `⬜ pending` occurrence in that file (it is a fully-green phase),
  making it a clean "must NOT block" fixture.
- `docs/UAT-SERIES.md:17228`: `## Series 150: Test Suite Green Baseline + CI Gate (Phase 150 —
  v5.12)` — the exact heading regex target for ARTIFACT-03
  (`re.search(rf"^## Series \d+:.*\(Phase {phase_num}\b", text, re.MULTILINE)`).
- `.planning/ROADMAP.md:66-67` (real Phase 150 close diff, commit `b09c9bc`):
  ```diff
  -- [ ] **Phase 150: Test Suite Green Baseline + CI Gate** — `pytest -q` green on a clean
  +- [x] **Phase 150: Test Suite Green Baseline + CI Gate** — `pytest -q` green on a clean
  ```
  Confirms D-03's `^\+- \[x\] \*\*Phase (\d+(?:\.\d+)?):` trigger regex against a real commit.
- `.planning/STATE.md:40` (real Phase-Map row, current on-disk shape):
  ```
  | 150 | Test Suite Green Baseline + CI Gate | SUITE-02, SUITE-03 | Phase 149 (scope depends on triage output) | Complete (2026-08-13; VERIFICATION passed 4/4 — green run 31723764281, red run 31725715958, both live-fire proven on real GitHub Actions) |
  ```
  The `Status` column's trailing cell text containing the literal substring `Complete` is the
  detection target for STATE.md's half of D-03 (or, if simpler, `check_phase_close()` may parse
  ROADMAP.md's checkbox flip alone and treat STATE.md as corroborating/optional — see Open
  Question 3 in RESEARCH.md, already resolved as "no change needed").
- `150-VERIFICATION.md` frontmatter shape (real, lines 1-7 of
  `.planning/phases/150-test-suite-green-baseline-ci-gate/150-VERIFICATION.md`):
  ```yaml
  ---
  phase: 150-test-suite-green-baseline-ci-gate
  verified: 2026-08-13T21:15:00Z
  status: passed
  score: 4/4 success criteria verified
  overrides_applied: 0
  ---
  ```
  ARTIFACT-01's presence check is filename-only (`<N>-VERIFICATION.md` exists under
  `.planning/phases/<N>-*/`); this frontmatter shape is provided for context only, in case the
  planner wants a stronger "not just present but non-empty/parseable" check.
- `.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md` (verified, read lines 1-30): the literal
  incident record ARTIFACT-04 exists to prevent — `phases.clear` deleted `.planning/phases/*`
  as a filesystem operation with zero git-visible trigger; only 19 of ~58 phase files survived
  because only those had ever been `git add`-ed. This is the concrete, non-hypothetical proof for
  Pitfall 1's "staged-diff detection is structurally blind here" finding.

## No Analog Found

None — every file in this phase's scope has at least a role-match analog in the repo (see table
above). The one genuinely novel piece is `.githooks/pre-commit` itself (no prior git-hook
infrastructure exists anywhere in this repo), but its *shape* (thin wrapper, near-zero logic,
delegates entirely to a tested Python script) is directly modeled on how
`release-tag-hygiene.yml` relates to `release_tag_hygiene.py` — same architectural relationship,
different trigger mechanism (git hook vs. GH Actions).

## Metadata

**Analog search scope:** `scripts/`, `tests/`, `.github/workflows/`, `.planning/phases/`,
`.planning/milestones/`, `docs/UAT-SERIES.md`, `CONTRIBUTING.md`, `.planning/STATE.md`,
`.planning/ROADMAP.md`
**Files scanned:** `scripts/release_tag_hygiene.py` (full), `tests/test_release_tag_hygiene.py`
(full), `tests/skip_registry.py` (full, design-reference only), `CONTRIBUTING.md` (full),
`147-VALIDATION.md` (targeted), `150-VERIFICATION.md` (targeted), `docs/UAT-SERIES.md` (grep +
targeted), `.planning/ROADMAP.md` (targeted), `.planning/STATE.md` (targeted),
`.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md` (targeted)
**Pattern extraction date:** 2026-08-13
