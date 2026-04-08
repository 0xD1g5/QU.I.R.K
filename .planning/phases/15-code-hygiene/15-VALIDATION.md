---
phase: 15
slug: code-hygiene
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_hygiene.py -x -q` |
| **Full suite command** | `python -m pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_hygiene.py -x -q`
- **After every plan wave:** Run `python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | HYGN-01/02/03/04 | unit | `python -m pytest tests/test_hygiene.py -x -q` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | HYGN-01 | unit | `python -m pytest tests/test_hygiene.py::test_connectors_stub_absent -x -q` | ✅ W0 | ⬜ pending |
| 15-02-02 | 02 | 1 | HYGN-02 | unit | `python -m pytest tests/test_hygiene.py::test_cfg_scan_restored_on_exception -x -q` | ✅ W0 | ⬜ pending |
| 15-02-03 | 02 | 1 | HYGN-03 | unit | `python -m pytest tests/test_hygiene.py::test_scorecard_py_absent -x -q` | ✅ W0 | ⬜ pending |
| 15-02-04 | 02 | 1 | HYGN-04 | manual+grep | `grep -r "nyquist_compliant: false" .planning/phases/ \| wc -l` → 0 | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_hygiene.py` — RED stubs for HYGN-01, HYGN-02, HYGN-03, HYGN-04

*Existing infrastructure covers test runner; only new test file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VALIDATION.md files reflect true phase status | HYGN-04 | File content audit across 13 files | `grep -r "nyquist_compliant" .planning/phases/*/\*-VALIDATION.md` must show `true` for all completed phases |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
