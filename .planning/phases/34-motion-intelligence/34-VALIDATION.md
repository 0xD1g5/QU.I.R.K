---
phase: 34
slug: motion-intelligence
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
updated: 2026-04-29
---

<!-- Re-validated 2026-04-29 by Phase 37 Plan 37-04 (D-05): tests/test_motion_scoring.py exists with 15 tests, all GREEN under `python -m pytest`. Direct `pytest` invocation fails with ModuleNotFoundError due to PYTHONPATH; `python -m pytest` is the project standard. -->


# Phase 34 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml / pytest.ini (existing) |
| **Quick run command** | `pytest tests/test_motion_scoring.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds (motion file) / ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_motion_scoring.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 34-01-01 | 01 | 1 | MOTION-01..04 | — | motion_ counters present in evidence summary even with zero endpoints | unit | `python -m pytest tests/test_motion_scoring.py::test_motion_keys_present_in_summary -q` | ✅ | ✅ green |
| 34-01-02 | 01 | 1 | MOTION-01 | — | email weak-cipher counter increments | unit | `python -m pytest tests/test_motion_scoring.py::test_motion_email_weak_cipher_count -q` | ✅ | ✅ green |
| 34-02-01 | 02 | 2 | MOTION-02 | — | score weights expose motion values | unit | `python -m pytest tests/test_motion_scoring.py::test_score_weights_motion_values -q` | ✅ | ✅ green |
| 34-02-02 | 02 | 2 | MOTION-02 | — | profile multipliers apply to motion | unit | `python -m pytest tests/test_motion_scoring.py::test_profile_multipliers_motion -q` | ✅ | ✅ green |
| 34-02-03 | 02 | 2 | MOTION-02 | — | data_in_motion subscore present | unit | `python -m pytest tests/test_motion_scoring.py::test_subscores_includes_data_in_motion -q` | ✅ | ✅ green |
| 34-02-04 | 02 | 2 | MOTION-02 | — | findings lower the motion subscore | unit | `python -m pytest tests/test_motion_scoring.py::test_motion_subscore_lowers_with_findings -q` | ✅ | ✅ green |
| 34-03-01 | 03 | 3 | MOTION-03 | — | top_drivers surfaces motion drivers | unit | `python -m pytest tests/test_motion_scoring.py::test_top_drivers_surfaces_motion -q` | ✅ | ✅ green |
| 34-03-02 | 03 | 3 | MOTION-04 (D-12) | — | legacy evidence without motion keys preserves full credit | unit | `python -m pytest tests/test_motion_scoring.py::test_legacy_evidence_no_motion_keys_full_credit -q` | ✅ | ✅ green |
| 34-03-03 | 03 | 3 | MOTION-02 | — | strict profile increases motion penalty | unit | `python -m pytest tests/test_motion_scoring.py::test_profile_strict_increases_motion_penalty -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_motion_scoring.py` — created (mirrors `tests/test_dar_storage_scoring.py`)
- [ ] No new fixtures required — reuse `MagicMock`/`_Ep` idioms from existing scoring tests
- [ ] No new framework install — pytest already in project

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Legacy scan compatibility | D-12 | Cannot synthesize a "pre-Phase-34 scan" file in pytest cleanly | Load a saved scan from `quirk-output/` predating commit 72f20d7; assert `compute_readiness_score()` accepts it without KeyError and returns `data_in_motion` (legacy → 25/cap or relative-baseline value) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — `tests/test_motion_scoring.py` created
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-29 (re-validated by Phase 37 Plan 37-04)
