---
gsd_state_version: 1.0
milestone: v5.4
milestone_name: Distributed On-Prem Scanner Architecture
status: planning
last_updated: "2026-05-25"
last_activity: 2026-05-25
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-25)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours — now across every segment of a segmented enterprise network
**Current focus:** Phase 106 — Architecture Documentation (roadmap drafted; ready for planning)

## Current Position

Phase: 106 — Architecture Documentation
Plan: —
Status: Roadmap created; awaiting `/gsd:plan-phase 106`
Last activity: 2026-05-25 — Milestone v5.4 roadmap written (7 phases, 33 requirements, 100% coverage)

```
v5.4 Progress: [          ] 0/7 phases | 0% complete
```

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v5.4 not started)
- Prior milestone (v5.3): 20 plans across 5 phases
- Prior milestone (v5.2): 12 plans across 4 phases

*Updated after each plan completion*

## Accumulated Context

### Decisions (pre-locked at roadmap)

- v5.4-D-01: Phase 106 (Architecture Documentation) is the mandatory no-code gating anchor per HORIZON 999.58 and research convergence — no v5.4 code ships until the wire contract, data-model keying, PM decisions, and forbidden-additions list are written and reviewed
- v5.4-D-02: Unified scoring methodology is Option A (union of pushed endpoints through the existing `compute_readiness_score()` / `build_cbom()` engines unchanged) — committed; Option B (weighted average) deferred to v5.5 after real-consultant validation
- v5.4-D-03: Enrollment tokens are one-time-use (consumed on successful enrollment) — committed; time-windowed tokens deferred to v5.5
- v5.4-D-04: Windows v5.4 floor is committed (OS-agnostic wire contract + pip install + `windows-latest` CI smoke job); ceiling (full PyInstaller frozen EXE + Scheduled Task packaging) to be decided during Phase 106 arch-doc and recorded in ARCH-03
- v5.4-D-05: STAB-02 (`_NoRedirectHandler` extraction to `quirk/util/no_redirect.py`) ships in Phase 108 (SENSOR) as a prerequisite for the sensor push client — not deferred to Phase 112 stabilization tail
- v5.4-D-06: Store-and-forward spool uses file-per-payload directory (not SQLite) — bounded depth, retried on next push invocation
- v5.4-D-07: The merge trigger is manual (`quirk sensor merge`) for v5.4; automatic console-side poll when all sensors check in is deferred to v5.5
- v5.4-D-08: `sensor_id` must be `nullable=True` on `CryptoEndpoint` (NULL = implicit local sensor); existing single-host scans are unaffected — backward compatibility is non-negotiable
- v5.4-D-09: Scoring/CBOM/evidence engines (`scoring.py`, `evidence.py`, `cbom/builder.py`, `cbom/writer.py`) are NOT forked or modified; the merge pipeline re-runs them over the union of sensor endpoints
- v5.4-D-10: The Windows chaos lab cannot validate Windows sensor correctness (Linux containers only); Windows validation is owned exclusively by the `windows-latest` CI smoke job in Phase 108

### Pending Todos

- Phase 106: Resolve Windows packaging ceiling decision (in-v5.4 full PyInstaller/Scheduled-Task, or floor-only with v5.5 fast-follow) — output must be written into ARCH-03
- Phase 106: Nail `sensor_pushes` dedup table schema at arch-doc time (payload_id, sensor_id, received_at, TTL/cleanup policy) so Phase 107 can create it in the same migration pass
- Phase 107: Write migration regression test using a pre-v5.4 SQLite fixture before any ingestion code touches the schema
- Phase 108: Audit `scheduler_cmd.py:136` (relative path → `cfg.output_root`-anchored) and `:258-259` (SIGTERM → `sys.platform != 'win32'`-guarded) — exact line numbers from research, verify before planning
- Phase 109: Extend the `safe_str()` AST gate to cover `quirk/dashboard/api/routes/sensor.py` explicitly
- Phase 110: Review `cbom/builder.py` Pass 1 `algo_registry` dedup logic (line 461 per research) to determine exact change needed to include `sensor_id` in component identity hash — flag as explicit seam audit at plan time
- Phase 112: Verify `lab.sh` ALL_PROFILES sync after adding distributed profiles (per CLAUDE.md chaos-lab maintenance rule)

### Blockers

None.

## Deferred Items

Carried forward from v5.3 close (2026-05-25):

| Category | Item | Status |
|----------|------|--------|
| verification (88) | CLI markdown report — Score Decomposition table visual render | deferred — code 5/5 verified |
| verification (88) | HTML report — Score Decomposition table visual render in browser | deferred — Jinja2 context wired |
| verification (88) | PDF report — Score Decomposition table (Playwright) | deferred — needs running server |
| verification (89) | kerberos `identity_weak_etype_count` > 0 | deferred — needs `[identity]`/impacket + live KDC |
| human-UAT (93) | getpass TTY prompt + live PDF export | deferred — TTY-gated |
| human-UAT (95) | live ldaps code-signing scan | deferred — needs ldaps lab |
| human-UAT (96) | TTY CONFIRM gate + non-TTY abort + live alg-confusion vs fuzz-target | deferred — TTY/environment-gated |
| human-UAT (101) | Slack / email / generic-webhook live delivery + end-to-end scheduler dispatch (4 scenarios) | deferred — needs live Slack/SMTP/webhook endpoints |
| human-UAT (102) | Login form render, wrong/correct token flow, Sign out, mid-session 401 logout, auth-disabled passthrough, live token CLI (7 scenarios) | deferred — needs running dashboard in a browser |
| human-UAT (103) | Live syslog/CEF delivery to a real SIEM + after-scan SIEM hook (2 scenarios) | deferred — needs a syslog-ingesting platform |
| human-UAT (104) | Live Jira issue creation + dedup, missing-extra skip, self-hosted token_auth (4 scenarios) | deferred — needs a real Jira instance |
| human-UAT (105) | Live ServiceNow incident creation + work_notes dedup (2 scenarios) | deferred — needs a real ServiceNow instance |

## Session Continuity

Last session: 2026-05-25
Stopped at: Roadmap created for v5.4
Resume file: None
Next: `/gsd:plan-phase 106`

## Operator Next Steps

- Plan Phase 106 with `/gsd:plan-phase 106`
