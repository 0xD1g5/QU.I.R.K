---
phase: 104
slug: jira-ticketing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-25
---

# Phase 104 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/conftest.py (QUIRK_DB_PATH fixture) |
| **Quick run command** | `python -m pytest tests/test_ticketing_base.py tests/test_ticketing_jira.py tests/test_ticket_cmd.py tests/test_install_all_includes_tickets.py -q` |
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

- [ ] `tests/test_ticketing_base.py` — TICKET-04 TicketingChannel ABC contract; fingerprint = SHA256(host:port::title) stability; shared dedup orchestration; integration_deliveries audit
- [ ] `tests/test_ticketing_jira.py` — TICKET-01/03 Jira create_issue (mocked jira lib) once on first run; JQL label search + rediscovery comment on second run; creds never logged; missing-[tickets] graceful skip
- [ ] `tests/test_ticket_cmd.py` — `quirk ticket create` reads findings json, one issue per finding, failure isolation
- [ ] `tests/test_install_all_includes_tickets.py` — [tickets] joins [all] CI guard (jira in resolved set)

*Confirmed during planning against existing pytest infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Jira issue creation + dedup | TICKET-01/03 | Requires a real Jira Cloud/Server instance + API token | Configure [ticketing], run `quirk ticket create`, confirm one issue per finding with QRAMM evidence; re-run, confirm rediscovery comment instead of duplicates |

*Jira API is unit-tested with a mocked client; live issue creation is human-UAT.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
