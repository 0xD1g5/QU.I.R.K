---
type: todo
created: 2026-11-08
title: New Scan form does not keep Port Scope = Custom between scans
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: medium
area: src/dashboard New Scan form
status: pending
resolves_phase: null
owner: null
---

# New Scan form does not keep Port Scope = Custom between scans

Kind: product

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261108-newscan-port-scope-reset`) when PR #70 lands.

## Observed

The New Scan form does not keep Port Scope = Custom (plus its list) between consecutive scans; the second scan silently ran top1000.

## Evidence

passA.md correction (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Small to medium (2-3h): persist the form state or warn on reset; relevant to the Phase 121 scope/connector coupling.
