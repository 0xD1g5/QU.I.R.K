---
phase: 114-automatic-merge-trigger
plan: "01"
subsystem: sensor-push / auto-merge
tags: [automerge, background-task, config, sensor-push, fastapi]
dependency_graph:
  requires: [113-per-sensor-authentication]
  provides: [auto-merge-trigger, run_auto_merge, _load_auto_merge_config, _eval_trigger_condition]
  affects: [quirk/dashboard/api/routes/sensor.py, config.yaml]
tech_stack:
  added: []
  patterns: [FastAPI BackgroundTasks, safe_str audit rows, YAML sub-block loader, naive-UTC datetime]
key_files:
  created: []
  modified:
    - quirk/dashboard/api/routes/sensor.py
    - config.yaml
decisions:
  - "BackgroundTask scheduled after final db.commit() — push response unaffected by merge latency (D-01)"
  - "run_auto_merge opens own DB session mirroring _cmd_merge (D-02)"
  - "Revoked sensors excluded from all-sensors-in via SensorToken.revoked_at subquery (D-04)"
  - "Idempotent re-check inside run_auto_merge: latest_push <= latest_merge.merged_at → no-op (D-05)"
  - "merge_scan() reused byte-for-byte unchanged (D-12)"
  - "IntegrationDelivery destination=auto_merge for both success (ok) and failure (failed) audit rows (D-10)"
  - "safe_str(exc) on all error paths — T-114-01 / T-109-07"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-27"
  tasks_completed: 3
  files_changed: 2
---

# Phase 114 Plan 01: Auto-Merge Trigger Core Summary

Auto-merge trigger core wired into sensor_push via FastAPI BackgroundTask: config loader, trigger evaluator, and run_auto_merge background task using the existing merge_scan() pipeline unchanged.

## What Was Built

### Task 1 + 2: Auto-merge functions in sensor.py (commit 4684062)

Added three new functions and wired `BackgroundTasks` into `sensor_push`:

- `_load_auto_merge_config(config_path)` — never-raise YAML sub-block loader following the `quirk/notify/config.py` pattern. Priority: explicit path > `QUIRK_CONFIG_PATH` env var > `./config.yaml`. Returns `{"enabled": True, "trigger_condition": "all-sensors-in"}` on any failure.

- `_eval_trigger_condition(db, config_path)` — evaluates whether to schedule a merge on each successful push. Two modes:
  - `all-sensors-in`: excludes revoked sensors (SensorToken.revoked_at subquery, Pitfall 2); returns True only when all active sensors have pushed and max(last_push_at) > latest MergeRun.merged_at
  - `cadence-window`: returns True when elapsed time since latest MergeRun exceeds configured window (defaults to per-sensor expected_cadence_minutes); always triggers if no prior MergeRun
  - Unknown condition returns False (safe-off, T-114-05)

- `run_auto_merge(db_path, config_path)` — background task with own DB session mirroring `_cmd_merge`. Includes:
  - idempotent re-check (D-05): no-op if latest_push <= latest_merge.merged_at
  - `merge_scan(db, output_dir=output_dir)` called unchanged (D-12)
  - success: IntegrationDelivery(destination="auto_merge", status="ok") in same session (Pitfall 6)
  - failure: logger.warning + IntegrationDelivery(destination="auto_merge", status="failed", error_summary=safe_str(exc)) in separate session; audit failure swallowed (D-10/D-11)

- `sensor_push` signature extended with `background_tasks: BackgroundTasks`. After the final `db.commit()`, trigger is evaluated and `background_tasks.add_task(run_auto_merge, db_path, config_path)` is scheduled when condition is met. Only scalar strings passed to the task (Pitfall 1).

New imports added: `os`, `yaml`, `BackgroundTasks`, `func` from sqlalchemy, `_default_db_path`, `MergeRun`, `SensorToken`.

### Task 3: config.yaml console.auto_merge block (commit e977dc2)

Appended `console.auto_merge` sub-block to `config.yaml`:
- `enabled: true` — ON by default (D-07)
- `trigger_condition: all-sensors-in` — D-08 selector
- `# cadence_window_minutes: 1440` — documented as commented key (D-09)

## Verification Results

- `python -m compileall quirk/` — clean
- `python -m pytest tests/ -k "sensor_push or sensor_ingest" -q` — 16 passed, 0 failures
- `_load_auto_merge_config('/nonexistent.yaml')` returns defaults without raising
- `sensor_push` signature confirmed via `inspect.signature` — `background_tasks` present
- `run_auto_merge` confirmed importable with `safe_str`, `merge_scan`, `destination="auto_merge"` present

## Deviations from Plan

None — plan executed exactly as written. Tasks 1 and 2 shared the same file so were committed together as one atomic change.

## Known Stubs

None. All functionality is fully wired. Acceptance/gating tests for AUTOMERGE-01/02/03 are deferred to Plan 114-02 as specified in the plan.

## Threat Flags

No new threat surface beyond the plan's threat model. All T-114-01..T-114-05 mitigations applied:
- T-114-01: safe_str(exc) on all IntegrationDelivery error_summary writes
- T-114-02: entire merge in task-owned try/except after response sent
- T-114-03: yaml.safe_load only
- T-114-04: SensorToken.revoked_at subquery excludes revoked sensors
- T-114-05: unknown trigger_condition returns False

## Self-Check: PASSED

- quirk/dashboard/api/routes/sensor.py: modified and committed at 4684062
- config.yaml: modified and committed at e977dc2
- Both commits verified in git log
- 16 sensor-related tests pass
