---
gsd_state_version: 1.0
milestone: v5.3
milestone_name: Adoption & Integration Surface
status: Awaiting next milestone
stopped_at: Completed 104-02-PLAN.md
last_updated: "2026-05-25T13:35:45.115Z"
last_activity: 2026-05-25 — Milestone v5.3 completed and archived
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 20
  completed_plans: 20
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-24)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** Phase 105 — servicenow-ticketing

## Current Position

Phase: Milestone v5.3 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-05-25 — Milestone v5.3 completed and archived

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v5.3 not started)
- Prior milestone (v5.2): 12 plans across 4 phases

*Updated after each plan completion*

## Accumulated Context

### Decisions (pre-locked at roadmap)

- v5.3-D-01: Phase 101 is the unambiguous anchor — all seven integration security pitfalls (SSRF, secret leakage, optional-extra import trap, delivery isolation, notification storm, exfiltration whitelist, route-coverage gap) must be addressed HERE before any other integration phase begins
- v5.3-D-02: ISEC primitives ship in Phase 101 alongside NOTIFY, not as a separate phase — they are prerequisites for every downstream integration; splitting would require retrofitting and is explicitly called out as high-risk by research
- v5.3-D-03: TRANS-04 (CLI score-source tax) folds into Phase 102 alongside AUTH — it is small, orthogonal, and avoids its own phase; groups naturally with the dashboard polish work
- v5.3-D-04: SIEM (Phase 103) before Ticketing (Phase 104/105) — stdlib-only, zero dep risk, validates the send_findings_export pattern before Jira/ServiceNow add higher-complexity dedup logic
- v5.3-D-05: Ticketing is split across two phases (104 Jira + 105 ServiceNow) — TICKET-01..04 requires both backends plus shared abstraction; keeping both in one phase risks >5 plans; Phase 104 builds the TicketingChannel ABC + Jira backend + dedup; Phase 105 adds ServiceNow as the second backend reusing the abstraction
- v5.3-D-06: ServiceNow uses stdlib urllib Table API — no new pip dep beyond [tickets] extra; jira>=3.10.5 stays the only [tickets] extra dep; ServiceNow access pattern is raw HTTP, not a client library
- v5.3-D-07: Global notification config only (no per-schedule overrides in v5.3) — per-schedule routing requires a scheduled_scans schema change; global config ships first per research recommendation; per-schedule is v5.3.x

### Pending Todos

- Phase 101: Confirm exact line number of `_dispatch_schedule()` seam in scheduler_cmd.py before planning (research cites line 162 post-db.commit)
- Phase 101: Define `integration_deliveries` table schema at plan time (minimum: scan_id, finding_hash, destination, status, attempted_at, error_summary)
- Phase 103: Verify Splunk HEC raw vs. event endpoint choice at plan time (research recommendation: event endpoint for <=hundreds of findings)
- Phase 104: Verify Jira Cloud REST v3 JQL label-filter syntax and create_issue() field map at plan time (research flags this as needing plan-time research)

### Blockers

None.

## Deferred Items

Carried forward from v5.2 close and prior milestones:

| Category | Item | Status |
|----------|------|--------|
| verification (88) | CLI markdown report — Score Decomposition table visual render | deferred — code 5/5 verified |
| verification (88) | HTML report — Score Decomposition table visual render in browser | deferred — Jinja2 context wired |
| verification (88) | PDF report — Score Decomposition table (Playwright) | deferred — needs running server |
| verification (89) | kerberos `identity_weak_etype_count` > 0 | deferred — needs `[identity]`/impacket + live KDC |
| human-UAT (93) | getpass TTY prompt + live PDF export | deferred — TTY-gated |
| human-UAT (95) | live ldaps code-signing scan | deferred — needs ldaps lab |
| human-UAT (96) | TTY CONFIRM gate + non-TTY abort + live alg-confusion vs fuzz-target | deferred — TTY/environment-gated |

Acknowledged and deferred at v5.3 milestone close (2026-05-25) — all are live-endpoint deliveries (network sends are unit-tested with mocked transports); tracked per-phase in `*-HUMAN-UAT.md`:

| Category | Item | Status |
|----------|------|--------|
| human-UAT (101) | Slack / email / generic-webhook live delivery + end-to-end scheduler dispatch (4 scenarios) | deferred — needs live Slack/SMTP/webhook endpoints |
| human-UAT (102) | Login form render, wrong/correct token flow, Sign out, mid-session 401 logout, auth-disabled passthrough, live token CLI (7 scenarios) | deferred — needs running dashboard in a browser |
| human-UAT (103) | Live syslog/CEF delivery to a real SIEM + after-scan SIEM hook (2 scenarios) | deferred — needs a syslog-ingesting platform |
| human-UAT (104) | Live Jira issue creation + dedup, missing-extra skip, self-hosted token_auth (4 scenarios) | deferred — needs a real Jira instance |
| human-UAT (105) | Live ServiceNow incident creation + work_notes dedup (2 scenarios) | deferred — needs a real ServiceNow instance |
| tech-debt (105) | Extract duplicated `_NoRedirectHandler` (webhook.py + servicenow.py) to `quirk/util/no_redirect.py` | LOW — design-documented (T-105-04), no runtime impact |

## Session Continuity

Last session: 2026-05-25T13:09:56.616Z
Stopped at: Completed 104-02-PLAN.md
Resume file: None
Next: `/gsd:plan-phase 101`

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
