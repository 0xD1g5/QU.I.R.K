---
type: todo
created: 2026-11-08
title: ConnectorsPanel field order splits credentials from targets
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: low
area: src/dashboard/.../ConnectorsPanel.tsx:621 and :661
status: pending
resolves_phase: null
owner: null
---

# ConnectorsPanel field order splits credentials from targets

Kind: product

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261108-connector-field-order`) when PR #70 lands.

## Observed

ConnectorsPanel renders all CONNECTOR_CREDENTIAL_FIELDS before detail fields, so Database shows PG Password, MySQL Password, PG Targets, PG Username, MySQL Targets, MySQL Username; the same split puts Vault Token above Address, AD CS Password above Targets, and Broker user/pass above Targets. Fix: one interleaved per-connector order (targets, username, password per engine). Operator: next release, not 5.28.2.

## Evidence

operator request 2026-11-08 (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Small to medium (2-3h): per-connector ordering table plus a render test; `npm run build`.
