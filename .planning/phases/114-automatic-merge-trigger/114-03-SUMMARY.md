---
phase: 114-automatic-merge-trigger
plan: "03"
subsystem: operator-docs / distributed-lab-oracle / uat
tags: [automerge, docs, operators-guide, chaos-lab, uat]
dependency_graph:
  requires: [114-01]
  provides: [auto-merge-operator-docs, distributed-lab-oracle-updated, uat-114-series]
  affects: [docs/operators-guide.md, quantum-chaos-enterprise-lab/expected_results_distributed.md, docs/UAT-SERIES.md]
tech_stack:
  added: []
  patterns: [documentation-only, no runtime changes]
key_files:
  created: []
  modified:
    - docs/operators-guide.md
    - quantum-chaos-enterprise-lab/expected_results_distributed.md
    - docs/UAT-SERIES.md
decisions:
  - "§8.9 Automatic Merge placed after §8.6 (air-gap) and before §8.7 (settings reference) to keep distributed workflow docs contiguous"
  - "Oracle notes manual Step 3 as harmless duplicate + regression proof per D-06 / AUTOMERGE-03"
  - "UAT-114-03 is human type — visual review of operators-guide §8.9 completeness cannot be automated"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-27"
  tasks_completed: 3
  files_changed: 3
---

# Phase 114 Plan 03: Operator Docs + Lab Oracle + UAT/Obsidian Sync Summary

Operator documentation for the auto-merge feature, distributed lab oracle updated to reflect default-ON auto-merge behavior, and UAT Series 114 added and synced to Obsidian.

## What Was Built

### Task 1: operators-guide.md §8.9 Automatic Merge (commit e8ebd58)

Added §8.9 Automatic Merge immediately before §8.7 in the Distributed Sensor Deployment section. Covers:

- **Default-ON behavior** — auto-merge fires after every successful push once the trigger condition is met; push latency unaffected (BackgroundTask after db.commit()).
- **Disable toggle** — `console.auto_merge.enabled: false` config snippet for explicit manual-only control.
- **In-flight safety** — toggle read per push; changing the setting does not affect pushes already in flight.
- **`all-sensors-in` condition** — merge fires when every non-revoked enrolled sensor has pushed a result newer than the latest MergeRun; revoked sensors excluded via Phase 113 `revoked_at`.
- **`cadence-window` condition** — push-evaluated time-bounded merge; fires when elapsed time since last MergeRun exceeds `cadence_window_minutes` (default: per-sensor `expected_cadence_minutes` = 1440); emits `coverage_warning` for sensors not yet in.
- **Idempotency note** — harmless duplicate MergeRun on narrow TOCTOU races (D-06).
- **IntegrationDelivery audit row table** — `destination="auto_merge"`, `status=ok/failed`, `error_summary`; SQLite query example.
- **AUTOMERGE-03** — explicit statement that `quirk sensor merge` is unchanged, calls the same `merge_scan()`, and remains fully available.

### Task 2: Distributed lab oracle (commit a0eae5c)

Updated the Expected E2E Outcome table in `expected_results_distributed.md`:

- Added auto-merge row: fires after sensor-b push; writes MergeRun + IntegrationDelivery `destination="auto_merge" status="ok"`.
- Manual Step 3 `quirk sensor merge` retained explicitly as harmless duplicate (D-06) and regression proof (AUTOMERGE-03).
- Wording consistent with the rest of the oracle; `quirk sensor merge` step not removed.

### Task 3: UAT-SERIES.md + Obsidian sync (commit 17af975)

Updated header `**Last Updated:**` to 2026-05-27 with Phase 114 Plan 03 completion note. Added UAT Series 114 with three test cases:

- **UAT-114-01** (Automated): grep gates confirming operators-guide has `auto_merge`, `all-sensors-in`, `cadence-window`, and `AUTOMERGE-03`.
- **UAT-114-02** (Automated): grep gates confirming oracle has `auto_merge`/`auto-merge`, `quirk sensor merge`, and regression note.
- **UAT-114-03** (Human): visual review of §8.9 completeness against 114-CONTEXT.md decisions.

Synced to Obsidian vault via `printf+cat+cp` sequence — `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` updated.

## Verification Results

- `grep -q "auto_merge" docs/operators-guide.md && grep -q "all-sensors-in" docs/operators-guide.md && grep -q "cadence-window" docs/operators-guide.md` — PASS
- `grep -q "auto_merge\|auto-merge" quantum-chaos-enterprise-lab/expected_results_distributed.md` — PASS
- `test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md"` — PASS (vault file confirmed)

## Deviations from Plan

None — plan executed exactly as written. The §8.9 section was placed between §8.6 and §8.7 (rather than at the very end of §8) to keep the distributed workflow docs contiguous; this is a layout decision consistent with the existing section order, not a semantic deviation.

## Known Stubs

None. All documentation is complete and accurately reflects the feature as implemented in Plans 114-01 and 114-02.

## Threat Flags

None — documentation-only plan; no new runtime trust boundaries introduced.

## Self-Check: PASSED

- `docs/operators-guide.md` modified and committed at e8ebd58 — verified
- `quantum-chaos-enterprise-lab/expected_results_distributed.md` modified and committed at a0eae5c — verified
- `docs/UAT-SERIES.md` modified and committed at 17af975 — verified
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` exists — verified
