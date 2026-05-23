---
phase: 91
plan: 01
subsystem: tests, quirk/models, quirk/db, quirk/scanner, quirk/assessment, quirk/engine, docs, planning
tags: [cleanup, deprecation, bookkeeping, jwt-advisory, nyquist]
depends_on: []
provides: [conftest-db-isolation, utcnow-clean, nyquist-current, jwt-advisory-docs]
affects: [tests/conftest.py, tests/test_dashboard_scan_history.py, quirk/models.py, quirk/db.py, quirk/scanner/jwt_scanner.py, docs/operators-guide.md, docs/configuration.md]
tech_stack:
  added: []
  patterns: [autouse-monkeypatch-fixture, collection-time-env-set]
key_files:
  created:
    - .planning/phases/90-oqs-nginx-pqc-hybrid/90-VALIDATION.md
  modified:
    - tests/conftest.py
    - tests/test_dashboard_scan_history.py
    - quirk/models.py
    - quirk/db.py
    - quirk/scanner/tls_scanner.py
    - quirk/assessment/operator_context.py
    - quirk/scanner/fingerprint.py
    - quirk/engine/findings_evaluator.py
    - quirk/scanner/jwt_scanner.py
    - docs/operators-guide.md
    - docs/configuration.md
    - .planning/codebase/CONCERNS.md
    - .planning/phases/87-dependency-hygiene/87-VALIDATION.md
    - .planning/phases/88-scoring-residuals/88-VALIDATION.md
    - .planning/phases/89-chaos-lab-profiles/89-VALIDATION.md
decisions:
  - "91-01-D-01: Collection-time QUIRK_DB_PATH set via os.environ at conftest import (not just autouse fixture) to fix 7 module collection errors triggered by module-level app = create_app() in app.py"
  - "91-01-D-02: CONCERNS.md stale sections annotated Resolved with context rather than deleted outright, preserving historical audit trail"
  - "91-01-D-03: allow_insecure_jwks documented in both operators-guide.md and configuration.md per plan requirement"
metrics:
  duration: ~8 minutes
  completed: 2026-05-22
  tasks_completed: 3
  tasks_total: 3
  files_modified: 14
  files_created: 1
---

# Phase 91 Plan 01: Code Cleanup Bookkeeping — Tier-A Summary

**One-liner:** QUIRK_DB_PATH conftest isolation fixture (collection-time + autouse) eliminates 7 collection errors; 9 datetime.utcnow() calls replaced with timezone-aware datetime.now(timezone.utc); v3.5.1 version string removed from operator output; v3.x/v4.x era-tagging comments stripped; WHY: advisory comments added at both httpx.get JWKS call sites with allow_insecure_jwks documented in operator and configuration guides; VALIDATION.md frontmatter updated for phases 87/88/89/90.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add autouse QUIRK_DB_PATH conftest fixture (CLEAN-03a) | 7ea806a | tests/conftest.py |
| 2 | Fix datetime.utcnow() + stale v3.x/v4.x comment sweep (CLEAN-01) | 67786fe | tests/test_dashboard_scan_history.py, quirk/models.py, quirk/db.py, quirk/scanner/tls_scanner.py, quirk/assessment/operator_context.py, quirk/scanner/fingerprint.py, quirk/engine/findings_evaluator.py |
| 3 | VALIDATION.md currency, CONCERNS.md cleanup, JWT advisory docs (CLEAN-03b/CLEAN-04) | 89e8063 | 87/88/89/90-VALIDATION.md, CONCERNS.md, jwt_scanner.py, operators-guide.md, configuration.md |

---

## Verification Results

### CLEAN-01: datetime.utcnow() deprecation gate
- `python -W error::DeprecationWarning -m pytest tests/test_dashboard_scan_history.py -q` — PASS (no DeprecationWarning errors; 5 pre-existing assertion failures unchanged)
- `grep -c utcnow tests/test_dashboard_scan_history.py` → 0

### CLEAN-03a: Collection error elimination
- `python -m pytest tests/ --collect-only -q` (no QUIRK_DB_PATH) → **0** "Multiple QU.I.R.K. DBs found" errors (was 7)

### CLEAN-03b: VALIDATION.md currency
- All four of 87/88/89/90-VALIDATION.md carry `nyquist_compliant: true`
- `tests/test_infra03_nyquist_coverage.py` → 18/18 PASS

### CLEAN-04: JWT advisory
- `grep -n 'WHY:' quirk/scanner/jwt_scanner.py` → 2 matches (both httpx.get call sites)
- `grep allow_insecure_jwks docs/operators-guide.md` → present
- `grep allow_insecure_jwks docs/configuration.md` → present

### Regression gate
- Full suite: 44 failed / 1882 passed / 7 skipped — identical to pre-plan baseline (no new failures)
- `python -m compileall quirk` → clean

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Collection-time QUIRK_DB_PATH fix required os.environ at import time**
- **Found during:** Task 1
- **Issue:** The plan described an autouse `monkeypatch.setenv` fixture, but `quirk/dashboard/api/app.py` has a module-level `app = create_app()` call that triggers `_default_db_path()` at pytest collection time — before any fixture can execute. The autouse fixture alone doesn't fix collection errors.
- **Fix:** Added `os.environ["QUIRK_DB_PATH"]` set at conftest.py module import time (inside an `if not os.environ.get("QUIRK_DB_PATH"):` guard) in addition to the autouse fixture. The autouse fixture still provides per-test isolation; the module-level set prevents collection-time crashes.
- **Files modified:** tests/conftest.py
- **Commit:** 7ea806a

---

## Known Stubs

None — all plan goals achieved.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. CONCERNS.md §8.1 (JWT verify=False) is now documented per CLEAN-04; no behavioral change.

---

## Self-Check: PASSED

- tests/conftest.py exists: FOUND
- tests/test_dashboard_scan_history.py modified: FOUND
- .planning/phases/90-oqs-nginx-pqc-hybrid/90-VALIDATION.md created: FOUND
- Commits 7ea806a, 67786fe, 89e8063: verified in git log
