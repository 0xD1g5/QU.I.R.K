---
phase: 54
slug: qramm-assessment-ui-scorecard
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-07
---

# Phase 54 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `pytest.ini` / `vite.config.ts` |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 54-01-01 | 01 | 0 | QRAMM-08 | — | N/A | unit | `python -m pytest tests/test_qramm_profile.py -x -q` | ❌ W0 | ⬜ pending |
| 54-01-02 | 01 | 0 | QRAMM-09 | — | evidence_note column present | unit | `python -m pytest tests/test_qramm_answer.py -x -q` | ❌ W0 | ⬜ pending |
| 54-02-01 | 02 | 1 | QRAMM-08 | — | Profile form stores qramm_profiles row | integration | `python -m pytest tests/test_qramm_api.py::test_create_profile -x -q` | ❌ W0 | ⬜ pending |
| 54-02-02 | 02 | 1 | QRAMM-09 | — | Draft endpoint persists answer + evidence_note | integration | `python -m pytest tests/test_qramm_api.py::test_draft_answer -x -q` | ❌ W0 | ⬜ pending |
| 54-03-01 | 03 | 1 | QRAMM-10 | — | Answers restored on page reload | integration | `python -m pytest tests/test_qramm_api.py::test_list_sessions -x -q` | ❌ W0 | ⬜ pending |
| 54-04-01 | 04 | 2 | QRAMM-11 | — | Scorecard returns dimension scores | integration | `python -m pytest tests/test_qramm_scoring.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Plan 01 Task 2 creates the test coverage before implementation proceeds:

- [ ] `tests/test_qramm_answer.py` — evidence_note column migration + round-trip (Plan 01 Task 1)
- [ ] `tests/test_qramm_router.py` additions — `test_create_profile`, `test_create_profile_multiplier_varies`, `test_list_sessions`, `test_draft_answer`, `test_get_answers` (Plan 01 Task 2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RadarChart renders correctly with 4 axes | QRAMM-11 | Visual chart output | Start dev server, open scorecard, verify 4 labeled axes |
| Dimension tab switching (CVI→SGRM→DPE→ITR) | QRAMM-09 | UI interaction | Manually navigate all 4 tabs, confirm questions change |
| Debounce autosave indicator | QRAMM-10 | Timing-dependent | Enter answer, watch for save indicator within 1s |
| Toast error on network failure | QRAMM-09 | Network condition | Block /api/qramm/assessment/draft, verify toast appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
