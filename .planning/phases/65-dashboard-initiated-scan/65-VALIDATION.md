---
phase: 65
slug: dashboard-initiated-scan
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-13
---

# Phase 65 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_jobs_api.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_jobs_api.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 65-01 | 01 | 1 | UI-SCAN-01 | POST /api/jobs creates scan_jobs row | unit | `pytest tests/test_jobs_api.py::test_post_job_creates_row -x` | ❌ W0 | ⬜ pending |
| 65-02 | 01 | 1 | UI-SCAN-01 | @file target returns 422 | unit | `pytest tests/test_jobs_api.py::test_post_job_rejects_file_path -x` | ❌ W0 | ⬜ pending |
| 65-03 | 01 | 1 | UI-SCAN-01 | empty targets returns 422 | unit | `pytest tests/test_jobs_api.py::test_post_job_empty_targets -x` | ❌ W0 | ⬜ pending |
| 65-04 | 01 | 1 | UI-SCAN-01 | POST requires auth | unit | `pytest tests/test_jobs_api.py::test_post_job_requires_auth -x` | ❌ W0 | ⬜ pending |
| 65-05 | 01 | 1 | UI-SCAN-01 | POST requires CSRF | unit | `pytest tests/test_jobs_api.py::test_post_job_requires_csrf -x` | ❌ W0 | ⬜ pending |
| 65-06 | 02 | 1 | UI-SCAN-02 | GET returns correct JobStatusResponse shape | unit | `pytest tests/test_jobs_api.py::test_get_job_status -x` | ❌ W0 | ⬜ pending |
| 65-07 | 02 | 1 | UI-SCAN-02 | GET returns 404 for unknown id | unit | `pytest tests/test_jobs_api.py::test_get_job_not_found -x` | ❌ W0 | ⬜ pending |
| 65-08 | 02 | 1 | UI-SCAN-02 | GET requires auth (no CSRF) | unit | `pytest tests/test_jobs_api.py::test_get_job_requires_auth -x` | ❌ W0 | ⬜ pending |
| 65-09 | 02 | 1 | UI-SCAN-02 | stage_index computed from current_stage | unit | `pytest tests/test_jobs_api.py::test_stage_index_computation -x` | ❌ W0 | ⬜ pending |
| 65-10 | 03 | 1 | UI-SCAN-03 | DELETE sends SIGTERM and sets cancelled | unit | `pytest tests/test_jobs_api.py::test_cancel_job -x` | ❌ W0 | ⬜ pending |
| 65-11 | 03 | 1 | UI-SCAN-03 | _recover_stale_jobs flips running→failed | unit | `pytest tests/test_jobs_api.py::test_stale_job_recovery -x` | ❌ W0 | ⬜ pending |
| 65-12 | 01 | 1 | All | POST/DELETE /api/jobs have require_auth | regression | `pytest tests/test_api_auth.py::test_all_mutating_routes_have_auth_dependency -x` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_jobs_api.py` — stubs for UI-SCAN-01, UI-SCAN-02, UI-SCAN-03 (11 test cases; reuse existing `dashboard_client` fixture from `conftest.py`)
- [ ] `tests/test_job_progress.py` — covers `update_job_stage()` no-op behavior when job not found

*Existing `tests/conftest.py` `dashboard_client` fixture is reusable — no new fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| /scan/new form renders correct fields in browser | UI-SCAN-01 | React UI rendering | Load dashboard, click "New Scan", verify 4 controls appear with correct defaults |
| Stage progress updates in real-time during scan | UI-SCAN-02 | Requires live subprocess | Submit form, observe stage indicator advancing through 7 stages |
| Post-completion navigation to results view | UI-SCAN-02 | End-to-end user flow | Let scan complete, verify auto-navigate to executive summary for new scan |
| Cancel button stops subprocess | UI-SCAN-03 | Requires live process | Click cancel during running scan, verify process terminates |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
