---
phase: 9
slug: scoring-consolidation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -x -q 2>&1 | tail -5` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q 2>&1 | tail -5`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 0 | SC-01 | unit | `python -m pytest tests/test_scoring_consolidation.py -x -q` | ❌ W0 | ⬜ pending |
| 9-01-02 | 01 | 1 | SC-02 | unit | `python -m pytest tests/test_scoring_consolidation.py::test_score_matches -x -q` | ❌ W0 | ⬜ pending |
| 9-01-03 | 01 | 1 | SC-03 | unit | `python -m pytest tests/test_scoring_consolidation.py::test_roadmap_matches -x -q` | ❌ W0 | ⬜ pending |
| 9-02-01 | 02 | 1 | SC-04 | unit | `python -m pytest tests/test_scoring_consolidation.py::test_profile_weights -x -q` | ❌ W0 | ⬜ pending |
| 9-02-02 | 02 | 1 | SC-05 | unit | `python -m pytest tests/test_scoring_consolidation.py::test_calibration_overrides -x -q` | ❌ W0 | ⬜ pending |
| 9-03-01 | 03 | 2 | SC-03 | integration | `python -m pytest tests/test_scoring_consolidation.py::test_deprecated_aliases -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scoring_consolidation.py` — stubs for SC-01 through SC-05
- [ ] `tests/conftest.py` — shared fixtures for intelligence layer and executive summary

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Executive summary score matches HTML report visually | SC-01 | HTML rendering requires visual inspection | Run scan, open HTML report, compare score to executive summary markdown |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
