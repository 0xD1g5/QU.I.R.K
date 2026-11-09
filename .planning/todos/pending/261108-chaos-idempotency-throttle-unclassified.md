---
type: todo
created: 2026-11-08
title: Registry pull throttle misread as plain first-up failure in chaos idempotency test
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: medium
area: tests/test_chaos_lab_idempotency.py
status: pending
resolves_phase: null
owner: null
---

# Registry pull throttle misread as plain first-up failure in chaos idempotency test

Kind: product-test

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261108-chaos-idempotency-throttle-unclassified`) when PR #70 lands.

## Observed

`test_profile_re_up_is_idempotent[adcs]` and `[broker]` failed on main at M (Python CI 42502514911, Linux Full Suite) with `error from registry: retry-after: ...us, allowed: 44000/minute`, a registry pull throttle, yet the test reported `registry_refusal=None control_probe=(None, None)`, so a transient infra failure read as a plain "first up failed". The identical tree (031d9394) passed twice. Fix: classify `retry-after` / `allowed: N/minute` (and HTTP 429 / toomanyrequests) as a registry refusal. Not a 5.28.2 blocker.

## Evidence

235.4-evidence/ci/main-at-merge.json (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Small (1-2h): extend the refusal classifier and add a unit case.
