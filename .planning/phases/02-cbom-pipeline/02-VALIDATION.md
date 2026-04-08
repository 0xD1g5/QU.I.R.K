---
phase: 2
slug: cbom-pipeline
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-29
---

# Phase 2 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_cbom_builder.py tests/test_cbom_classifier.py -x -q` |
| **Full suite command** | `python -m pytest -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_cbom_builder.py tests/test_cbom_classifier.py -x -q`
- **After every plan wave:** Run `python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | CBOM-01 | unit | `python -m pytest tests/test_cbom_classifier.py -x -q` | ✅ | ✅ green |
| 2-01-02 | 01 | 1 | CBOM-02 | unit | `python -m pytest tests/test_cbom_builder.py -x -q` | ✅ | ✅ green |
| 2-02-01 | 02 | 2 | CBOM-01,02 | integration | `python -m pytest tests/test_cbom_builder.py tests/test_cbom_classifier.py -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- None — existing `tests/test_cbom_builder.py` and `tests/test_cbom_classifier.py` cover all phase requirements.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CycloneDX JSON validates against schema | CBOM-01 | Requires CycloneDX validator tool | Run scan, validate `cbom-*.cdx.json` with `cyclonedx validate` |
| CBOM XML file produced alongside JSON | CBOM-02 | File system check after scan | Run scan, confirm `cbom-*.cdx.xml` present in output directory |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

*Note: VALIDATION.md created retroactively during Phase 15 code hygiene. All Phase 2 tests have been passing GREEN since phase completion.*
