---
phase: 105
slug: servicenow-ticketing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-25
---

# Phase 105 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/conftest.py (QUIRK_DB_PATH fixture) |
| **Quick run command** | `python -m pytest tests/test_ticketing_servicenow.py tests/test_ticketing_base.py tests/test_ticket_cmd.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~30s targeted |

---

## Sampling Rate

- **After every task commit:** Run the targeted quick command for the touched module
- **After every plan wave:** Run the phase's test files
- **Before `/gsd:verify-work`:** Full suite green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*Populated by gsd-planner during planning.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | — | — | — | — | — | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ticketing_servicenow.py` — TICKET-02 ServiceNowChannel (mocked urllib): POST create on first run returns sys_id; GET sysparm_query=correlation_id dedup → PATCH work_notes on second run (no duplicate); correlation_id carries fingerprint; creds (Basic auth) never logged; http:// instance_url rejected; identical fingerprint to Jira
- [ ] (reuse) `tests/test_ticketing_base.py` — confirms ServiceNowChannel satisfies the ABC contract with zero base.py changes

*Confirmed during planning against existing pytest infrastructure; mirrors Phase 104 mocked-client tests + Phase 103 urllib mocking.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live ServiceNow incident creation + dedup | TICKET-02 | Requires a real ServiceNow instance + credentials | Configure [ticketing].servicenow, run `quirk ticket create --backend servicenow`, confirm one incident per finding with QRAMM evidence + correlation_id; re-run, confirm work_notes appended instead of duplicate incidents |

*ServiceNow Table API is unit-tested with mocked urllib; live incident creation is human-UAT.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
