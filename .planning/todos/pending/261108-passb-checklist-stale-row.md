---
type: todo
created: 2026-11-08
title: (process) Pass B checklist staged with stale rows
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: low
area: release walkthrough staging
status: pending
resolves_phase: null
owner: null
---

# (process) Pass B checklist staged with stale rows

Kind: process (gsd-tooling/dev-env flavour; belongs in LEDGER 'Development tooling (not shipped)', not Open)

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261108-passb-checklist-stale-row`) when PR #70 lands.

## Observed

Plan 02 staged passB checklist row 2 as "no cloud creds" although Plan 04 used MinIO keys, and a loopback-only trusted_targets that omitted the DNSSEC zones.

## Evidence

235.4-evidence/walkthrough/passB.md (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Trivial (under 1h): derive the checklist from the plan's actual credentials and zone list.
