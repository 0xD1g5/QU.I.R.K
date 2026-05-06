---
gsd_state_version: 1.0
milestone: v4.7
milestone_name: Governance & Compliance Platform
current_phase: null
current_phase_name: null
status: planning
stopped_at: Roadmap created for v4.7 Governance & Compliance Platform
last_updated: "2026-05-05T23:59:00.000Z"
last_activity: 2026-05-05 -- v4.7 roadmap initialized (6 phases, 24 requirements)
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-05)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** Planning v4.7 milestone — Governance & Compliance Platform

## Current Position

Phase: Not started
Plan: —
Status: Roadmap created; awaiting phase planning
Last activity: 2026-05-05 — v4.7 roadmap created (Phases 51–56)

Progress bar: `░░░░░░░░░░░░░░░░░░░░` 0% (0/6 phases)

## Phase Overview

| Phase | Slug | Depends On | Requirements |
|-------|------|------------|--------------|
| 51 | qramm-core-infrastructure | Phase 50 | QRAMM-01, QRAMM-02, QRAMM-03, QRAMM-04, DEBT-01 |
| 52 | compliance-uplift-health-check | Phase 50 (parallel to 51) | COMPLY-10, COMPLY-11, COMPLY-12, DOCS-05, DEBT-02, DEBT-03, DEBT-04 |
| 53 | qramm-evidence-bridge | Phase 51 | QRAMM-12, QRAMM-13, QRAMM-14 |
| 54 | qramm-assessment-ui-scorecard | Phase 51, Phase 53 | QRAMM-08, QRAMM-09, QRAMM-10, QRAMM-11 |
| 55 | qramm-compliance-mapping-view | Phase 52, Phase 54 | QRAMM-05, QRAMM-06, QRAMM-07, QRAMM-15 |
| 56 | pdf-export-staleness-enforcement | Phase 54, Phase 55 | QRAMM-16 |

**Critical path:** 50 → 51 → 53 → 54 → 55 → 56
**Parallel execution:** Phase 52 runs in parallel with Phase 51 (zero shared dependencies)

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v4.7)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Status |
|-------|-------|--------|
| 51 | TBD | Not started |
| 52 | TBD | Not started |
| 53 | TBD | Not started |
| 54 | TBD | Not started |
| 55 | TBD | Not started |
| 56 | TBD | Not started |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

**v4.7 roadmap decisions (2026-05-05):**

- [v4.7-D-01]: Phase 51 and Phase 52 are fully parallel — Phase 51 owns QRAMM tables/API/scoring/questions, Phase 52 owns compliance extensions + doctor CLI + tech debt. Zero shared code paths at planning time.
- [v4.7-D-02]: DEBT-01 (datetime.utcnow → datetime.now(timezone.utc)) assigned to Phase 51 — must ship before any staleness gate logic is written in Phase 55/56 to avoid a Python 3.12+ DeprecationWarning in the CI staleness infrastructure itself.
- [v4.7-D-03]: QRAMM evidence bridge (Phase 53) gates on Phase 51 only, not Phase 52 — the bridge reads CryptoEndpoint rows via SESSION_BRACKET pattern; no dependency on compliance module extensions.
- [v4.7-D-04]: Phase 55 gates on both Phase 52 (for ISO 27001:2022 + SOC2 framework availability) and Phase 54 (for active assessment session data to drive per-practice relevance scores).
- [v4.7-D-05]: Phase 56 gates on Phase 54 (radar chart SVG must exist for PDF embed) and Phase 55 (compliance mapping summary section requires the 8-framework view to be implemented).
- [v4.7-D-06]: QRAMM-16 (PDF export) is the sole requirement in Phase 56 — it is not combined with Phase 55 to avoid a phase that conflates UI work (Phase 55) with print/export work (Phase 56) and to keep success criteria independently verifiable.
- [v4.7-D-07]: QRAMM staleness metadata (QRAMM-05, QRAMM-06, QRAMM-07) assigned to Phase 55, not Phase 51 — staleness enforcement requires the compliance mapping view (Phase 55) to be meaningful; it mirrors the `quirk compliance status` pattern from v4.6 Phase 49.

### Pending Todos

None at roadmap creation.

### Blockers/Concerns

None at roadmap creation.

## Deferred Items

Items carried forward from v4.6 close (2026-05-05):

| Category | Item | Status |
|----------|------|--------|
| uat_gap | Phase 43: 43-HUMAN-UAT.md (2 pending) — loading-state first paint + keyboard focus ring visibility | deferred — require live browser session |
| uat_gap | Phase 44: 44-HUMAN-UAT.md (1 pending) — Phase 29 K8s cloud-only justification review | deferred — human confirmation needed |
| verification_gap | Phase 46: 46-VERIFICATION.md not authored (code verified live during Phase 46 execution) | deferred — retroactive authoring needed |
| uat_gap | Phase 47: 4 manual TTY tests pending (nmap wizard interactive flow) | deferred — require TTY session |
| test_infra | `test_cbom_schema_validation.py` fails when `cyclonedx-python-lib[json-validation]` not installed | deferred — optional dep, not blocking |

## Session Continuity

Last session: 2026-05-05T23:59:00.000Z
Stopped at: v4.7 roadmap created; Phase 51 is next
Next action: `/gsd-plan-phase 51` — QRAMM Core Infrastructure
