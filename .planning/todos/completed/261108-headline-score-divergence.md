---
type: todo
created: 2026-11-08
title: Dashboard headline score differs from job report for the same run
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: medium
area: dashboard score vs report pipeline
status: pending
resolves_phase: 236
owner: "999.132"
---

# Dashboard headline score differs from job report for the same run

Kind: product

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261108-headline-score-divergence`) when PR #70 lands.

## Observed

Same run: dashboard headline 42 ("6 open HIGH, computed 78") vs job report 27 ("2 open CRITICAL, computed 78"). Relates to 999.132.

## Evidence

passA.md correction; plan 03 SUMMARY (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Medium (half a day): trace both derivations (the two report pipelines) and unify the cap source.

## Resolution (2026-11-16)

Fixed by Phase 236 (XSURF-14): per-family pinned headline parity (tests/test_cross_surface_parity.py::test_xsurf236_*) plus live legs 28/28/28 and 27/27/27 (intel/html/dashboard). Commits main 405925d5 (PR #82 merge). Pass A replay 27 == 27. Residual: dispositioned DNSSEC NONE (masked by the CRITICAL ceiling in the wider leg).
