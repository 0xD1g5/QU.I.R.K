---
phase: 11-dashboard-wiring-fixes
verified: 2026-04-04T13:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 11: Dashboard Wiring Fixes Verification Report

**Phase Goal:** Fix dashboard wiring bugs — close GAP-INT-01, GAP-INT-02, GAP-INT-03 so the default E2E dashboard flow works correctly
**Verified:** 2026-04-04T13:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                  | Status     | Evidence                                                                                              |
| --- | -------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------- |
| 1   | deps.py default db_path matches config_template.yaml value `./quirk.db`               | ✓ VERIFIED | Line 14 of deps.py: `os.environ.get("QUIRK_DB_PATH", "./quirk.db")`. config_template.yaml line 44: `db_path: "./quirk.db"` |
| 2   | server.py sets `QUIRK_SERVE_PORT` env var before `uvicorn.run()` so PDF exporter inherits the correct port | ✓ VERIFIED | Line 39 of server.py: `os.environ["QUIRK_SERVE_PORT"] = str(port)` placed before `uvicorn.run()` call on line 40 |
| 3   | SSH endpoints with ssh_audit_json produce CBOM components in the dashboard viewer     | ✓ VERIFIED | scan.py lines 203–223: full kex/key/enc/mac parsing block inside `_derive_cbom()` for loop           |
| 4   | SSH-only scans show algorithm data in CBOM tab (not empty list)                       | ✓ VERIFIED | Same SSH parsing block; test_derive_cbom_ssh_only_scan passes GREEN (confirmed via pytest run)        |
| 5   | Existing TLS/JWT/cloud CBOM derivation is unchanged                                   | ✓ VERIFIED | Full 199-test suite passes with zero regressions                                                      |
| 6   | Tests exist and pass for all three Phase 11 fixes                                     | ✓ VERIFIED | All 5 tests in test_dashboard_wiring.py pass GREEN                                                    |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact                                    | Expected                               | Status     | Details                                                                                    |
| ------------------------------------------- | -------------------------------------- | ---------- | ------------------------------------------------------------------------------------------ |
| `quirk/dashboard/api/deps.py`               | Corrected default db_path `./quirk.db` | ✓ VERIFIED | Line 14 confirmed. File is 38 lines, substantive, imported and used by get_db() dependency |
| `quirk/dashboard/server.py`                 | QUIRK_SERVE_PORT env var propagation   | ✓ VERIFIED | Line 39 confirmed. `os.environ["QUIRK_SERVE_PORT"] = str(port)` precedes uvicorn.run()    |
| `tests/test_dashboard_wiring.py`            | Unit tests for all three Phase 11 fixes | ✓ VERIFIED | 150 lines, 5 test functions, all GREEN via pytest                                          |
| `quirk/dashboard/api/routes/scan.py`        | SSH algorithm parsing in _derive_cbom() | ✓ VERIFIED | Lines 203–223: 22-line SSH block with kex/key/enc/mac section-to-type mapping              |

---

### Key Link Verification

| From                                            | To                                          | Via                                      | Status     | Details                                                                                     |
| ----------------------------------------------- | ------------------------------------------- | ---------------------------------------- | ---------- | ------------------------------------------------------------------------------------------- |
| `quirk/dashboard/api/deps.py`                   | `quirk/config_template.yaml`                | matching default db_path value           | ✓ WIRED    | Both use `./quirk.db`; deps.py line 14, config_template.yaml line 44                       |
| `quirk/dashboard/server.py`                     | `quirk/dashboard/api/routes/pdf.py`         | QUIRK_SERVE_PORT env var inheritance     | ✓ WIRED    | server.py line 39 sets env var; pdf.py line 45 reads `os.environ.get("QUIRK_SERVE_PORT", "8512")` |
| `quirk/dashboard/api/routes/scan.py::_derive_cbom()` | `quirk/cbom/builder.py::_extract_ssh_algorithms()` | mirrored SSH JSON parsing pattern | ✓ WIRED    | scan.py SSH block mirrors builder.py section loop; pattern `ssh_audit_json` confirmed at lines 204, 206 |
| `quirk/dashboard/api/routes/scan.py::_derive_cbom()` | `quirk/cbom/classifier.py`            | _qs_for_alg() classifies SSH algorithm names | ✓ WIRED | `_qs_for_alg()` inner function called for every SSH algorithm at line 215                   |

---

### Data-Flow Trace (Level 4)

| Artifact                                   | Data Variable | Source                          | Produces Real Data | Status      |
| ------------------------------------------ | ------------- | ------------------------------- | ------------------ | ----------- |
| `quirk/dashboard/api/routes/scan.py`       | `algo_map`    | `ep.ssh_audit_json` via json.loads | Yes — parses live endpoint data | ✓ FLOWING |
| `quirk/dashboard/api/deps.py`              | `db_path`     | env var or `./quirk.db` literal | Yes — resolves real filesystem path | ✓ FLOWING |
| `quirk/dashboard/server.py`                | `QUIRK_SERVE_PORT` | `str(port)` from function arg | Yes — reflects actual binding port | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior                                    | Command                                                                                                   | Result       | Status  |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------ | ------- |
| All 5 Phase 11 wiring tests pass            | `python3 -m pytest tests/test_dashboard_wiring.py -v -q`                                                 | 5 passed     | ✓ PASS  |
| No regressions in dashboard and gap tests   | `python3 -m pytest tests/test_dashboard_api.py tests/test_gap_closure.py -q`                             | 11 passed    | ✓ PASS  |
| Full suite green                            | `python3 -m pytest tests/ -q`                                                                             | 199 passed   | ✓ PASS  |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                 | Status      | Evidence                                                                                                   |
| ----------- | ----------- | --------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------- |
| UI-01       | Plan 01     | FastAPI API layer — scan job management, results API, serving scanner output | ✓ SATISFIED | deps.py default db_path fix ensures `/api/scan/latest` resolves the correct SQLite path for fresh installs |
| UI-03       | Plan 02     | Findings table, certificate inventory, CBOM viewer in dashboard             | ✓ SATISFIED | SSH algorithm parsing in `_derive_cbom()` populates CBOM viewer for SSH endpoints and SSH-only scans       |
| UI-04       | Plan 01     | HTML report export + PDF generation via Playwright headless                 | ✓ SATISFIED | QUIRK_SERVE_PORT env var set before uvicorn starts so PDF exporter targets the actual serving port         |

REQUIREMENTS.md coverage table (line 128–131) records UI-01, UI-03, UI-04 as Phase 11 / Complete. No orphaned requirements found — REQUIREMENTS.md line 144 confirms "36/36 v1 requirements mapped. No orphans."

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| —    | —    | None    | —        | —      |

No TODO/FIXME/PLACEHOLDER comments found. No stub return patterns (empty lists, null returns, console-only handlers) found in any of the four modified files.

Note: `test_derive_cbom_ssh_algorithms` and `test_derive_cbom_ssh_only_scan` contain comments referencing "RED state" from their Plan 01 creation. These are documentation comments only — both tests now pass GREEN. They are not functional stubs.

---

### Commit Verification

All three documented commits verified to exist in git history:

| Commit    | Message                                                         |
| --------- | --------------------------------------------------------------- |
| `884e314` | test(11-01): add failing tests for dashboard wiring fixes (RED) |
| `b387a48` | fix(11-01): close GAP-INT-01 and GAP-INT-02 dashboard wiring bugs |
| `e1f62d1` | feat(11-02): add SSH algorithm parsing branch to _derive_cbom() |

---

### Human Verification Required

None. All three gap closures (GAP-INT-01, GAP-INT-02, GAP-INT-03) are fully verifiable programmatically via unit tests and source inspection. No visual, real-time, or external service behavior is involved in this phase's scope.

---

### Gaps Summary

No gaps. All six observable truths verified, all four artifacts substantive and wired, all four key links confirmed, all three requirement IDs satisfied, full 199-test suite passes with zero regressions.

---

_Verified: 2026-04-04T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
