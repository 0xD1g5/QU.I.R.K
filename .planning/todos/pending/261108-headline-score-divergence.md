---
type: todo
created: 2026-11-08
title: Dashboard headline score differs from job report for the same run
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: medium
area: dashboard score vs report pipeline
status: pending
resolves_phase: null
owner: null
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
