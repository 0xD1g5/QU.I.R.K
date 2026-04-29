---
phase: 39
plan: "01"
subsystem: testing
tags: [tdd, red-scaffold, dar, dashboard, gap-04]
dependency_graph:
  requires: []
  provides: [tests/test_dar_dashboard.py]
  affects: []
tech_stack:
  added: []
  patterns: [tdd-red, simplenamespace-fixture, dashboard-client-fixture]
key_files:
  created:
    - tests/test_dar_dashboard.py
  modified: []
decisions:
  - "Tests use deferred import (inside each test function) per D-04 pattern from test_dashboard_api.py"
  - "_ep() fixture extended with service_detail, dat_scan_json, scan_error, severity defaults to support all DAR protocol variants"
  - "Integration tests accept 200 or 404 (no scan data in test DB) — matching precedent from test_dashboard_api.py"
metrics:
  duration: "~80 seconds"
  completed_date: "2026-04-29"
  tasks_completed: 1
  files_created: 1
  files_modified: 0
---

# Phase 39 Plan 01: DAR Test Scaffold (RED) Summary

**One-liner:** Failing pytest scaffold with 8 tests covering DarFinding category dispatch (database/object_storage/kubernetes/vault) plus API contract, establishing feedback contract for Plan 02 GREEN phase.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing DAR test scaffold | c9d7f14 | tests/test_dar_dashboard.py (created) |

## What Was Built

### Task 1: Write failing DAR test scaffold

Created `tests/test_dar_dashboard.py` with 8 failing unit and integration tests:

**Extended `_ep()` fixture factory** — copied from `tests/test_dashboard_api.py` lines 100-104, extended with `service_detail=None`, `dat_scan_json=None`, `scan_error=None`, `severity="INFO"` to cover all DAR projection inputs.

**Unit tests (6):**
- `test_derive_dar_findings_db` — POSTGRESQL/ssl-enforced endpoint produces `DarFinding(category="database")`
- `test_derive_dar_db_postgresql` — `service_detail="PostgreSQL/ssl-off"` maps to `encryption_at_rest=False, tls_in_transit=False, severity="HIGH"`
- `test_derive_dar_s3` — S3 endpoint with `dat_scan_json={"service_detail":"S3/sse-s3"}` maps to `encryption_mode="SSE-S3", encryption_at_rest=True, category="object_storage"`
- `test_derive_dar_k8s_dispatch` — Two KUBERNETES endpoints dispatch by `"namespace" in dat` vs. `"provider"` presence; namespace/encryption_provider fields populated correctly
- `test_derive_dar_vault_dispatch` — Three VAULT endpoints dispatch to `mount_type` in `{"transit","pki","auth"}` based on key_name/mount_point/auth_path presence; seal_type and auto_unseal always None
- `test_derive_dar_scan_error_excluded` — Endpoint with `scan_error` set returns empty list

**Integration tests (2):**
- `test_api_dar_findings_key` — GET /api/scan/latest includes `dar_findings` key as list
- `test_api_dar_findings_empty` — `dar_findings` is `[]` (not absent) when no DAR data

**RED state confirmed:** All unit tests fail with `ImportError: cannot import name '_derive_dar_findings' from 'quirk.dashboard.api.routes.scan'` — implementation does not exist yet. This is the correct TDD RED state for Plan 02 to GREEN against.

## Deviations from Plan

None - plan executed exactly as written. All 8 tests match the specified behavior contract from VALIDATION.md.

## Known Stubs

None — this is a test-only file. No implementation stubs.

## Threat Flags

None — test code only, no runtime trust boundaries crossed (per T-39-00 in plan threat model).

## Self-Check: PASSED

- `tests/test_dar_dashboard.py` exists: FOUND
- Commit `c9d7f14` exists: FOUND
- 8 test functions present: CONFIRMED
- All tests fail with ImportError (RED): CONFIRMED
- `python -m compileall tests/test_dar_dashboard.py`: PASS
