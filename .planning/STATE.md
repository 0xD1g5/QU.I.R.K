---
gsd_state_version: 1.0
milestone: v4.10.1
milestone_name: Scoring Correctness Hotfix
status: executing
last_updated: "2026-05-22T12:00:27.581Z"
last_activity: "2026-05-22 — Plan 86-01 complete: int(round(sum/1.5)) normalization live, docstring rewritten, 3 boundary tests green"
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** v4.10.1 — roadmap defined (Phase 86 single-phase MVP hotfix), ready for `/gsd-mvp-phase` stamp + planning

## Current Position

Phase: 86 — Scoring Correctness Hotfix (in progress)
Plan: 86-01 complete; 86-02 and 86-03 pending
Status: In progress — Plan 86-01 complete (backend normalization + boundary tests)
Last activity: 2026-05-22 — Plan 86-01 complete: int(round(sum/1.5)) normalization live, docstring rewritten, 3 boundary tests green

## Milestone Summary (v4.10.1 — in progress)

| Phase | Mode | Slug | Plans | Status |
|-------|------|------|-------|--------|
| 86 | mvp | scoring-correctness-hotfix | 3 | In progress (1/3 plans complete) |

**Structure:** Single-phase vertical MVP slice — backend math fix (SCORE-FIX-01..03) + frontend gauge fix (GAUGE-01..03) + release engineering (RELEASE-01..02) are tightly coupled and ship together. Splitting would yield half-fixes that contradict each other (backend without frontend produces a different wrong number; frontend without backend is meaningless).

**Deferred to v5.0 Phase 01 — Stabilization:** EVIDENCE-TALLY-01 (subscore tally bug — separate root cause in evidence summarizer), RENDER-CLI-01 (CLI report same-bug-class audit), RENDER-PDF-01 (PDF report same-bug-class audit). Captured as Future Requirements in `.planning/REQUIREMENTS.md` so the v5.0 plan absorbs them without re-discovery.

## Previous Milestone Summary (v4.10 — SHIPPED 2026-05-21)

| Phase | Wave | Slug | Plans | Status |
|-------|------|------|-------|--------|
| 78 | A | html-pdf-injection-hardening | 5/5 | Complete 2026-05-16 |
| 79 | A | smime-ldap-discovery-scanner | 4/4 | Complete 2026-05-16 |
| 80 | A | windows-adcs-scanner | 4/4 | Complete 2026-05-16 |
| 81 | A | cmvp-attestation-feed | 4/4 | Complete 2026-05-16 |
| 82 | A/B | chaos-lab-fidelity | 4/4 | Complete 2026-05-16 |
| 83 | B | integration-gate-cleanup | 1/1 | Complete 2026-05-16 |
| 84 | B | release-engineering | 4/4 | Complete 2026-05-21 |
| 85 | C | public-launch-polish | 5/5 | Complete 2026-05-21 |

**v4.10 archive:** `.planning/milestones/v4.10-ROADMAP.md` + `.planning/milestones/v4.10-REQUIREMENTS.md`. Tag `v4.10.0` (local-only; v4.10.0 release tag NOT pushed). PyPI distribution name `quirk-scanner`. 5 deferred human UAT items for release dry-run.

## Previous Milestone Summary (v4.9 — SHIPPED 2026-05-15)

| Phase | Slug | Plans | Status |
|-------|------|-------|--------|
| 69 | deferred-blockers-scanner-cloud | 6/6 | Complete 2026-05-15 |
| 69.1 | k8s-test-fixture-hardening (INSERTED) | 1/1 | Complete 2026-05-15 |
| 70 | deferred-blockers-api-qramm-model | 3/3 | Complete 2026-05-15 |
| 71 | protocol-scanner-warnings | 5/5 | Complete 2026-05-15 |
| 72 | cloud-scanner-warnings | 5/5 | Complete 2026-05-15 |
| 73 | cbom-intel-reports-warnings | 3/3 | Complete 2026-05-15 |
| 74 | qramm-compliance-warnings | 3/3 | Complete 2026-05-15 |
| 75 | api-cli-core-warnings | 4/4 | Complete 2026-05-15 |
| 76 | react-frontend-warnings | 3/3 | Complete 2026-05-15 |
| 77 | info-code-quality-audit-ledger | 5/5 | Complete 2026-05-15 |

**Audit ledger (v4.9):** zero `[ ] open` rows — 166 closed, 2 deferred-with-rationale, 4 wont-fix-with-rationale; CI gate `tests/test_audit_ledger_zero_open.py` locks the invariant forward.

## Accumulated Context

### Roadmap Evolution

- v4.9 shipped 2026-05-15. All 35 requirements satisfied; archive at `.planning/milestones/v4.9-ROADMAP.md` + `.planning/milestones/v4.9-REQUIREMENTS.md`.
- v4.10 shipped 2026-05-21. 8 phases (78–85), 31 plans, 52/52 requirements; archived to `.planning/milestones/v4.10-ROADMAP.md`.
- v4.10.1 roadmap created 2026-05-22. Single phase (86), 8 requirements, 100% coverage. Vertical MVP slice — backend + frontend + release engineering coupled by physics (the wrong-number bug spans backend aggregation and frontend gauge math; fixing only half produces a different wrong number).

### Decisions (v4.10.1)

- 86-01-D-01: int(round(sum/1.5)) normalization replaces _clamp(sum,0,100) — canonical 120→80 confirmed
- 86-01-D-02: SCORE_WEIGHTS and _apply_weighted_impacts unchanged (0-25 subscore budget preserved)
- 86-01-D-03: Docstring rewritten to remove Phase 60 SCORE-04 clamp-is-intentional language

### Decisions (v4.10.1 — pre-execution)

- v4.10.1-D-01 (pre-locked by milestone scope): single-phase MVP. Backend math fix, frontend gauge fix, version bump and changelog ship as one atomic unit. Splitting risks shipping a half-fix that displays a different wrong number.
- v4.10.1-D-02 (pre-locked by milestone scope): no stored-score migration. SQLite values are untouched; old scans display the new math when re-rendered. Visual jump from 100 → ~80 for the canonical `tls-cert-defects` scan is documented in CHANGELOG.md as accepted trade-off.
- v4.10.1-D-03 (pre-locked by milestone scope): CLI / HTML / PDF render-side fixes deferred to v5.0 Phase 01 (Stabilization). Same bug class likely exists there but a full-stack scoring sweep is the right shape; mixing into a hotfix risks shipping new bugs.
- v4.10.1-D-04 (pre-locked by milestone scope): evidence-tally gap (3 subscores at 25 despite findings) deferred to v5.0 Phase 01. Separate root cause in the evidence summarizer; touching that pipeline expands the diff well beyond a hotfix.

### Pending Todos

- Execute Plan 86-02: frontend gauge fix (ScoreGauge.tsx maxValue prop, executive.tsx + data-at-rest.tsx maxValue={25}).
- Execute Plan 86-03: version bump to 4.10.1 + changelog entry.

### Blockers

None.

## Session Continuity

**Last session:** 2026-05-22T12:00:27.577Z

**Next session:** Execute Plan 86-02 (frontend gauge fix: maxValue prop, _gaugeColor fraction rewrite, executive.tsx + data-at-rest.tsx maxValue={25}).
