---
phase: 8
slug: legacy-debt-cleanup
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-03
---

# Phase 8 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_validate.py tests/test_scoring_consolidation.py -x -q` |
| **Full suite command** | `python -m pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_validate.py tests/test_scoring_consolidation.py -x -q`
- **After every plan wave:** Run `python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 1 | DEBT-01 | unit | `python -m pytest tests/test_validate.py -x -q` | ✅ | ✅ green |
| 8-02-01 | 02 | 1 | DEBT-02 | unit | `python -m pytest tests/test_scoring_consolidation.py -x -q` | ✅ | ✅ green |
| 8-03-01 | 03 | 2 | DEBT-01,02 | integration | `python -m pytest tests/test_validate.py tests/test_scoring_consolidation.py -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- None — existing `tests/test_validate.py` and `tests/test_scoring_consolidation.py` cover all phase requirements.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No stale qcscan/ or QuRisk references in codebase | DEBT-01 | Full codebase grep required | Run `grep -r "qcscan\|QuRisk" --include="*.py" .` — expect no results |
| datetime.utcnow() removed from all modules | DEBT-02 | Codebase-wide search | Run `grep -r "utcnow" --include="*.py" .` — expect no results |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

*Note: VALIDATION.md created retroactively during Phase 15 code hygiene. All Phase 8 tests have been passing GREEN since phase completion.*
