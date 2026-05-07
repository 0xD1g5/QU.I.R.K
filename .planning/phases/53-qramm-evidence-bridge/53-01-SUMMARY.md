---
phase: 53-qramm-evidence-bridge
plan: "01"
subsystem: qramm
tags: [qramm, evidence-bridge, tdd, red-scaffold]
dependency_graph:
  requires: []
  provides: [tests/test_qramm_evidence_bridge.py]
  affects: [quirk/qramm/evidence_bridge.py]
tech_stack:
  added: []
  patterns: [UUID-named in-memory SQLite fixture, FastAPI TestClient override, TDD RED scaffold]
key_files:
  created:
    - tests/test_qramm_evidence_bridge.py
  modified: []
decisions:
  - "Test file written verbatim from plan spec — no modifications needed; all 8 tests collected and fail RED as expected"
metrics:
  duration_minutes: 1
  tasks_completed: 1
  files_changed: 1
  completed_date: "2026-05-07"
---

# Phase 53 Plan 01: QRAMM Evidence Bridge RED Scaffold Summary

**One-liner:** Wave 0 TDD RED scaffold with 8 failing tests locking the contract for `quirk/qramm/evidence_bridge.py` before implementation.

## What Was Built

Created `tests/test_qramm_evidence_bridge.py` — the Wave 0 RED test file for Phase 53. This file defines the full API contract that Plans 02 and 03 must satisfy.

### Test Functions (8 total)

| Test | Requirement | Purpose |
|------|-------------|---------|
| `test_bridge_populates_on_session_create` | QRAMM-12 | POST /api/qramm/sessions triggers bridge; 30 CVI rows get suggested_answer |
| `test_bridge_skips_when_no_scan_data` | QRAMM-12 | Zero endpoints → 30 blank CVI rows, no suggested_answer |
| `test_no_risk_engine_import` | QRAMM-12 | evidence_bridge.py must not import risk_engine (isolation gate) |
| `test_rc4_scan_lower_score_than_aes256` | QRAMM-13 | RC4-HMAC scan → CVI 1.2 suggested=1; AES-256 scan → suggested=4 |
| `test_unconfirmed_excluded_from_score` | QRAMM-13 | suggested_answer set but answer_value NULL → score excludes row |
| `test_confirmed_included_in_score` | QRAMM-13 | Writing answer_value to suggested row flips it into score |
| `test_confirmed_at_auto_set` | QRAMM-13 | save_answers auto-sets confirmed_at when answer_value written to suggested row |
| `test_badge_signal_data_model` | QRAMM-14 | Badge visible iff suggested_answer NOT NULL AND answer_value NULL |

### Shared Helpers

- `_make_bridge_db()` — UUID-named in-memory SQLite engine with all Base.metadata tables; returns sessionmaker
- `_make_bridge_client()` — FastAPI TestClient with DB override (mirrors test_qramm_router pattern)
- `_seed_endpoints(db, scenario)` — Seeds CryptoEndpoint rows for scenarios: `rc4_heavy`, `aes256_only`, `mixed`, `empty`

### RED State Verification

```
collected 8 items

FAILED tests/test_qramm_evidence_bridge.py::test_bridge_populates_on_session_create
ModuleNotFoundError: No module named 'quirk.qramm.evidence_bridge'
```

All 8 tests fail with `ModuleNotFoundError` on `quirk.qramm.evidence_bridge` — confirmed RED state.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `9e58315` | test(53-01): add RED scaffold — 8 QRAMM evidence bridge tests |

## Deviations from Plan

None — plan executed exactly as written. Test file written verbatim from plan spec.

## Known Stubs

None — this plan only creates a test file. No implementation stubs.

## Threat Flags

No new attack surface introduced. Tests use isolated in-memory SQLite, no network or filesystem exposure.

## Self-Check

- [x] `tests/test_qramm_evidence_bridge.py` exists
- [x] 8 test functions present
- [x] All 8 named tests present
- [x] `_make_bridge_db` helper present
- [x] `_seed_endpoints` helper present
- [x] No `datetime.utcnow()` usage
- [x] Passes `py_compile`
- [x] RED state confirmed — `ModuleNotFoundError: No module named 'quirk.qramm.evidence_bridge'`
- [x] Commit `9e58315` exists
