---
type: todo
created: 2026-11-08
title: Executive header says no report artifacts while report files exist
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: low
area: src/dashboard executive page
status: pending
resolves_phase: null
owner: null
---

# Executive header says no report artifacts while report files exist

Kind: product

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261107-exec-no-report-artifacts`) when PR #70 lands.

## Observed

Executive header shows "No report artifacts yet - run a scan first" while report-*.html/.docx exist for the job.

## Evidence

passA.md attempt 2 (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Small (1-2h): check the artifact lookup the header uses vs the job report listing.
