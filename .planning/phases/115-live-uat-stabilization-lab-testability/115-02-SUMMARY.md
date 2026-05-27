---
phase: 115-live-uat-stabilization-lab-testability
plan: "02"
subsystem: packaging, scheduler
tags: [stab-02, stab-03, cmvp, scheduler, importlib-resources, regression-guard]
dependency_graph:
  requires: []
  provides: [STAB-02, STAB-03]
  affects: [quirk.compliance.cmvp, quirk.cli.scheduler_cmd]
tech_stack:
  added: []
  patterns:
    - importlib.resources.files() for wheel-safe package resource loading
    - static source-analysis regression test (tokenize-based _strip_comments)
    - fail-fast guard on missing scan config before subprocess launch
key_files:
  created: []
  modified:
    - pyproject.toml
    - quirk/compliance/cmvp.py
    - quirk/cli/scheduler_cmd.py
    - tests/test_scheduler_posix_fixes.py
decisions:
  - "STAB-02: importlib.resources used for _load_cache read path; override hook honors monkeypatched _CACHE_PATH for test isolation; _CACHE_PATH write path kept for refresh_cache (dev-only tool)"
  - "STAB-03: --target and --output removed from scheduler subprocess cmd; fail-fast guard marks run failed when scan_config_path is None; regression test added via static source analysis"
metrics:
  duration_minutes: 12
  completed_date: "2026-05-27"
  tasks_completed: 2
  files_changed: 4
---

# Phase 115 Plan 02: CMVP Packaging + Scheduler Arg Fix Summary

**One-liner:** cmvp_cache.json shipped in wheel via package-data + importlib.resources load; scheduler drops unsupported --target/--output, fails fast on missing config.

## What Was Built

### Task 1: Ship cmvp_cache.json in wheel + wheel-safe load (STAB-02)

- **pyproject.toml**: added `"compliance/*.json"` to `[tool.setuptools.package-data]` quirk list — ensures `cmvp_cache.json` (and any future compliance JSON) is included when building a wheel. Without this, the file was absent from wheel installs, producing a "CMVP cache unavailable" warning on merge.

- **quirk/compliance/cmvp.py**: added `from importlib.resources import files as _ir_files` import; migrated `_load_cache` read path from `_CACHE_PATH.read_text()` to `_ir_files("quirk.compliance").joinpath("cmvp_cache.json").read_text(encoding="utf-8")` — wheel-safe resource loading.

  Override hook retained: if `_CACHE_PATH` has been replaced by a test monkeypatch (e.g. `test_refresh_dry_run_writes_nothing`), `_load_cache` falls back to reading it directly for test isolation. The `refresh_cache` write path (`_atomic_write_json(_CACHE_PATH, ...)`) was left unchanged — refresh is a developer-only tool run from a source checkout (Pitfall 2).

- Existing schema assertion validation (last_verified, source_url, modules keys, algorithm list type) unchanged.

### Task 2: Drop --target/--output + fail-fast guard + regression test (STAB-03)

- **quirk/cli/scheduler_cmd.py**: removed `--target`/`schedule.target` and `--output`/`str(output_dir)` from the `python -m run_scan` subprocess cmd list. `run_scan.py`'s top-level argparser does not declare either argument; passing them caused `unrecognized arguments` and non-zero exit on every scheduled scan.

  Added fail-fast guard (open-Q1): if `scan_config_path is None`, the run is immediately marked `failed`, an error is logged naming the schedule, and the function returns without launching run_scan. This prevents a targetless/hung scan attempt when no config file is associated with a schedule.

  Simplified cmd builder: `--config` is now always appended (after the fail-fast guard guarantees `scan_config_path` is non-None). The `output_dir.mkdir` and `output_base` fallback branch were removed since `scan_config_path` is always set at that point.

  Added NOTE comment explaining target + output are driven by `--config` (cfg.target + cfg.output.directory, SENSOR-05 anchoring).

- **tests/test_scheduler_posix_fixes.py**: added `test_scheduler_cmd_drops_target_and_output()` module-level function using `_strip_comments` static source-analysis style (mirrors SENSOR-05 Fix 1 regression guard). Asserts `'"--target"'` and `'"--output"'` are absent from the stripped scheduler source.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test isolation regression in _load_cache**

- **Found during:** Task 1 verification (`pytest tests/ -k cmvp`)
- **Issue:** Migrating `_load_cache` to use `importlib.resources` unconditionally broke `test_refresh_dry_run_writes_nothing`, which monkeypatches the module-level `_CACHE_PATH` to a tmp path to feed a synthetic cache. The new code bypassed `_CACHE_PATH` entirely, so the patched path was never read and the test's diff logic got no "before" snapshot.
- **Fix:** Added override hook in `_load_cache` — compares `_CACHE_PATH` to `Path(__file__).parent / "cmvp_cache.json"` (the default); if they differ and `_CACHE_PATH.exists()`, reads it directly. Production code always takes the `importlib.resources` path.
- **Files modified:** `quirk/compliance/cmvp.py`
- **Commit:** ba4bb74

## Known Stubs

None. Both changes are complete functional fixes with no placeholder or deferred wiring.

## Threat Flags

None. Both changes are purely code/packaging fixes with no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries (T-115-07 and T-115-08 accepted per plan threat model).

## Self-Check: PASSED

Files present:
- pyproject.toml — modified (compliance/*.json entry)
- quirk/compliance/cmvp.py — modified (importlib import + load path)
- quirk/cli/scheduler_cmd.py — modified (--target/--output removed, fail-fast added)
- tests/test_scheduler_posix_fixes.py — modified (test_scheduler_cmd_drops_target_and_output added)

Commits:
- ba4bb74: fix(115-02): STAB-02 — ship cmvp_cache.json in wheel + importlib.resources load
- 855f260: fix(115-02): STAB-03 — drop --target/--output from scheduler + fail-fast + regression
