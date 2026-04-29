---
phase: 38-identity-api-regression-fix
plan: "01"
subsystem: identity-api
tags: [bug-fix, scan-window, regression-test, identity-findings]
dependency_graph:
  requires: []
  provides: [GAP-01-fix, GAP-02-fix, SESSION_BRACKET-constant]
  affects: [quirk/dashboard/api/routes/scan.py, tests/test_identity_surface.py]
tech_stack:
  added: []
  patterns: [session-bracket-window, shared-cache-sqlite-test-isolation]
key_files:
  modified:
    - quirk/dashboard/api/routes/scan.py
    - tests/test_identity_surface.py
decisions:
  - "Use backward bracket [MAX - SESSION_BRACKET, MAX] instead of strftime-based 1-second forward window for implicit-latest query"
  - "Use unique named shared-cache SQLite URI per test helper to avoid cross-test table contamination"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-29"
  tasks_completed: 3
  files_modified: 2
---

# Phase 38 Plan 01: Scan-Window Regression Fix Summary

**One-liner:** Replaced 1-second forward strftime window in `/api/scan/latest` implicit-latest branch with 5-minute backward bracket (`SESSION_BRACKET = timedelta(minutes=5)`) anchored on `MAX(scanned_at)`, restoring SAML/OIDC visibility and closing GAP-01/GAP-02.

## Exact Diff Applied to scan.py

### New module-level constant (after `router = APIRouter()`, line 35):

```python
# Phase 38 (D-01): backward bracket from MAX(scanned_at) restores SAML/OIDC visibility under timestamp skew
SESSION_BRACKET = timedelta(minutes=5)
```

### Implicit-latest branch (else: clause) — OLD:

```python
else:
    # Derive the latest scan second from MAX, then load all endpoints in that second.
    latest_ts_str = db.query(
        func.strftime("%Y-%m-%d %H:%M:%S", func.max(CryptoEndpoint.scanned_at))
    ).scalar()
    if latest_ts_str is None:
        raise HTTPException(
            status_code=404,
            detail="No scan results found. Run your first scan: quirk --config config.yaml",
        )
    latest_ts = datetime.fromisoformat(latest_ts_str)
    endpoints: list[CryptoEndpoint] = (
        db.query(CryptoEndpoint)
        .filter(
            CryptoEndpoint.scanned_at >= latest_ts,
            CryptoEndpoint.scanned_at < latest_ts + timedelta(seconds=1),
        )
        .all()
    )
```

### Implicit-latest branch — NEW:

```python
else:
    # D-01: anchor on MAX(scanned_at), then load all endpoints in the
    # SESSION_BRACKET window before that maximum. This restores SAML/OIDC
    # findings that the previous 1-second forward window silently excluded
    # when Kerberos finished last (ISSUE-3 / DEF-v4.4-02).
    latest_ts = db.query(func.max(CryptoEndpoint.scanned_at)).scalar()
    if latest_ts is None:
        raise HTTPException(
            status_code=404,
            detail="No scan results found. Run your first scan: quirk --config config.yaml",
        )
    endpoints: list[CryptoEndpoint] = (
        db.query(CryptoEndpoint)
        .filter(
            CryptoEndpoint.scanned_at >= latest_ts - SESSION_BRACKET,
            CryptoEndpoint.scanned_at <= latest_ts,
        )
        .all()
    )
```

The explicit `?scan_id=` branch (lines 576-591 after edit) is byte-for-byte unchanged — still uses `target_ts + timedelta(seconds=1)`.

## Tests Added

All three methods live in `tests/test_identity_surface.py::Issue3ScanWindowRegressionTest`.

### Helper extracted: `_make_client_and_session(self)`

Returns `(TestClient, TestingSession)` backed by a unique named shared-cache SQLite URI (`sqlite:///file:{uuid}?mode=memory&cache=shared&uri=true`) to ensure the app's `get_db` override and the test's direct writes share the same in-memory database instance. Each call generates a new UUID so tests are isolated.

### `test_saml_visible_with_earlier_dnssec`

- Seeds DNSSEC at `T = 2026-01-15 12:00:00` and SAML at `T+60s = 2026-01-15 12:01:00`.
- `GET /api/scan/latest` — asserts status 200.
- Asserts `"SAML" in protocols` AND `"DNSSEC" in protocols` from `identity_findings[]`.
- Proves the 5-minute backward bracket covers ≥60s timestamp skew on the early side.

### `test_explicit_scan_id_uses_exact_second`

- Seeds Kerberos at `ts_a = 2026-01-15 12:00:00` (older) and `ts_b = 2026-01-15 12:05:00` (newer, 5 min later).
- `GET /api/scan/latest?scan_id={ts_a.isoformat()}` — asserts status 200.
- Asserts `"dc-old.example.com" in hosts` AND `"dc-new.example.com" not in hosts`.
- Proves the explicit `?scan_id=` branch was NOT widened — it still uses 1-second exact-second semantics.

## Full-Suite Pytest Result

```
1 failed, 664 passed, 7 skipped, 9 warnings in 6.79s
```

The single failure is `tests/test_hygiene.py::CodeHygieneTests::test_all_completed_phase_validations_nyquist_compliant` — pre-existing, closed by PLAN 38-03.

Focused subset (identity_surface + identity_findings_accuracy + dashboard_api):
```
37 passed in 0.84s
```

## Tests Outside test_identity_surface.py With Changed Expected Counts

None. The bracket fix did not cause any previously-passing test to change its expected endpoint count. Pitfall 1 (tests asserting specific counts on `/api/scan/latest`) was monitored during the full-suite run — no count-assertion tests newly failed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Shared-cache SQLite URI required for `_make_client_and_session` helper**
- **Found during:** Task 2 — first run of `test_explicit_scan_id_uses_exact_second`
- **Issue:** Initial helper used `sqlite:///:memory:` (per-connection anonymous database). Each new SQLite connection to `:memory:` gets its own empty database, so `Base.metadata.create_all(engine)` created tables on one connection while the app's `override_get_db` opened a different connection with no tables, causing `OperationalError: no such table: crypto_endpoints`.
- **Fix:** Changed helper to use `sqlite:///file:{uuid}?mode=memory&cache=shared&uri=true` with a unique UUID per call, matching the shared-cache pattern already used by `test_issue3_scan_window_returns_all_identity_protocols`. UUID ensures per-test isolation.
- **Files modified:** `tests/test_identity_surface.py` (within Task 2 commit)
- **Commit:** 841e07c

## Self-Check: PASSED

- quirk/dashboard/api/routes/scan.py: FOUND
- tests/test_identity_surface.py: FOUND
- Commit e5f2572 (scan.py fix): FOUND
- Commit 841e07c (test extensions): FOUND
- `grep -c "^SESSION_BRACKET = timedelta(minutes=5)" scan.py` = 1: CONFIRMED
- `grep -c "latest_ts - SESSION_BRACKET" scan.py` = 1: CONFIRMED
- `grep -c "scanned_at < target_ts + timedelta(seconds=1)" scan.py` = 1 (explicit branch unchanged): CONFIRMED
- Issue3ScanWindowRegressionTest: 3 passed: CONFIRMED
- Full suite: 664 passed, 1 pre-existing failure: CONFIRMED
