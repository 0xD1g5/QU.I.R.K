---
phase: 55
slug: qramm-compliance-mapping-view
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + Vitest (frontend) |
| **Config file** | `pytest.ini` / `src/dashboard/vite.config.ts` |
| **Quick run command** | `python -m pytest tests/test_qramm_staleness.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_qramm_staleness.py -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 55-01-01 | 01 | 1 | QRAMM-05 | — | N/A | unit | `python -m pytest tests/test_qramm_staleness.py -q` | ❌ W0 | ⬜ pending |
| 55-01-02 | 01 | 1 | QRAMM-06 | — | N/A | integration | `python -m pytest tests/test_qramm_staleness.py -q` | ❌ W0 | ⬜ pending |
| 55-02-01 | 02 | 1 | QRAMM-07 | — | No fully-compliant badge rendered | unit | `python -m pytest tests/ -q` | ✅ | ⬜ pending |
| 55-03-01 | 03 | 2 | QRAMM-15 | — | No coverage percentage above scanner ceiling | integration | `python -m pytest tests/ -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_qramm_staleness.py` — stubs for QRAMM-05, QRAMM-06 (staleness gate + env var override)

*Existing test infrastructure (pytest.ini, conftest.py) covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Compliance Map 6th tab renders table with 8 frameworks | QRAMM-15 | React UI — no headless test infrastructure in this phase | Start dev server, navigate to /qramm/assessment, click `[ Compliance Map ]` tab, confirm 8 framework rows visible |
| "Scanner-informed" / "Manual only" badges render correctly | QRAMM-15 | Visual badge variant inspection | Confirm CVI-mapped practices show default-variant badge; non-CVI practices show secondary-variant badge |
| No "fully compliant" badge rendered under any score | QRAMM-15 | Visual regression | Score a session at max values; confirm no green "fully compliant" chip appears anywhere in the tab |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
