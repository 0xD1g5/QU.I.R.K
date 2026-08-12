# Phase 149 Test Suite Triage Ledger (SUITE-01)

This ledger tracks the disposition of every currently-failing test in QU.I.R.K.'s full
suite, one cluster at a time. Each of Plans 02-10 in Phase 149 owns one or more clusters
below, investigates every failing test in scope, and appends a row to that cluster's
table recording how the failure was resolved (fixed, quarantined, deleted, or
environment-fixed). This file is the single source of truth for the triage effort — no
test is dropped silently; every disposition is either a code fix, a documented
quarantine entry in `tests/skip_registry.py`, or an explicit deletion with rationale.

Built against: `pytest -q -m ""` → 113 failed, 3078 passed, 22 skipped, 125 warnings — 2026-08-11

## Status Legend

- **fixed** — the underlying code or test defect was corrected; the test now passes
  legitimately.
- **quarantined-skip** — the test is marked `pytest.skip()` / `@pytest.mark.skipif` with
  a `pre_existing_triage_149`-category entry in `tests/skip_registry.py`, pending a
  follow-up fix outside this phase's scope.
- **quarantined-xfail** — the test is marked `@pytest.mark.xfail` with a
  `pre_existing_triage_149`-category entry in `tests/skip_registry.py`, expected to fail
  until a follow-up fix lands.
- **deleted** — the test (or the marker) was removed because it tests behavior/a module
  that no longer exists, confirmed via grep/read (mirrors D-05 from Phase 41).
- **environment-fix-applied** — the test failure was caused by a dev-environment gap
  (missing optional extra, stale local state, etc.) that was fixed at the environment
  level rather than in test or production code.

## Cluster 1: SSRF/DNS-blocked sandbox

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 2: Playwright cross-test pollution

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 3: Version staleness (environment)

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 4: Version staleness (stale assertions)

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 5: sensor_id shape / AUDIT-08 regression

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 6: pip dry-run extras-install flakiness

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 7: Optional GCP extras missing

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 8: Meta-gate self-failure (D-04)

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `test_skip_registry.py::test_no_unregistered_skips` | fixed | D-04 drift repaired | 30 unregistered skip markers registered/updated in `tests/skip_registry.py`; AST walker extended to detect `skip`/`skipif`/`xfail` decorators (Plan 01, Tasks 1-2) | No — resolved via direct registry repair, no quarantine needed |

## Cluster 9: Remaining individually-distinct failures

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

---

*Phase: 149-test-suite-triage*
*Plan: 01*
*Updated: 2026-08-11*
