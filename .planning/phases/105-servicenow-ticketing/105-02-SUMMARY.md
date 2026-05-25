---
phase: 105-servicenow-ticketing
plan: "02"
subsystem: ticketing
tags: [servicenow, jira, cli, dispatch, backend-selection, argparse]

# Dependency graph
requires:
  - phase: 105-01
    provides: ServiceNowChannel + ServiceNowTicketingCfg in quirk/ticketing/servicenow.py + config.py

provides:
  - --backend {jira,servicenow} flag in quirk ticket create CLI (default: jira)
  - Backend-neutral extra-gate advisory message
  - Conditional dispatch: servicenow→ServiceNowChannel, jira→JiraChannel
  - 3 new CLI dispatch tests (servicenow happy-path, missing-config exit-2, default-jira regression)

affects: [105-03, cli-ticketing-dispatch]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - argparse choices=["jira","servicenow"] for closed backend selection (T-105-07 mitigation)
    - Lazy import pattern inside backend branch (from quirk.ticketing.servicenow import ServiceNowChannel)
    - Backend-conditional cfg guard before channel construction (cfg.servicenow is None → exit 2)

key-files:
  created: []
  modified:
    - quirk/cli/ticket_cmd.py
    - tests/test_ticket_cmd.py

key-decisions:
  - "extra-gate message neutralized to 'Ticketing skipped' (backend-neutral per RESEARCH recommendation — gate is shared, jira extra is the trigger)"
  - "cfg is None check split from cfg.jira is None — allows backend-conditional sub-block check after confirming config loaded"
  - "Lazy ServiceNowChannel import inside servicenow branch mirrors existing JiraChannel lazy-import pattern"

# Metrics
duration: 5min
completed: 2026-05-25
---

# Phase 105 Plan 02: CLI Backend Dispatch Summary

**`--backend {jira,servicenow}` flag wired to `quirk ticket create` with conditional dispatch, backend-neutral extra-gate advisory, and 3 new CLI tests covering servicenow happy-path, missing-config exit-2, and default-jira regression**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-05-25
- **Tasks:** 2 (Task 1: ticket_cmd.py, Task 2: tests)
- **Files modified:** 2

## Accomplishments

- Extended `quirk/cli/ticket_cmd.py` with `--backend {jira,servicenow}` argparse flag (default: jira)
- Neutralized the is_extra_available advisory from "Jira ticketing skipped" to backend-neutral "Ticketing skipped"
- Replaced hard-coded `cfg.jira is None` check with backend-conditional dispatch:
  - `cfg is None` → exit 2 (config not found)
  - `--backend servicenow` + `cfg.servicenow is None` → exit 2 with servicenow-specific error
  - `--backend servicenow` + servicenow configured → lazy import + `ServiceNowChannel(cfg.servicenow)`
  - default jira + `cfg.jira is None` → exit 2 with jira-specific error
  - default jira + jira configured → lazy import + `JiraChannel(cfg.jira)` (unchanged behavior)
- Added 3 new tests to `tests/test_ticket_cmd.py` — all 8 tests in the file pass green

## Task Commits

1. **Task 1: Add --backend flag + neutral extra-gate + conditional dispatch** - `8ef95d7` (feat)
2. **Task 2: Add CLI dispatch tests** - `96f4654` (test)

## Files Created/Modified

- `quirk/cli/ticket_cmd.py` — --backend argument, neutralized advisory, backend-conditional dispatch block
- `tests/test_ticket_cmd.py` — test_backend_servicenow, test_backend_servicenow_missing_config, test_default_backend_uses_jira added

## Decisions Made

- Extra-gate message neutralized to "Ticketing skipped" — gate is shared CLI-level infrastructure; Jira-specific language was misleading when ServiceNow is the selected backend
- `cfg is None` guard separated from sub-block check — allows a single config-not-found error path before branching on backend, keeping the error messages precise
- Lazy `from quirk.ticketing.servicenow import ServiceNowChannel` inside the servicenow branch — mirrors the existing JiraChannel lazy-import pattern; consistent with the optional-extra lazy-import pattern documented in project feedback

## Deviations from Plan

None — plan executed exactly as written. Both tasks mapped directly to PATTERNS.md without any blocking issues or structural discoveries.

## Known Stubs

None — all dispatch paths are fully wired to real channel implementations (ServiceNowChannel from Plan 105-01, JiraChannel from Plan 104-01).

## Threat Surface Scan

No new threat surface beyond the plan's threat model:
- T-105-07 (Spoofing via --backend): `choices=["jira","servicenow"]` enforced by argparse — any other value rejected before dispatch
- T-105-08 (exception text): existing `safe_str(exc)` wrapper preserved in the outer except block
- T-105-09 (silent skip): `is_extra_available("tickets")` gate retained at top; advisory now backend-neutral

## Self-Check

- `quirk/cli/ticket_cmd.py` exists and contains `--backend` flag: FOUND
- `tests/test_ticket_cmd.py` defines `test_backend_servicenow`: FOUND
- Commit `8ef95d7` exists: FOUND
- Commit `96f4654` exists: FOUND
- `python -m pytest tests/test_ticket_cmd.py -q`: 8 passed
- `python -m compileall quirk/cli/ticket_cmd.py`: OK
- `grep 'Jira ticketing skipped' quirk/cli/ticket_cmd.py`: no match (neutralized)

## Self-Check: PASSED

---
*Phase: 105-servicenow-ticketing*
*Completed: 2026-05-25*
