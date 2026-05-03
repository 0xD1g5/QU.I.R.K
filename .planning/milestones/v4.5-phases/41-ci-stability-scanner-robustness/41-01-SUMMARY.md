---
phase: 41-ci-stability-scanner-robustness
plan: 01
subsystem: testing
tags: [pytest, sqlalchemy, migrations, test-infrastructure, ast]

requires:
  - phase: 40-chaos-lab-parity
    provides: chaos lab profile parity oracle
provides:
  - "[tool.pytest.ini_options] block with slow + live_infra markers and addopts excluding slow"
  - "tests/skip_registry.py: 9 allowed-skip entries (optional_extra + live_infra)"
  - "tests/test_skip_registry.py: AST-walk meta-test gating unregistered skips"
  - "scan_error_category column on CryptoEndpoint"
  - "_ensure_phase41_columns idempotent migration helper invoked from init_db"
  - "tests/test_scan_robustness.py: 5 xfail stubs for ROBUST-01/02/03"
  - "tests/test_timeouts_config.py: 4 xfail stubs for D-06/D-07"
affects: [41-02, 41-03, 41-04, 41-05, 41-06, 41-07]

tech-stack:
  added: []
  patterns:
    - "AST-walk meta-test gate for skip-marker hygiene"
    - "Phase-scoped _ensure_*_columns migration helper (idempotent ALTER TABLE)"
    - "xfail-with-reason stubs identifying which downstream plan turns each green"

key-files:
  created:
    - tests/skip_registry.py
    - tests/test_skip_registry.py
    - tests/test_scan_robustness.py
    - tests/test_timeouts_config.py
  modified:
    - pyproject.toml
    - quirk/models.py
    - quirk/db.py

key-decisions:
  - "9 ALLOWED_SKIPS entries match RESEARCH.md skip-marker triage table verbatim"
  - "Meta-test marked @pytest.mark.skip_registry_gate (not added to ALLOWED_SKIPS — it is the gate)"
  - "scan_error_category VARCHAR(32) added as new column on CryptoEndpoint (not new table) per RESEARCH §scan_errors[] map"
  - "_ensure_phase41_columns invoked AFTER _ensure_broker_columns to preserve existing migration order"

patterns-established:
  - "Skip registry: (file, line, category, reason) tuples with +/-2 line tolerance in gate"
  - "Test stub pattern: xfail(reason='Plan NN wires X', strict=False) + raise NotImplementedError"
  - "Migration helper naming: _ensure_phase{NN}_columns mirrors _ensure_v43_columns shape"

requirements-completed: [CI-01, CI-03, ROBUST-01, ROBUST-02, ROBUST-03]

duration: ~12 min
completed: 2026-04-29
---

# Phase 41 Plan 01: Wave 0 — Test Infra + ScanError Data Shape Summary

**Pytest config with slow-marker exclusion, AST-walk skip-registry gate, scan_error_category column with idempotent migration, and 9 xfail stubs that downstream plans turn green.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-29
- **Completed:** 2026-04-29
- **Tasks:** 3
- **Files modified:** 7 (3 modified, 4 created)

## Accomplishments

- pyproject.toml `[tool.pytest.ini_options]` registers `slow` + `live_infra` markers and excludes slow by default — bare `pytest` is now under the 60s D-16 budget by construction.
- AST-walk meta-test (`tests/test_skip_registry.py`) detects every `pytest.skip` / `pytest.importorskip` / `@pytest.mark.skipif` site and fails on any not in the 9-entry registry, with +/-2 line tolerance for minor edits.
- `scan_error_category` column added to `crypto_endpoints` with idempotent `_ensure_phase41_columns` migration; `init_db` invokes it after the existing v4.4 broker migration. Smoke-tested for double-init.
- 9 xfail test stubs (5 robustness + 4 timeouts) collect cleanly under pytest, each annotated with the plan that lands the wiring (Plans 02–04).

## Task Commits

1. **Task 1: pytest config + skip registry + meta-gate test** — `9552091` (feat)
2. **Task 2: ScanError data shape — column + migration helper** — `17e1f57` (feat)
3. **Task 3: Robustness + timeouts test stubs** — `2fb8138` (test)

## Files Created/Modified

- `pyproject.toml` — Added `[tool.pytest.ini_options]` block with markers + addopts + testpaths
- `tests/skip_registry.py` — ALLOWED_SKIPS list of 9 (file, line, category, reason) tuples
- `tests/test_skip_registry.py` — AST-walk gate; marked `@pytest.mark.skip_registry_gate`; exempts itself + registry from the walk
- `quirk/models.py` — Added `scan_error_category = Column(String(32), nullable=True)` immediately after `scan_error`
- `quirk/db.py` — Added `_PHASE41_COLUMN_DDLS` + `_ensure_phase41_columns(engine)`; called from `init_db` after `_ensure_broker_columns`
- `tests/test_scan_robustness.py` — 5 xfail stubs (ROBUST-01/02/03 + KeyboardInterrupt propagation)
- `tests/test_timeouts_config.py` — 4 xfail stubs (TimeoutsCfg, RetryCfg, 2 deprecation alias tests)

## Decisions Made

- **scan_error_category storage:** Added as a new column on `CryptoEndpoint` (not a separate `scan_errors` table). Preserves existing trends.py counting logic and reuses `_ensure_*_columns` migration pattern. Matches RESEARCH §scan_errors[] map recommendation.
- **Skip registry shape:** Single `tests/skip_registry.py` module exporting `ALLOWED_SKIPS` (per CONTEXT D-02 first option). +/-2 line tolerance absorbs minor test-file edits without forcing registry churn.
- **Meta-test marker:** Used a custom `@pytest.mark.skip_registry_gate` rather than adding the meta-test's own location to ALLOWED_SKIPS — it is the gate, not a tested skip. Marker is unregistered in pyproject.toml (which is fine: pytest only warns on unknown markers, doesn't fail).
- **xfail rather than skip on stubs:** xfail keeps the tests visible in collection (so reviewers see what work is pending) while not blocking the suite. Each stub names the plan that lands the wiring.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Idempotency smoke-test signature mismatch**
- **Found during:** Task 2 (ScanError data shape verification)
- **Issue:** Plan acceptance criterion specifies `init_db(e)` where `e` is a SQLAlchemy `Engine`, but the actual `init_db` signature in `quirk/db.py` takes `db_path: str` and constructs the engine internally.
- **Fix:** Ran the equivalent idempotency smoke test against the real signature (`init_db(path); init_db(path)` against a tempfile-backed sqlite DB) — second call did not raise.
- **Files modified:** none (verification-only adjustment; no source change needed)
- **Verification:** `python -c "from quirk.db import init_db; ..."` against tempfile path — exits 0.
- **Committed in:** 17e1f57 (Task 2 commit; the helper itself is correct, only the verification command needed adapting)

**2. [Rule 1 - Doc string] xfail count miscount in scan_robustness docstring**
- **Found during:** Task 3 verification
- **Issue:** Module docstring contained the literal string ```@pytest.mark.xfail``` which inflated `grep -c "@pytest.mark.xfail"` to 6 instead of the acceptance-required 5 (one per test function).
- **Fix:** Reworded the docstring to refer to "pytest xfail" without the literal decorator syntax.
- **Files modified:** tests/test_scan_robustness.py
- **Verification:** `grep -c "@pytest.mark.xfail" tests/test_scan_robustness.py` → 5 (matches acceptance).
- **Committed in:** 2fb8138 (Task 3 commit; included before push)

---

**Total deviations:** 2 auto-fixed (1 verification-command adjustment, 1 docstring grep-counter fix)
**Impact on plan:** No scope creep. Plan executed as written; only verification harness adapted to actual code shape.

## Issues Encountered

None of substance. Pre-existing test-collection warnings (e.g., "broker_scanner_kafka.py: 12" — already an `importorskip`) surface only when the gate test runs and are by design — that's the meta-test's job.

## Threat Flags

None. This plan changes only test infrastructure and adds a single non-secret column; no new network surface, auth path, or trust boundary.

## Next Phase Readiness

- Plan 02 (Wave 1, TimeoutsCfg/RetryCfg) has its 4 xfail stubs ready to flip green.
- Plan 03 (per-scanner timeout reads) has 1 xfail stub ready.
- Plan 04 (D-12 advisory + D-14 BaseException wrapper) has 4 xfail stubs ready.
- Plan 05 (D-04 stale-skip deletion) has the meta-test gate ready — running `pytest tests/test_skip_registry.py` after Plan 05 will validate the deletions landed correctly.
- `scan_error_category` column is in place for Plans 03/04 producers and Plan 04 trends.py consumer (D-15).

## Self-Check: PASSED

Files verified present:
- pyproject.toml (modified, contains `[tool.pytest.ini_options]`)
- tests/skip_registry.py (created, 9 ALLOWED_SKIPS entries)
- tests/test_skip_registry.py (created, ast.walk gate)
- tests/test_scan_robustness.py (created, 5 xfail stubs)
- tests/test_timeouts_config.py (created, 4 xfail stubs)
- quirk/models.py (modified, scan_error_category column)
- quirk/db.py (modified, _ensure_phase41_columns helper + invocation)

Commits verified in `git log`:
- 9552091 — Task 1
- 17e1f57 — Task 2
- 2fb8138 — Task 3

---
*Phase: 41-ci-stability-scanner-robustness*
*Plan: 01*
*Completed: 2026-04-29*
