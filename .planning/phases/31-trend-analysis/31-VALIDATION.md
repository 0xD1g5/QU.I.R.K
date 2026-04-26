---
phase: 31
slug: trend-analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-26
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + Vitest (frontend) |
| **Config file** | `pytest.ini` / `src/dashboard/vitest.config.ts` |
| **Quick run command** | `python -m pytest tests/test_intelligence_trends.py tests/test_dashboard_trends.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_intelligence_trends.py tests/test_dashboard_trends.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 0 | TREND-01 | — | N/A | unit | `python -m pytest tests/test_intelligence_trends.py -x -q` | ❌ W0 | ⬜ pending |
| 31-01-02 | 01 | 1 | TREND-01 | — | N/A | unit | `python -m pytest tests/test_intelligence_trends.py::test_score_delta_computed -x -q` | ✅ | ⬜ pending |
| 31-01-03 | 01 | 1 | TREND-02 | — | N/A | unit | `python -m pytest tests/test_intelligence_trends.py::test_new_findings_counted -x -q` | ✅ | ⬜ pending |
| 31-01-04 | 01 | 1 | TREND-03 | — | N/A | unit | `python -m pytest tests/test_intelligence_trends.py::test_resolved_findings_counted -x -q` | ✅ | ⬜ pending |
| 31-02-01 | 02 | 2 | TREND-04 | — | N/A | integration | `python -m pytest tests/test_dashboard_trends.py -x -q` | ❌ W0 | ⬜ pending |
| 31-03-01 | 03 | 3 | TREND-04 | — | N/A | integration | `python -m pytest tests/test_dashboard_trends.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_intelligence_trends.py` — 10 unit test stubs for TREND-01, TREND-02, TREND-03
- [ ] `tests/test_dashboard_trends.py` — 2 integration test stubs for TREND-04 using `dashboard_client` fixture from `conftest.py`

*Existing `conftest.py` with `dashboard_client` fixture covers shared infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Trends tab visible in dashboard nav | TREND-04 | Browser UI | Load dashboard, confirm "Trends" tab appears in sidebar, click and verify score delta + new/resolved counts render |
| NULL scanned_at rows excluded | TREND-01 | Requires v4.2-era data | Insert a row with NULL scanned_at, run trend report, confirm it does not appear as a session |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
