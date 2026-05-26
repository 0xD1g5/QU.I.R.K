---
phase: 109-console-ingestion-api
plan: "03"
subsystem: tests
tags: [sensor, ingestion, push-endpoint, auth-gate, audit, version-skew, extra-ignore, enroll, ast-gate, uat]
dependency_graph:
  requires: [109-02]
  provides: [CONSOLE-02-test, CONSOLE-03-test, CONSOLE-04-test, CONSOLE-05-test]
  affects:
    - tests/test_sensor_ingest.py
    - tests/test_console_enroll.py
    - tests/scanner/test_phase57_invariants.py
    - docs/UAT-SERIES.md
tech_stack:
  added: []
  patterns:
    - "in-memory SQLite TestClient factory (mirror of test_api_auth.py)"
    - "_seed_sensor() helper: writes Sensor row before push tests"
    - "_build_envelope() + _compress(): canonical zstd push body builder"
    - "INGEST_FILES parametrized AST gate (mirror of SCANNER_FILES pattern in test_phase57_invariants.py)"
    - "QUIRK_DB_PATH monkeypatch + tmp_path DB for enroll CLI tests"
key_files:
  created:
    - tests/test_sensor_ingest.py
    - tests/test_console_enroll.py
  modified:
    - tests/scanner/test_phase57_invariants.py
    - docs/UAT-SERIES.md
decisions:
  - "109-03-D-01: _build_envelope helper uses datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ') (tz-naive UTC — mirrors sensor_cmd._build_envelope convention)"
  - "109-03-D-02: INGEST_FILES added alongside SCANNER_FILES (not merged in) so Phase 57 gate and Phase 109 gate are independently readable"
  - "109-03-D-03: UAT-Series.md synced via printf+cat+cp pattern (not obsidian CLI) per CLAUDE.md mandatory step 3 (file too large for CLI content=)"
metrics:
  duration: "~20 min"
  completed: "2026-05-25"
  tasks_completed: 3
  files_modified: 4
---

# Phase 109 Plan 03: Test Suite + UAT-SERIES Update Summary

**One-liner:** Complete CONSOLE-01..05 test coverage with ten sensor-ingest contract tests, two console-enroll provisioning tests, an INGEST_FILES safe_str AST gate across both new ingest modules, and Series 109 added to docs/UAT-SERIES.md (synced to Obsidian).

## What Was Built

### Task 1: `tests/test_sensor_ingest.py` — full POST /api/sensor/push contract

Created `tests/test_sensor_ingest.py` with ten tests covering the complete §6 security contract:

- `test_push_endpoint_exists` — route `/api/sensor/push` registered (CONSOLE-01)
- `test_push_requires_auth` — 401 without auth header (CONSOLE-02)
- `test_push_413_body_too_large` — 413 on Content-Length > 10 MB (CONSOLE-03)
- `test_push_409_duplicate_payload` — first push 200, second push 409 (CONSOLE-03)
- `test_push_422_replay_window` — stale pushed_at → 422 with `console_utc` in detail (CONSOLE-03)
- `test_push_200_accepted` — valid push → 200, SensorPush row, sensors.last_push_at, CryptoEndpoint rows (CONSOLE-03)
- `test_audit_row_written` — IntegrationDelivery row on success (status="ok") AND failure (status="failed") (CONSOLE-04)
- `test_extra_fields_ignored` — extra field in envelope → 200 (CONSOLE-05)
- `test_version_skew_graceful` — schema_version="99.99.99" → not 422/500 (CONSOLE-05)
- `test_unknown_sensor_id_4xx` — unregistered sensor_id → 4xx + failed audit row

Helpers: `_build_envelope()`, `_compress()`, `_seed_sensor()`, `_app_with_db()`.

**Test result:** 10/10 passed.

**Commit:** `2ff89c0`

### Task 2: `tests/test_console_enroll.py` + extend safe_str AST gate

Created `tests/test_console_enroll.py` with two tests:

- `test_console_enroll`: invokes `run_console(["enroll","--sensor-id","S1","--segment","dmz"])` against a tmp DB, asserts one sensors row + one sensor_tokens row, verifies SHA-256(raw_token) == token_hash, and confirms raw token absent from all DB columns.
- `test_console_enroll_duplicate`: second enroll with same sensor_id exits non-zero; row counts remain 1/1 (no partial write).

Extended `tests/scanner/test_phase57_invariants.py`:
- Added `INGEST_FILES` list containing `console_cmd.py` and `sensor.py`.
- Added `test_ingest_no_raw_exception_stringification` parametrized over `INGEST_FILES`: strips comments via the existing `_strip_comments` helper, asserts no `\bstr\s*\(\s*exc\b` or `\brepr\s*\(\s*exc\b` matches. Both files pass (safe_str used on all error paths per Phase 109-02).

**Test result:** 2/2 enroll + 12/12 invariants (including 2 new INGEST_FILES parametrized runs).

**Commit:** `b71948d`

### Task 3: Update `docs/UAT-SERIES.md` and sync to Obsidian

Updated `docs/UAT-SERIES.md`:
- Bumped `**Last Updated:**` to `2026-05-25` with Phase 109 COMPLETE summary.
- Added `## Series 109: Console Ingestion API (Phase 109 — v5.4)` with four test cases:
  - `UAT-109-01`: quirk console enroll provisioning — Automated
  - `UAT-109-02`: POST /api/sensor/push 401 gating — Automated
  - `UAT-109-03`: §6 failure ladder + 200 accepted + audit trail — Automated
  - `UAT-109-04`: extra='ignore' + version-skew graceful + safe_str AST gate — Automated

Synced to Obsidian vault via `printf+cat+cp` pattern per CLAUDE.md mandatory step 3.

Committed via `docs(phase-109): update UAT-SERIES.md` using gsd-tools.cjs.

**Commit:** `c552f60`

## Verification Results

```
pytest tests/ -k "sensor_push or console_enroll or ingest" -q
→ 22 passed, 2585 deselected (10 sensor_ingest + 2 console_enroll + 10 phase57_invariants)

python -m compileall quirk run_scan.py
→ Exit code 0 (CLEAN)

grep -q "sensor/push\|console enroll\|Console Ingestion" docs/UAT-SERIES.md && echo PASS
→ PASS

test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md" && echo PASS
→ PASS
```

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria met across all three tasks.

## Threat Surface Scan

No new runtime code — plan produces only test files and documentation. No new network endpoints, auth paths, file access patterns, or schema changes.

## Known Stubs

None.

## Self-Check: PASSED

- `tests/test_sensor_ingest.py` created: FOUND
- `tests/test_console_enroll.py` created: FOUND
- `tests/scanner/test_phase57_invariants.py` modified (INGEST_FILES + parametrized gate): FOUND
- `docs/UAT-SERIES.md` updated with Series 109 + today's Last Updated: FOUND
- Vault copy `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`: FOUND
- Commit `2ff89c0` (Task 1 sensor_ingest tests): FOUND
- Commit `b71948d` (Task 2 enroll tests + AST gate): FOUND
- Commit `c552f60` (Task 3 UAT-SERIES.md): FOUND
- `python -m compileall quirk run_scan.py`: CLEAN (exit 0)
- `pytest tests/ -k "sensor_push or console_enroll or ingest" -q`: 22 passed
- INGEST_FILES gate: 2 parametrized tests pass (console_cmd.py + sensor.py)
- 401 gating test asserts status_code == 401: PASS
- 200 accepted test asserts SensorPush + last_push_at + CryptoEndpoint: PASS
- audit_row test asserts ok AND failed rows in integration_deliveries: PASS
- version_skew test asserts not 422 and not 500: PASS
