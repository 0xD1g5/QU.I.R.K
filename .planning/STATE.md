---
gsd_state_version: 1.0
milestone: v4.5
milestone_name: Reliability & Gap Closure
status: planning
last_updated: "2026-04-29T12:34:56.764Z"
last_activity: 2026-04-29
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-26)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** v4.4 shipped — planning next milestone (`/gsd-new-milestone`)

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-29 — Milestone v4.5 started

## Phase Overview

| Phase | Slug | Complexity | Depends On |
|-------|------|------------|------------|
| 32 | email-scanner | L | Phase 31 |
| 33 | broker-scanner | L | Phase 31 (parallel to 32) |
| 34 | motion-intelligence | M | Phase 32, 33 |
| 35 | cbom-integration | M | Phase 32, 33 (parallel to 34) |
| 36 | dashboard-motion-tab | M | Phase 34, 35 |
| 37 | gap-closure-v4.4.0 | S | Phase 36 |

**Critical path:** 31 → 32/33 (parallel) → 34/35 (parallel) → 36 → 37

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v4.4)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|

## Accumulated Context

| Phase 32 P03 | 12 min | 2 tasks | 1 files |
| Phase 32 P04 | 22 | 2 tasks | 5 files |
| Phase 32 P06 | 30 min | 2 tasks | 1 files |
| Phase 32 P07 | 10min | 2 tasks | 4 files |
| Phase 32 P08 | ~3.5 minutes | 2 tasks | 3 files |
| Phase 35 P04 | 180 | 3 tasks | 4 files |

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Previous milestone (v4.3) key decisions carried forward:

- ISSUE-2 and ISSUE-3 patterns must be treated as structural requirements on every scanner phase — pyproject.toml diff is a required PLAN.md deliverable; session_start parameter is mandatory for all new scanners
- All new scanners must include [motion] extras group entry in pyproject.toml at plan time

Roadmap decisions (2026-04-27):

- Phase 32 and Phase 33 develop in parallel — no shared code dependencies between email_scanner.py and broker_scanner.py
- Phase 34 (Motion Intelligence) and Phase 35 (CBOM Integration) develop in parallel once 32+33 are done
- Chaos lab port allocation: email profile uses 30xxx range, broker profile uses 26xxx/29xxx/25xxx ranges (no conflicts with existing profiles)
- KAFKA-04 (AdminClient enrichment) is optional/graceful-degradation only — not required for Phase 33 success criteria; TLS probe via sslyze is the required path
- OpenSSL 3.x TLS 1.0/1.1 caveat applies to both email and broker chaos labs — target RSA key-exchange and weak cipher as primary detectable findings at TLS 1.2
- [Phase ?]: Phase 32 Plan 03: email_scanner.py uses module-level sslyze stub names so tests can patch SslyzeScanner even when sslyze is absent
- [Phase ?]: Phase 32 Plan 03: _peer_metadata() duck-types the wrapped socket so MagicMock SSLSockets work without spec=ssl.SSLSocket
- [Phase ?]: Phase 32 Plan 04: email findings merged inside the existing risk_engine phase-timer (single span) to preserve report metric integrity
- [Phase 32]: Plan 32-08: mirrored kerberos_scan_json attachment pattern to populate CryptoEndpoint.email_scan_json (closes Phase 32 SC-1) and added an AST-based real-Logger smoke test that catches stdlib-positional-args drift in run_scan.py's email branch
- [Phase ?]: Phase 35 close: CBOM-01..04 marked Complete; REQUIREMENTS wording aligned to code; UAT-35-01..03 added

### Pending Todos

None at roadmap creation.

### Blockers/Concerns

None at roadmap creation.

## Deferred Items

Items deferred at v4.4 close on 2026-04-29 (acknowledged, non-blocking for v4.4 ship):

| ID | Category | Item | Status |
|----|----------|------|--------|
| DEF-v4.4-01 | phase_gating | Phase 36 `wave_0_complete: false` flip | gated on DEF-v4.4-02 fix; documented in `37-VALIDATION.md` "Deferred Gaps" #1 |
| DEF-v4.4-02 | regression | SAML/OIDC missing from `/api/scan/latest` `identity_findings` (real bug, ISSUE-3 from Phase 24) | predates v4.4; out-of-scope for v4.4.0; tracked for v4.5 |

Items carried over from v4.3 (acknowledged, non-blocking for v4.4):

| Category | Item | Status |
|----------|------|--------|
| uat_gap | Phase 04: 04-HUMAN-UAT.md (5 pending scenarios) | partial — Docker chaos lab tests, pre-v3.9 carry-over |
| uat_gap | Phase 05: 05-HUMAN-UAT.md (5 pending scenarios) | partial — Dashboard UI tests, pre-v3.9 carry-over |
| uat_gap | Phase 07: 07-HUMAN-UAT.md (4 pending scenarios) | partial — Packaging tests, pre-v3.9 carry-over |
| uat_gap | Phase 13: 13-UAT.md (6 pending scenarios) | deferred — Interactive mode, pre-v4.1 carry-over |
| uat_gap | Phase 25: 25-HUMAN-UAT.md (2 pending scenarios) | partial — live identity scan requires Docker + samba-dc |
| uat_gap | Phase 27: 27-HUMAN-UAT.md (1 pending scenario) | partial — live DB encryption scan requires running DB |
| uat_gap | Phase 27: 27-UAT.md (7 pending scenarios) | deferred — DB encryption behavioral tests require live DB |
| uat_gap | Phase 28: 28-HUMAN-UAT.md (3 pending scenarios) | partial — live S3/GCS bucket scan requires cloud credentials |
| uat_gap | Phase 29: 29-UAT.md (10 pending scenarios) | testing — K8s secrets inspection requires live cluster |
| uat_gap | Phase 30: 30-HUMAN-UAT.md (1 pending scenario) | partial — live Vault connector requires running Vault instance |
| uat_gap | Phase 31: 31-HUMAN-UAT.md (4 pending scenarios) | partial — trend analysis requires prior scan history |
| verification_gap | Phase 25: 25-VERIFICATION.md | human_needed — live identity scan (requires Docker) |
| verification_gap | Phase 28: 28-VERIFICATION.md | human_needed — live object storage scan (requires cloud credentials) |
| verification_gap | Phase 31: 31-VERIFICATION.md | human_needed — trend analysis UI requires running dashboard with scan history |

## Session Continuity

Last session: 2026-04-29T02:53:56.747Z
Stopped at: Phase 37 context gathered
Next action: Execute Plan 35-04 (REQUIREMENTS.md amendments per D-01/D-02 + UAT-SERIES.md updates per D-07 + Obsidian sync per D-08)
