---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: Stabilization + Tech Debt Sweep
status: planning
last_updated: "2026-05-22T13:23:32.973Z"
last_activity: 2026-05-22
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** v5.0 Stabilization + Tech Debt Sweep — milestone opened 2026-05-22; research-first → requirements → roadmap. Numbering continues at Phase 87; ≤6 phases.

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-22 — Milestone v5.0 started

## Milestone Plan (v5.0 — Stabilization + Tech Debt Sweep, opened 2026-05-22)

Theme locked in `.planning/HORIZON.md` (Candidate C, pulled forward from v5.2). Numbering continues at **Phase 87**; HORIZON guardrail **≤6 phases**. Approach: research-first (full 4-agent sweep) → full-sweep requirements scoping, trimmed per-category.

**Candidate bundles:** dependency hygiene (Node 20→24 sequenced FIRST as Phase 87 — hard deadline 2026-06-02; lxml/XXE migration BACK-67), scoring residuals (EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01, Phase 42 OBS-1 CBOM Pass-1, BACK-63), chaos lab targets (BACK-80–84; BACK-81 OQS-nginx PQC-hybrid is the scoring-ceiling anchor), identity lab gap (BACK-78), code cleanup (BACK-49–57), bookkeeping (BACK-62, BACK-58).

**Pre-locked requirements (from v4.10.1 deferral):** EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01 — archived in `.planning/milestones/v4.10.1-REQUIREMENTS.md`, to be absorbed into the v5.0 scoring-residuals phase.

## Previous Milestone Summary (v4.10.1 — SHIPPED 2026-05-22)

| Phase | Mode | Slug | Plans | Status |
|-------|------|------|-------|--------|
| 86 | mvp | scoring-correctness-hotfix | 3 | Complete 2026-05-22 (3/3 plans) |

**v4.10.1 archive:** `.planning/milestones/v4.10.1-ROADMAP.md` + `.planning/milestones/v4.10.1-REQUIREMENTS.md`. Tag `v4.10.1` (local). Verifier PASSED 5/5; HUMAN-UAT PASS.

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
- v4.10.1 shipped 2026-05-22. Single phase (86), 3 plans, 8/8 requirements. Vertical MVP slice — backend + frontend + release engineering coupled by physics (the wrong-number bug spans backend aggregation and frontend gauge math; fixing only half produces a different wrong number). Archived to `.planning/milestones/v4.10.1-ROADMAP.md` + `-REQUIREMENTS.md`.

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

- None for v4.10.1 (shipped). For v5.0 Phase 01 (Stabilization): EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01 are pre-captured as Future Requirements.

### Blockers

None.

## Session Continuity

**Last session:** 2026-05-22 — v5.0 milestone opened. PROJECT.md Current Milestone section written, STATE.md reset, Phase 86 archived to `milestones/v4.10.1-phases/`. Decisions locked: research-first (full 4-agent sweep) → full-sweep scoping; Node 20→24 bump = Phase 87 (2026-06-02 deadline).

**Next session:** Continue v5.0 setup — run domain research (4 parallel gsd-project-researcher agents), then define REQUIREMENTS.md, then spawn gsd-roadmapper. After roadmap approval: `/gsd-discuss-phase 87`.

## Operator Next Steps

- v5.0 research → requirements → roadmap in progress.
