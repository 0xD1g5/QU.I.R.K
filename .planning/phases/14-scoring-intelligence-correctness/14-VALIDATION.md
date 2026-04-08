---
phase: 14
slug: scoring-intelligence-correctness
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` or `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_scoring_correctness.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_scoring_correctness.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | SCORE-01 | unit | `python -m pytest tests/test_scoring_correctness.py::test_strict_profile_higher_than_lenient -v` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | SCORE-02 | unit | `python -m pytest tests/test_scoring_correctness.py::test_validate_run_no_delta_failure -v` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | SCORE-03 | unit | `python -m pytest tests/test_scoring_correctness.py::test_migration_advisor_tls_recommendations -v` | ❌ W0 | ⬜ pending |
| 14-01-04 | 01 | 1 | SCORE-04 | unit | `python -m pytest tests/test_scoring_correctness.py::test_dashboard_profile_propagation -v` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 2 | SCORE-01 | unit | `python -m pytest tests/test_scoring_correctness.py::test_strict_profile_higher_than_lenient -v` | ✅ | ⬜ pending |
| 14-02-02 | 02 | 2 | SCORE-02 | unit | `python -m pytest tests/test_scoring_correctness.py::test_validate_run_no_delta_failure -v` | ✅ | ⬜ pending |
| 14-02-03 | 02 | 2 | SCORE-03 | unit | `python -m pytest tests/test_scoring_correctness.py::test_migration_advisor_tls_recommendations -v` | ✅ | ⬜ pending |
| 14-02-04 | 02 | 2 | SCORE-04 | unit | `python -m pytest tests/test_scoring_correctness.py::test_dashboard_profile_propagation -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scoring_correctness.py` — new test file with RED stubs for SCORE-01 through SCORE-04

*Existing infrastructure covers test runner and fixtures. Only the new test file needs creation in Wave 0 (Plan 1).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard score matches CLI score for same scan with non-default profile | SCORE-04 | Requires running a real scan + dashboard + comparing outputs | Run scan with `profile: strict`, open dashboard, compare score in executive summary vs dashboard detail |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
