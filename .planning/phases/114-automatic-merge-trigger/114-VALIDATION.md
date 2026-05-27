---
phase: 114
slug: automatic-merge-trigger
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-26
---

# Phase 114 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml / pytest.ini |
| **Quick run command** | `python -m pytest tests/ -k "auto_merge or sensor_push" -q` |
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
| (planner to fill) | — | — | AUTOMERGE-01/02/03 | — | safe_str audit, no token leak | unit | `python -m pytest tests/ -k auto_merge -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_auto_merge.py` — acceptance tests for AUTOMERGE-01/02/03 (the 6 scenarios in CONTEXT.md <specifics>)
- [ ] Reuse existing sensor-push / merge fixtures (temp DB, FastAPI TestClient)

*Planner finalizes the exact file/fixture set.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Distributed lab e2e auto-merge row | AUTOMERGE-01 | Needs full Docker distributed lab | `lab.sh distributed e2e` and confirm MergeRun before manual merge step |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
