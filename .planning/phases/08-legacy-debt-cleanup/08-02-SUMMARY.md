---
phase: 08-legacy-debt-cleanup
plan: 02
subsystem: config
tags: [interactive, config, connectors, jwt, container, source]

# Dependency graph
requires:
  - phase: 03-scanner-coverage
    provides: ConnectorsCfg Phase 3 fields (enable_jwt, enable_container, enable_source, jwt_targets, container_targets, source_targets)
provides:
  - ConnectorsCfg without enable_windows_adcs (backward-compat pop in config_from_dict)
  - Interactive mode with correct AWS/Azure labels (not stub)
  - Interactive mode prompts for JWT, container, and source scanners with target lists
  - config.yaml without enable_windows_adcs
affects: [interactive-mode, config-loading, 08-legacy-debt-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "config_from_dict strips deprecated fields via dict comprehension before constructing dataclass — backward-compat pattern for field removal"

key-files:
  created: []
  modified:
    - quirk/config.py
    - quirk/interactive.py
    - config.yaml

key-decisions:
  - "Backward compat for enable_windows_adcs: dict comprehension exclude in config_from_dict rather than pop() — avoids mutating caller's dict"

patterns-established:
  - "Field removal pattern: exclude deprecated key in config_from_dict dict comprehension, remove from dataclass, update config.yaml in same commit"

requirements-completed: [D-03, D-04, D-05]

# Metrics
duration: 5min
completed: 2026-04-03
---

# Phase 08 Plan 02: Interactive Mode Cleanup Summary

**Removed enable_windows_adcs from ConnectorsCfg and interactive.py; added JWT/container/source scanner prompts with correct AWS/Azure labels**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-03T04:17:00Z
- **Completed:** 2026-04-03T04:22:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Removed `enable_windows_adcs: bool` from `ConnectorsCfg` dataclass; old config files with the field silently ignored via dict-comprehension filter in `config_from_dict`
- Stripped all `(stub)` labels from AWS/Azure prompts and renamed section header from "Connectors (stubs in v2)" to "Cloud Connectors"
- Added "Additional Scanners" section in `interactive_config()` with enable/target prompts for JWT, container, and source scanners

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove enable_windows_adcs from ConnectorsCfg and config_from_dict (D-04)** - `942ebb8` (fix)
2. **Task 2: Fix interactive mode labels and add Phase 3 scanner prompts (D-03, D-05)** - `676cc46` (fix)

## Files Created/Modified

- `quirk/config.py` - Removed `enable_windows_adcs: bool` field; added backward-compat exclusion in `config_from_dict`
- `quirk/interactive.py` - Fixed connector labels, removed ADCS prompt, added Phase 3 scanner prompts
- `config.yaml` - Removed `enable_windows_adcs: false` from connectors block

## Decisions Made

- Used dict comprehension (`{k: v for k, v in ... if k != "enable_windows_adcs"}`) instead of `pop()` in `config_from_dict` to avoid mutating the caller's raw dict

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- D-03, D-04, D-05 requirements fulfilled — interactive mode is clean for v4 users
- Remaining Phase 08 plans (08-03, 08-04) can proceed independently

---
*Phase: 08-legacy-debt-cleanup*
*Completed: 2026-04-03*
