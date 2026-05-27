---
phase: 115
slug: live-uat-stabilization-lab-testability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-27
---

# Phase 115 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml / pytest.ini |
| **Quick run command** | `python -m pytest tests/ -k "enroll or scheduler or missing_extra or phantom or cmvp" -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~60–120 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (planner to fill) | — | — | STAB-01 | — | idempotent enroll, no token churn | unit | `pytest tests/ -k enroll -q` | ❌ W0 | ⬜ pending |
| (planner to fill) | — | — | STAB-03 | — | no --target/--output to run_scan | unit | `pytest tests/test_scheduler_posix_fixes.py -q` | ✅ | ⬜ pending |
| (planner to fill) | — | — | STAB-04 | — | no scanned_at=None/port-0 phantom rows | unit | `pytest tests/ -k "missing_extra or phantom" -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Enroll idempotency tests (STAB-01) — new or extend existing console/sensor enroll tests
- [ ] Phantom-row exclusion test (STAB-04) — assert merged output has zero scanned_at=None/port-0 endpoints
- [ ] STAB-03 regression test in `tests/test_scheduler_posix_fixes.py` (existing class — SENSOR-05 home)
- [ ] STAB-02 packaging assertion (cmvp_cache.json reachable via importlib.resources)

*Planner finalizes exact files/fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Lab re-runnable without `down -v` | STAB-01 | Needs full Docker distributed lab | Run `lab.sh distributed e2e` twice without teardown; second run succeeds |
| Weak-TLS per-segment filter end-to-end | LAB-01 | Needs Docker distributed lab | `lab.sh distributed e2e` exercises Test 7 against the new segment-b weak-TLS target |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
