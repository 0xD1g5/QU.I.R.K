---
phase: 45-install-day-ux
plan: 01
subsystem: packaging
tags: [packaging, extras, regression-test, install]
requires: []
provides:
  - "[all] meta-extra in pyproject.toml"
  - "CI regression guard against impacket inclusion in [all]"
  - "User-facing docs for [all] composition + Playwright cost"
affects:
  - pyproject.toml
  - tests/test_install_all_excludes_impacket.py
  - docs/installation.md
tech_stack:
  added: []
  patterns:
    - "Self-referential PEP 621 extras (already used by `motion`)"
    - "pip --report JSON dry-run as CI regression mechanism (PEP 658-aware)"
key_files:
  created:
    - tests/test_install_all_excludes_impacket.py
  modified:
    - pyproject.toml
    - docs/installation.md
decisions:
  - "[all] composition is exactly cloud + db + motion + redis + dashboard (D-01) — identity intentionally omitted"
  - "Regression test marked @pytest.mark.slow so it runs in CI under `pytest -m slow` but not in default local runs"
  - "Test additionally asserts presence of expected component packages (kubernetes, psycopg2-binary, redis, fastapi) to prevent vacuous pass when [all] is undefined"
  - "Documented two-venv pattern for consultants who need both [all] and [identity]"
metrics:
  duration_minutes: 8
  completed_date: 2026-05-03
  commits: 3
  tasks_completed: 3
---

# Phase 45 Plan 01: Add `[all]` Meta-Extra Summary

**One-liner:** Added the `[all]` meta-extra to `pyproject.toml` (cloud+db+motion+redis+dashboard,
impacket explicitly excluded), wired a slow-marked CI regression test that asserts
`pip install quirk[all]` does not transitively pull `impacket`, and documented the `[all]`
composition plus Playwright browser-binary cost in `docs/installation.md`.

## Goal

Phase 45 SC #3: `pip install quirk[all]` installs all scanner extras; `impacket` is NOT in
`[all]` (stays in `[identity]` only). This is the structural guard that prevents the
pyOpenSSL / cryptography downgrade chain from breaking the TLS scanner.

## What Was Built

### Task 1 — Regression test (RED → GREEN)

`tests/test_install_all_excludes_impacket.py` invokes
`python -m pip install --dry-run --ignore-installed --quiet --report <tmp>/report.json -e <repo>[all]`,
parses the JSON report, and asserts:

1. The pip resolver did not warn `does not provide the extra 'all'` (catches missing-extra silent no-op).
2. Expected component packages (`kubernetes`, `psycopg2-binary`, `redis`, `fastapi`) are present (proves `[all]` actually expanded).
3. `impacket` is absent (case-insensitive) from the resolved install set.

Marked `@pytest.mark.slow`; default `pytest` runs skip it. Failure messages reference
Phase 45 / D-01 and the pyOpenSSL / cryptography downgrade rationale so a future maintainer
who breaks the guard immediately understands why the test exists.

Commit: `5563e9b`

### Task 2 — `[all]` meta-extra (GREEN)

Appended to `[project.optional-dependencies]` in `pyproject.toml`:

```toml
all = [
    "quirk[cloud]",
    "quirk[db]",
    "quirk[motion]",
    "quirk[redis]",
    "quirk[dashboard]",
]
# NOTE: quirk[identity] is INTENTIONALLY EXCLUDED ...
```

Self-referential extras (matching the existing `motion` pattern) keep the per-extra package
lists as the single source of truth. Inline comment plus the regression test together prevent
future drift.

Verification:
- `pip install --dry-run -e '.[all]'` resolves cleanly (69+ packages including all expected components).
- `pytest -m slow tests/test_install_all_excludes_impacket.py -x` → PASS.
- `pip install --dry-run -e '.[identity]'` still includes `impacket` (regression intact).
- `python -m compileall quirk run_scan.py` → rc 0.

Commit: `fdbde03`

### Task 3 — User-facing documentation

`docs/installation.md` updated with four substantive additions:

1. **System Requirements row:** pip ≥ 21.3 (required for self-referential extras), pip ≥ 22.2 recommended for the `--report` JSON test in CI.
2. **Optional Dependencies table row** (new top entry): `pip install quirk[all]` — composition, identity exclusion called out, Playwright ~250 MB cost noted.
3. **New subsection "Why `[all]` excludes `[identity]`"** — explains the impacket → pyOpenSSL → cryptography downgrade chain and gives consultants a two-venv pattern for needing both surfaces.
4. **Coverage advisories callout** after install verification — describes the new "skip with INFO advisory" behavior (Plan 02 contract) so users know the tool degrades gracefully when an extra is absent.

Commit: `3595e63`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Test bug] Strengthened RED test to fail loudly when `[all]` is undefined**

- **Found during:** Task 1 verification.
- **Issue:** When the `[all]` extra does not yet exist, pip emits a WARNING (`does not provide the extra 'all'`) but exits with returncode 0 and resolves only the base package. Without `impacket` in the base resolution, the original test passed vacuously in the RED phase — a TDD fail-fast violation.
- **Fix:** Added two assertions before the impacket check: (a) the pip output must not contain the literal warning string, and (b) the resolved set must include known sentinel packages from each component extra (`kubernetes`, `psycopg2-binary`, `redis`, `fastapi`). This guarantees the impacket assertion is meaningful both before and after Task 2.
- **Files modified:** `tests/test_install_all_excludes_impacket.py`
- **Commit:** folded into `5563e9b` (single Task 1 commit).

## TDD Gate Compliance

- RED gate: `5563e9b` (`test(45-01): add regression test ...`) — confirmed FAIL on `[all]` undefined.
- GREEN gate: `fdbde03` (`feat(45-01): add [all] meta-extra ...`) — test PASS.
- REFACTOR: not required.

## Verification

| Check | Status |
|-------|--------|
| `pip install --dry-run -e '.[all]'` resolves | PASS |
| `pytest -m slow tests/test_install_all_excludes_impacket.py -x` | PASS |
| `pip install --dry-run -e '.[identity]'` still includes impacket | PASS (regression intact) |
| `python -m compileall quirk run_scan.py` | rc 0 |
| `docs/installation.md` contains required strings (`pip install quirk[all]`, `excludes [identity]`, Playwright) | 7 hits (≥ 3 required) |

## Self-Check: PASSED

- FOUND: `tests/test_install_all_excludes_impacket.py`
- FOUND: `pyproject.toml` (contains `all = [`)
- FOUND: `docs/installation.md` ("Why `[all]` excludes")
- FOUND commits: `5563e9b`, `fdbde03`, `3595e63`
