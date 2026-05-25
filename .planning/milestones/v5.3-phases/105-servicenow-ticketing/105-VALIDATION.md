---
phase: 105
slug: servicenow-ticketing
status: ready
nyquist_compliant: true
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

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 105-01-T0 | 105-01 | 1 | TICKET-02 | T-105-01..06 | Wave 0 RED scaffold defines all behaviors before impl | unit | `python -m pytest tests/test_ticketing_servicenow.py --collect-only -q` | ❌ W0 (creates) | ⬜ pending |
| 105-01-T1 | 105-01 | 1 | TICKET-02 | T-105-02 | http:// instance_url rejected at parse; env-var-name creds only | unit | `python -m pytest tests/test_ticketing_servicenow.py -k "instance_url or env_fields or valid_config" -q` | ✅ (T0) | ⬜ pending |
| 105-01-T2 | 105-01 | 1 | TICKET-02 | T-105-01,03,04,05 | SSRF guard + _NoRedirectHandler + creds scrubbed + dedup; sys_id not number; PATCH not POST | unit | `python -m pytest tests/test_ticketing_servicenow.py -q` | ✅ (T0) | ⬜ pending |
| 105-02-T1 | 105-02 | 2 | TICKET-02 | T-105-07,09 | --backend choices set; neutral extra-gate; backend-conditional dispatch | unit | `python -m compileall quirk/cli/ticket_cmd.py` | n/a | ⬜ pending |
| 105-02-T2 | 105-02 | 2 | TICKET-02 | T-105-07,08 | servicenow routes to ServiceNowChannel; default jira; missing config exits 2 | unit | `python -m pytest tests/test_ticket_cmd.py -q` | ✅ (T1) | ⬜ pending |
| 105-03-T1 | 105-03 | 3 | TICKET-02 | T-105-10,11 | docs: https-only, env-var-name creds, --backend servicenow | docs | `grep -qi 'backend servicenow' docs/configuration.md` | ✅ | ⬜ pending |
| 105-03-T2 | 105-03 | 3 | TICKET-02 | — | Series 105 + Obsidian note + vault sync + commit | docs | `grep -q "Series 105" docs/UAT-SERIES.md` | ✅ | ⬜ pending |
| (gate) | all | — | TICKET-04 | — | ZERO changes to base.py/jira.py | structural | `git diff --quiet quirk/ticketing/base.py quirk/ticketing/jira.py` | ✅ (existing) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ticketing_servicenow.py` — TICKET-02 ServiceNowChannel (mocked urllib): POST create on first run returns sys_id; GET sysparm_query=correlation_id dedup → PATCH work_notes on second run (no duplicate); correlation_id carries fingerprint; creds (Basic auth) never logged; http:// instance_url rejected; SSRF guard; identical fingerprint to Jira. Created in 105-01 Task 0.
- [ ] (reuse) `tests/test_ticketing_base.py` — confirms ServiceNowChannel satisfies the ABC contract with zero base.py changes
- [ ] (extend) `tests/test_ticket_cmd.py` — --backend servicenow dispatch + default-jira regression + missing-config exit-2. Created in 105-02 Task 2.

*Confirmed during planning against existing pytest infrastructure; mirrors Phase 104 mocked-client tests + Phase 103 urllib mocking.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live ServiceNow incident creation + dedup | TICKET-02 | Requires a real ServiceNow instance + credentials | Configure [ticketing].servicenow, run `quirk ticket create --backend servicenow`, confirm one incident per finding with QRAMM evidence + correlation_id; re-run, confirm work_notes appended instead of duplicate incidents |

*ServiceNow Table API is unit-tested with mocked urllib; live incident creation is human-UAT.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (planning)
