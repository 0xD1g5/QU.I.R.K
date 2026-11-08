---
type: todo
created: 2026-11-08
title: MySQL 23306 scan fails with a client-library AttributeError
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: medium
area: quirk/scanner (MySQL path)
status: pending
resolves_phase: null
owner: null
---

# MySQL 23306 scan fails with a client-library AttributeError

Kind: product

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261107-mysql-auth-switch-crash`) when PR #70 lands.

## Observed

MySQL 23306 scan fails with `AttributeError: 'NoneType' object has no attribute 'is_auth_switch_request'` (client-library crash). The UI shows it honestly as a red Failed.

## Evidence

235.4-evidence/walkthrough/passA.md attempt 1 (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Small to medium (1-3h): reproduce against the lab MySQL, catch the library crash and report a reasoned failure, or pin/upgrade the client.
