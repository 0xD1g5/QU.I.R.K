---
phase: 154-identity-data-model-foundation
plan: 01
subsystem: database
tags: [sqlalchemy, sqlite, config, migration]

# Dependency graph
requires: []
provides:
  - "HardwareDevice.ssh_host_key_fingerprint / match_confidence / probe_status nullable columns"
  - "_IDENTITY_HW_COLUMNS additive migration entry for hardware_devices"
  - "ScanCfg.hardware_history_retention_days (default 180, YAML-overridable)"
affects: [155-drift-detection-eol-tracking, 156-reporting-and-otics-safety]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New HardwareDevice column block follows existing per-phase comment-header + _ADDITIVE_MIGRATIONS tuple-append convention"
    - "New ScanCfg field follows existing three-edit-point pattern (class annotation, __init__ param, __init__ body assignment) with zero YAML-loader changes"

key-files:
  created: []
  modified:
    - quirk/models.py
    - quirk/db.py
    - quirk/config.py
    - tests/test_hardware_device_model.py
    - tests/test_db_migrations.py
    - tests/test_config.py

key-decisions:
  - "match_confidence kept as a column distinct from the pre-existing confidence column (D-04/D-05) — cross-scan identity confidence vs. probe-result confidence"
  - "hardware_history_retention_days defaults to 180, deliberately not the 90-day STALENESS_THRESHOLD_DAYS convention (D-11)"
  - "quirk/interactive.py left untouched — mirrors existing omission of nmap_port_scope/openapi_spec_path in the setup wizard"

patterns-established:
  - "Phase 154 HWLC-01/02 column block mirrors Phase 141 OTICS block shape exactly (comment header + nullable Column() declarations + _ADDITIVE_MIGRATIONS registration)"

requirements-completed: [HWLC-01, HWLC-02, HWLC-03]

# Metrics
duration: 15min
completed: 2026-08-14
---

# Phase 154 Plan 01: Identity Data-Model Foundation Summary

**Three new nullable HardwareDevice columns (ssh_host_key_fingerprint, match_confidence, probe_status) with additive-migration retrofit, plus ScanCfg.hardware_history_retention_days (default 180) — the schema foundation Plans 02/03/04 build on.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-08-14T18:21:31Z
- **Completed:** 2026-08-14T18:23:47Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- `HardwareDevice` ORM class carries `ssh_host_key_fingerprint`, `match_confidence`, `probe_status` — all nullable, all documented in the class docstring, with `match_confidence` explicitly distinguished from the pre-existing `confidence` column.
- `_IDENTITY_HW_COLUMNS` registered in `_ADDITIVE_MIGRATIONS`, proven to retrofit onto a pre-Phase-154 `hardware_devices` table and report `already-present` idempotently on re-run.
- `ScanCfg.hardware_history_retention_days` added with a 180-day default, overridable from a `scan:` YAML block via the existing `**scan_raw` kwarg passthrough — zero loader code changes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the three HardwareDevice columns + additive-migration registration** - `990a189` (feat)
2. **Task 2: Add ScanCfg.hardware_history_retention_days (default 180)** - `67c4b98` (feat)

**Plan metadata:** (pending — final metadata commit follows this summary)

## Files Created/Modified
- `quirk/models.py` - Added `ssh_host_key_fingerprint`, `match_confidence`, `probe_status` nullable columns + docstring updates to `HardwareDevice`
- `quirk/db.py` - Added `_IDENTITY_HW_COLUMNS` tuple, registered in `_ADDITIVE_MIGRATIONS`
- `quirk/config.py` - Added `ScanCfg.hardware_history_retention_days: int = 180` (annotation, `__init__` param, `__init__` assignment)
- `tests/test_hardware_device_model.py` - Column-contract, nullability, and create/query round-trip tests for the three new columns
- `tests/test_db_migrations.py` - `test_identity_columns_migrate_onto_pre_existing_table` (legacy-table retrofit + idempotency)
- `tests/test_config.py` - Default-value and YAML-override tests for `hardware_history_retention_days`

## Decisions Made
- `match_confidence` (high|low) is a new, separate column from the existing `confidence` (high|medium|low|unknown) column per D-04/D-05 — cross-scan identity match confidence vs. probe-result confidence. Guarded by an explicit inequality assertion in the new test.
- `hardware_history_retention_days` default of 180 deliberately does not reuse the project's 90-day `STALENESS_THRESHOLD_DAYS` convention (D-11) — that constant governs catalog/matrix freshness, this governs engagement-history retention.
- `quirk/interactive.py` left untouched, matching the existing precedent of omitting `nmap_port_scope`/`openapi_spec_path` from the setup wizard's direct `ScanCfg(...)` construction.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Schema foundation is in place for Plan 02 (population), Plan 03 (read-side filtering), and Plan 04 (retention purge consuming `hardware_history_retention_days`). No blockers.

---
*Phase: 154-identity-data-model-foundation*
*Completed: 2026-08-14*
