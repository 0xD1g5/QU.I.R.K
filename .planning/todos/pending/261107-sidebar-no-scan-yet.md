---
type: todo
created: 2026-11-08
title: Sidebar footer reads 'No scan yet' after completed scans
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: low
area: src/dashboard sidebar
status: pending
resolves_phase: null
owner: null
---

# Sidebar footer reads 'No scan yet' after completed scans

Kind: product

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261107-sidebar-no-scan-yet`) when PR #70 lands.

## Observed

Sidebar footer reads "No scan yet" after completed scans.

## Evidence

passA.md and screenshots (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Small (1-2h): find the footer's data source and why it ignores completed jobs.
