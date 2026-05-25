---
phase: 105-servicenow-ticketing
plan: "01"
subsystem: ticketing
tags: [servicenow, urllib, ticketing, dedup, ssrf, basic-auth, table-api]

# Dependency graph
requires:
  - phase: 104-jira-ticketing
    provides: TicketingChannel ABC + dispatch_finding + compute_fingerprint + IntegrationDelivery model

provides:
  - ServiceNowChannel(TicketingChannel) implementing 3 abstract methods via urllib Table API
  - ServiceNowTicketingCfg dataclass + _parse_servicenow_cfg parser in config.py
  - Wave-0 test scaffold: 9 mocked-urllib tests covering TICKET-02 + TICKET-04 behaviors

affects: [105-02, 105-03, cli-ticketing-dispatch]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ServiceNowChannel subclasses TicketingChannel — pure additive, zero changes to base/jira
    - urllib Build+opener pattern with _NoRedirectHandler (copied from webhook.py)
    - Basic auth header resolved from env-var names at __init__, stored only on self._auth_header
    - sysparm_query=correlation_id=<fp> for dedup GET; sys_id (not INC-number) for PATCH URL
    - Config parser returns None on any validation failure (https-only, non-empty env-var names)

key-files:
  created:
    - quirk/ticketing/servicenow.py
    - tests/test_ticketing_servicenow.py
  modified:
    - quirk/ticketing/config.py

key-decisions:
  - "Return sys_id (not INC-number) from create_issue_from_finding — INC-number causes PATCH 404 (Pitfall 2)"
  - "PATCH (not POST/PUT) for work_notes — POST creates hidden journal entry not visible in task UI (KB0623936)"
  - "_NoRedirectHandler copied verbatim from webhook.py — blocks post-validation redirect SSRF bypass"
  - "https:// enforced at config parse time (returns None for http://) before validate_external_url runs"
  - "All ServiceNow imports are lazy (in-body) in tests to allow RED-state collection"

patterns-established:
  - "urllib.request.Request(method='PATCH') for journal-append work_notes entries"
  - "compute_fingerprint NEVER overridden in subclasses — SHA256(host:port::title) is cross-backend identity"
  - "Test _FakeOpener callback receives the Request object for method/data assertions"

requirements-completed: [TICKET-02]

# Metrics
duration: 5min
completed: 2026-05-25
---

# Phase 105 Plan 01: ServiceNow Ticketing Channel Summary

**ServiceNowChannel(TicketingChannel) via stdlib urllib Table API with SHA256 dedup, Basic-auth, SSRF guard, and redirect-blocking — proving TICKET-04 one-abstraction holds with a second backend**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-25T12:53:04Z
- **Completed:** 2026-05-25T12:57:35Z
- **Tasks:** 3 (Task 0 Wave-0 tests, Task 1 config, Task 2 implementation)
- **Files modified:** 3

## Accomplishments

- Created `quirk/ticketing/servicenow.py` with `ServiceNowChannel(TicketingChannel)` implementing
  all 3 abstract methods via stdlib urllib: GET (find by correlation_id), POST (create incident,
  returns sys_id), PATCH (append work_notes journal entry)
- Extended `quirk/ticketing/config.py` with `ServiceNowTicketingCfg` dataclass and `_parse_servicenow_cfg`
  parser (https-only enforcement, env-var name validation, table default "incident")
- Delivered 9 mocked-urllib tests covering all TICKET-02 + TICKET-04 behaviors; all 9 pass green

## Task Commits

Each task was committed atomically:

1. **Task 0 (Wave-0): Write failing tests for ServiceNowChannel + config** - `1b72561` (test)
2. **Task 1: Add ServiceNowTicketingCfg + _parse_servicenow_cfg to config.py** - `aa56940` (feat)
3. **Task 2: Implement ServiceNowChannel** - `ce0d290` (feat)

## Files Created/Modified

- `quirk/ticketing/servicenow.py` — ServiceNowChannel(TicketingChannel) with 3 abstract methods,
  _NoRedirectHandler, Basic auth via env vars, zero compute_fingerprint override
- `quirk/ticketing/config.py` — ServiceNowTicketingCfg dataclass + _parse_servicenow_cfg +
  servicenow field on TicketingCfg + _parse_ticketing_cfg wiring
- `tests/test_ticketing_servicenow.py` — 9 mocked-urllib tests: create_incident,
  dedup_then_work_notes, correlation_id_is_fingerprint, http_instance_url_rejected,
  missing_instance_url, missing_env_fields_rejected, https_valid_config, ssrf_guard,
  credentials_not_in_logs

## Decisions Made

- All ServiceNowChannel imports in test file are lazy (inside test bodies) to enable pytest
  collection in RED state before implementation exists — deviation from module-level import
  pattern in jira tests, but required for correct TDD flow
- `_parse_servicenow_cfg` placed after `_parse_jira_cfg` in config.py to maintain logical ordering
  and avoid forward-reference issues (both called from `_parse_ticketing_cfg`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Moved config imports to lazy in-body style in test file**
- **Found during:** Task 0 (Wave-0 test collection)
- **Issue:** Module-level `from quirk.ticketing.config import ServiceNowTicketingCfg, _parse_servicenow_cfg`
  caused collection failure (`ImportError`) because the symbols don't exist yet in RED state.
  The plan requires all 9 tests to be *collected* (not just defined) in RED state.
- **Fix:** Made all `ServiceNowTicketingCfg` and `_parse_servicenow_cfg` imports lazy (inside
  test function bodies or helpers), matching the `ServiceNowChannel` lazy-import pattern.
  This is consistent with the plan requirement that `ServiceNowChannel` be imported lazily.
- **Files modified:** `tests/test_ticketing_servicenow.py`
- **Verification:** `pytest --collect-only` shows 9 tests collected; all 9 FAIL in RED state;
  all 9 PASS after implementation
- **Committed in:** `1b72561` (Task 0 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — lazy import for RED-state collection)
**Impact on plan:** Required for correct TDD flow; no scope creep; all 9 acceptance criteria met.

## Issues Encountered

None — implementation mapped cleanly from PATTERNS.md and RESEARCH.md. All three urllib
methods (GET/POST/PATCH) worked first try against the mocked opener. The only unexpected
issue was the RED-state collection failure (documented as deviation above).

## User Setup Required

None - no external service configuration required for this plan. ServiceNow credentials
are configured via env vars at runtime (`user_env`/`password_env` names in config YAML).

## Next Phase Readiness

- `ServiceNowChannel` is ready for Phase 105-02 (CLI `--backend servicenow` dispatch in `ticket_cmd.py`)
- `ServiceNowTicketingCfg` is registered in `TicketingCfg.servicenow` field — config loading works end-to-end
- `git diff --quiet quirk/ticketing/base.py quirk/ticketing/jira.py` exits 0 (TICKET-04 zero-change proven)
- `grep -n 'def compute_fingerprint' quirk/ticketing/servicenow.py` returns no output (inheritance confirmed)
- All 17 ticketing tests (jira + servicenow) pass green

## Threat Surface Scan

No new threat surface beyond what the plan's threat model anticipated:
- All four mitigations (T-105-01 through T-105-04) are implemented and verified by tests
- T-105-05 (dedup) covered by test_dedup_then_work_notes
- T-105-SC: zero new pip deps confirmed (stdlib urllib only)

---
*Phase: 105-servicenow-ticketing*
*Completed: 2026-05-25*
