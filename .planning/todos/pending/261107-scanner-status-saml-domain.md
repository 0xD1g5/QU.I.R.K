---
type: todo
created: 2026-11-08
title: Scanner Status lists saml_scanner under data_at_rest
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: low
area: Scanner Status domain map
status: pending
resolves_phase: null
owner: null
---

# Scanner Status lists saml_scanner under data_at_rest

Kind: product

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261107-scanner-status-saml-domain`) when PR #70 lands.

## Observed

Scanner Status lists saml_scanner under data_at_rest; it should be identity.

## Evidence

passA.md attempt 2 (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Trivial (under 1h): fix the domain mapping and add a test.
