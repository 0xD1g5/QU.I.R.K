---
phase: 34
slug: motion-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

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
| TBD | TBD | TBD | MOTION-01..04 | — | counter ticks lower data_in_motion subscore | unit | `pytest tests/test_motion_scoring.py -q` | ❌ W0 | ⬜ pending |

*Planner fills exact rows during PLAN.md write — one row per task with motion_ counter or scoring_ assertion.*

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
