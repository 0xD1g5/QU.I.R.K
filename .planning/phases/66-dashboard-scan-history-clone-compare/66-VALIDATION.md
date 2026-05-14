---
phase: 66
slug: dashboard-scan-history-clone-compare
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 66 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (Python)** | pytest |
| **Config file** | `pytest.ini` / `pyproject.toml` (existing) |
| **Quick run command** | `python -m pytest tests/test_dashboard_scan_history.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q && cd src/dashboard && npx vitest run` |
| **Estimated runtime** | ~30s (Python) + ~15s (Vitest) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_dashboard_scan_history.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q && cd src/dashboard && npx vitest run`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| list_scans schema | 01 | 1 | UI-HIST-01 | — | N/A | integration | `pytest tests/test_dashboard_scan_history.py::test_list_scans_schema -x` | ❌ W0 | ⬜ pending |
| list_scans no limit | 01 | 1 | UI-HIST-01 | — | N/A | integration | `pytest tests/test_dashboard_scan_history.py::test_list_scans_no_limit -x` | ❌ W0 | ⬜ pending |
| clone data recovery | 01 | 1 | UI-HIST-01 | — | N/A | unit | `pytest tests/test_dashboard_scan_history.py::test_clone_data_recovery -x` | ❌ W0 | ⬜ pending |
| clone reconstruction | 01 | 1 | UI-HIST-01 | — | N/A | unit | `pytest tests/test_dashboard_scan_history.py::test_clone_reconstruction -x` | ❌ W0 | ⬜ pending |
| compare schema | 02 | 2 | UI-HIST-02 | T-66-01 | `/api/compare` returns 401 without auth | integration | `pytest tests/test_dashboard_scan_history.py::test_compare_schema -x` | ❌ W0 | ⬜ pending |
| compare self-check 400 | 02 | 2 | UI-HIST-02 | T-66-02 | `a == b` returns 400 | integration | `pytest tests/test_dashboard_scan_history.py::test_compare_self -x` | ❌ W0 | ⬜ pending |
| compare score delta | 02 | 2 | UI-HIST-02 | — | N/A | unit | `pytest tests/test_dashboard_scan_history.py::test_compare_score_delta -x` | ❌ W0 | ⬜ pending |
| compare finding diff | 02 | 2 | UI-HIST-02 | — | N/A | unit | `pytest tests/test_dashboard_scan_history.py::test_compare_finding_diff -x` | ❌ W0 | ⬜ pending |
| compare endpoint diff | 02 | 2 | UI-HIST-02 | — | N/A | unit | `pytest tests/test_dashboard_scan_history.py::test_compare_endpoint_diff -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard_scan_history.py` — stubs for all UI-HIST-01 and UI-HIST-02 test cases above; uses `dashboard_client` fixture from `conftest.py`; seeds `CryptoEndpoint` + `ScanJob` rows using shared-cache SQLite pattern from `test_dashboard_trends.py`

*No JS test gaps — `useScanList` is covered by integration tests; `useCompareData` follows the same cancellation pattern verified in Phase 62.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/scans` page renders history table with checkboxes and Clone buttons | UI-HIST-01 | React UI visual | Start dev server, navigate to `/scans`, verify table loads with date/target/profile/score/finding columns |
| Checkbox radio-window: 3rd check unchecks oldest | UI-HIST-01 | React checkbox state | On `/scans` with ≥3 scans, check A, B, C — verify A is unchecked |
| Clone button pre-fills `/scan/new` correctly | UI-HIST-01 | Form pre-fill state | Click Clone on a dashboard-launched scan; verify target/profile/calibration fields populated with no amber notice |
| Clone of CLI scan shows amber notice | UI-HIST-01 | Amber notice visibility | Click Clone on a CLI-launched scan; verify amber notice appears above Targets field |
| `/compare` page renders score header + 3 tabs | UI-HIST-02 | React UI visual | Navigate to `/compare?a=...&b=...`; verify score delta header, Findings/Subscores/Endpoints tabs |
| Compare URL is bookmarkable | UI-HIST-02 | Browser navigation | Copy `/compare?a=...&b=...` URL; paste in new tab; verify page loads correctly |

---

## Threat Model

| ID | Pattern | STRIDE | Mitigation |
|----|---------|--------|------------|
| T-66-01 | Unauthenticated history/compare access | Information Disclosure | `require_auth` at router level (scan.py line 34) — no per-route annotation needed |
| T-66-02 | `scan_id` injection (malformed ISO timestamp) | Tampering | `datetime.fromisoformat()` validation; raises 400 on parse failure |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
