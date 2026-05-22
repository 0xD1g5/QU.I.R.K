---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: Stabilization + Tech Debt Sweep — Phases 87–92
status: Awaiting next milestone
last_updated: "2026-05-22T23:52:43.267Z"
last_activity: 2026-05-22 — Milestone v5.0 completed and archived
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 16
  completed_plans: 16
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** Planning next milestone (v5.1 — capability work resumes)

## Current Position

Phase: Milestone v5.0 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-05-22 — Milestone v5.0 completed and archived

## Milestone Plan (v5.0 — Stabilization + Tech Debt Sweep, opened 2026-05-22)

Theme locked in `.planning/HORIZON.md` (Candidate C, pulled forward from v5.2). Numbering continues at **Phase 87**; HORIZON guardrail **≤6 phases**. No new capability surface.

**Phase sequence:**

| Phase | Slug | Requirements | Dependencies | Notes |
|-------|------|--------------|--------------|-------|
| 87 | dependency-hygiene | DEP-01, DEP-02 | None (sequenced first by deadline) | Node 20→24 hard deadline 2026-06-16 |
| 88 | scoring-residuals | EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01, SCORE-CBOM-01, SCORE-XPARENCY-01 | Phase 87 | Opens with product-decision gate |
| 89 | chaos-lab-profiles | LAB-01..06 | Phase 87 (parallel-safe with 91) | CLAUDE.md lab-sync in each change |
| 90 | oqs-nginx-pqc-hybrid | PQC-01, PQC-02, PQC-03 | Phase 88 (avoids double-churning invariant) | Discuss strategy before planning |
| 91 | code-cleanup-bookkeeping | CLEAN-01..04 | Phase 87 (parallel-safe with 89) | Tier-A before Tier-B |
| 92 | v5.0-close-out | REL-01 | All prior phases | Version 5.0.0, towncrier, tag |

**Pre-locked decisions:**

- Phase 88 MUST open with EVIDENCE-TALLY-01 product-decision gate + parametrized RED test suite
- Phase 90 MUST discuss OQS image digest + detection strategy via `/gsd-discuss-phase 90` before planning
- OQS image MUST be digest-pinned, not `:latest`
- Phase 90 sequenced after Phase 88 so SCORE_WEIGHTS invariant sum changes don't collide

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

**v4.10 archive:** `.planning/milestones/v4.10-ROADMAP.md` + `.planning/milestones/v4.10-REQUIREMENTS.md`. Tag `v4.10.0` (local-only). PyPI distribution name `quirk-scanner`.

## Accumulated Context

### Roadmap Evolution

- v4.10.1 shipped 2026-05-22. Single phase (86), 3 plans, 8/8 requirements. Archived to `.planning/milestones/v4.10.1-ROADMAP.md`.
- v5.0 roadmap created 2026-05-22. 6 phases (87–92), 21 requirements, 100% coverage. Phases derived from approved research structure.

### Decisions (v5.0 — pre-locked at roadmap)

- v5.0-D-01: Phase 87 sequenced first — Node 20→24 bump has a hard GitHub deadline (2026-06-16 default-switch, 2026-09-16 hard removal); lxml/XXE migration bundled in same phase as two-plan unit
- v5.0-D-02: Phase 88 entry criterion — product-decision gate on EVIDENCE-TALLY-01 must resolve before any penalty-counter changes; parametrized RED test suite must exist first
- v5.0-D-03: Phase 90 sequenced after Phase 88 — adding a new SCORE_WEIGHTS key after Phase 88 stabilizes the invariant sum avoids double-churning `tests/test_score_weights_invariant.py`
- v5.0-D-04: OQS image must be digest-pinned (not `:latest`) — oqs-provider renames group names across releases; `:latest` creates a moving-target that silently breaks detection
- v5.0-D-05: Phase 90 detection strategy (real probe vs advisory) deferred to `/gsd-discuss-phase 90` after the digest is pinned and sslyze output is observed empirically
- v5.0-D-06: Phase 91 Tier-A (file/comment/syntax) ships before Tier-B (function/module deletions) — each Tier-B deletion batch requires vulture/AST call-graph confirmation + clean-venv smoke test
- v5.0-D-07: Phases 89 and 91 are parallel-safe (disjoint code paths) and can run concurrently after Phase 87

### Decisions (v4.10.1)

- 86-01-D-01: int(round(sum/1.5)) normalization replaces _clamp(sum,0,100) — canonical 120→80 confirmed
- 86-01-D-02: SCORE_WEIGHTS and _apply_weighted_impacts unchanged (0-25 subscore budget preserved)
- 86-01-D-03: Docstring rewritten to remove Phase 60 SCORE-04 clamp-is-intentional language

### Pending Todos

- Confirm smtp-starttls profile is non-redundant with existing `email` profile before finalizing LAB-03 (check in Phase 89 planning)
- LAB-05 gRPC: empirically verify sslyze negotiates ALPN `h2` before finalizing probe approach

### Blockers

None.

## Deferred Items

Acknowledged and deferred at v5.0 milestone close (2026-05-22) — all non-blocking, environment-gated human-UAT (run at release dry-run before any public push):

| Category | Item | Status |
|----------|------|--------|
| verification (88) | CLI markdown report — Score Decomposition table visual render (six /25 rows + ÷1.5 rollup) | deferred — code 5/5 verified |
| verification (88) | HTML report — Score Decomposition table visual render in a browser | deferred — Jinja2 context wired |
| verification (88) | PDF report — Score Decomposition table (Playwright) | deferred — needs running server |
| verification (89) | kerberos `identity_weak_etype_count` > 0 | deferred — needs `[identity]`/impacket + live KDC; macOS port-88 caveat. DNSSEC+SAML counters verified non-zero; wiring confirmed correct |

89's original `gaps_found` bookkeeping (LAB-01/02/04/06 REQUIREMENTS rows) was retroactively closed by Phase 91 CLEAN-03. The VERIFICATION.md status strings (88 `human_needed`, 89 `gaps_found`) were left as-is for historical accuracy; the v5.0 milestone audit (PASSED) is the authoritative reconciliation.

## Session Continuity

**Last session:** 2026-05-22T23:41:11.991Z

**Next session:** v5.0 SHIPPED (6/6 phases, audit PASSED, local `v5.0.0` tag). Start v5.1 capability work with `/gsd-new-milestone`. SCORE_WEIGHTS invariant now at sum 283.0 / count 37 (PQC-03 added the agility bonus). 4 human-UAT deferred (see Deferred Items).

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
