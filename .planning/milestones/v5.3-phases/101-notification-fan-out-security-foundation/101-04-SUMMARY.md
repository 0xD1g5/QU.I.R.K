---
phase: 101-notification-fan-out-security-foundation
plan: "04"
subsystem: notify/dispatcher
tags: [security, notify, dispatcher, scheduler, isec, tdd, docs]
dependency_graph:
  requires:
    - phase: 101-01
      provides: safe_str-integration-patterns, IntegrationDelivery model
    - phase: 101-02
      provides: NotifyCfg, load_notifications_config, DriftSummary, to_integration_payload
    - phase: 101-03
      provides: send_slack, send_email, send_webhook channels
  provides:
    - quirk.notify.dispatcher (dispatch_notifications, should_notify, _find_two_sessions)
    - scheduler dispatch hook after _dispatch_schedule db.commit()
    - docs/configuration.md Notifications section
    - UAT-101-01..04 in UAT-SERIES.md
    - Obsidian Phase-101 note
  affects: [103-siem, 104-jira, 105-servicenow]
tech-stack:
  added: []
  patterns:
    - conservative-trigger (new_high>0 OR score_delta<-floor; score_delta=None → False)
    - millisecond-session-discovery (func.strftime %Y-%m-%d %H:%M:%f, mirrors trends.py)
    - per-channel-fan-out-isolation (individual try/except per channel, IntegrationDelivery row)
    - deferred-import-scheduler-hook (from quirk.notify.dispatcher import dispatch_notifications inside try/except)
    - safe_str-in-audit-rows (ISEC-02 — error_summary always scrubbed before persistence)
key-files:
  created:
    - quirk/notify/dispatcher.py
    - tests/test_notify_dispatcher.py
  modified:
    - quirk/notify/__init__.py
    - quirk/cli/scheduler_cmd.py
    - docs/configuration.md
    - docs/UAT-SERIES.md
key-decisions:
  - "Dispatcher never receives config_path — config loaded via QUIRK_CONFIG_PATH env var (Pitfall 1 guard)"
  - "score_delta is None returns False from should_notify — explicit guard against first-scan alert storm (Pitfall 4)"
  - "Deferred import of dispatch_notifications inside scheduler_cmd try/except — avoids circular import + failure isolation"
  - "Scheduler try/except swallows delivery exceptions entirely — scan record always returned completed"
  - "Per-channel fan-out uses individual try/except + IntegrationDelivery row — one channel failure never blocks others"
requirements-completed: [NOTIFY-01, NOTIFY-02, NOTIFY-07, ISEC-02]
duration: ~30min
completed: "2026-05-25"
---

# Phase 101 Plan 04: Dispatcher + Scheduler Hook + Docs Summary

**Dispatcher wires conservative trigger (new HIGH/CRITICAL OR score regression, never first scan) to per-channel fan-out with IntegrationDelivery audit rows and safe_str secret scrubbing; scheduler hook wrapped in try/except so delivery failure never touches the committed scan record.**

## Performance

- **Duration:** ~30 minutes
- **Completed:** 2026-05-25
- **Tasks:** 3 (Task 1 TDD + Task 2 + Task 3 docs)
- **Files modified:** 6

## Accomplishments

- `dispatch_notifications` evaluates the conservative trigger, builds DriftSummary once, fans out to all enabled channels with per-channel isolation, and writes one IntegrationDelivery audit row per attempt
- Scheduler hook inserted after `_dispatch_schedule` final `db.commit()` in a try/except that swallows all delivery exceptions — scan record is never corrupted
- `should_notify` explicitly returns False when `score_delta is None` (first scan — Pitfall 4 guard)
- All error_summary fields always written via `safe_str(exc)` — Slack tokens and SMTP credentials are scrubbed before persistence (ISEC-02)
- `docs/configuration.md` Notifications section documents YAML block, env var convention, security controls, and audit log query
- UAT-101-01..04 added; Phase 101 Obsidian note written; UAT-Series synced to vault

## Task Commits

1. **Task 1 RED: failing dispatcher tests** - `198b5b1` (test)
2. **Task 1 GREEN: dispatcher implementation** - `a275d45` (feat)
3. **Task 2: scheduler dispatch hook** - `f74e92b` (feat)
4. **Task 3: docs, UAT-SERIES** - `7b8e148` (docs)

## Files Created/Modified

- `quirk/notify/dispatcher.py` — Core dispatcher: `_find_two_sessions`, `should_notify`, `dispatch_notifications`, pluggable `_channel_send_*` indirections
- `quirk/notify/__init__.py` — Re-exports `dispatch_notifications`
- `quirk/cli/scheduler_cmd.py` — Notification hook after final `db.commit()`, wrapped in try/except
- `tests/test_notify_dispatcher.py` — 12 TDD test cases: trigger/no-trigger/first-scan/MEDIUM-only, fan-out, failure isolation, secret scrub, scheduler isolation
- `docs/configuration.md` — Added "Notifications (v5.3+)" section
- `docs/UAT-SERIES.md` — Version 5.3.0-dev, Last Updated 2026-05-25, UAT-101-01..04

## Decisions Made

- Dispatcher uses `should_notify(report, threshold=abs(notify_cfg.trigger_score_floor))` — pulls threshold from config at dispatch time, default matches plan spec
- Per-channel delivery uses individual try/except blocks with `IntegrationDelivery` rows committed immediately after each attempt, not batched — ensures partial delivery is auditable
- run.scan_id bonus fix: when `run.scan_id is None`, set to `current_ts.isoformat()` and commit — improves audit row linkage for queries
- `logging.getLogger(__name__)` inline in the scheduler hook's except clause (deferred) since scheduler_cmd.py had no module-level `logger`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] logger not defined in scheduler_cmd.py**
- **Found during:** Task 2 — dispatcher raised RuntimeError in test, scheduler_cmd.py tried to log via `logger` which was not defined in that module
- **Issue:** `quirk/cli/scheduler_cmd.py` has no module-level `logger` variable; the hook's except clause attempted `logger.warning(...)` causing `NameError`
- **Fix:** Changed to `import logging as _logging` + `_logging.getLogger(__name__).warning(...)` inside the except clause
- **Files modified:** `quirk/cli/scheduler_cmd.py`
- **Verification:** `python -m pytest tests/test_notify_dispatcher.py -q` — 12/12 pass
- **Committed in:** f74e92b

---

**Total deviations:** 1 auto-fixed (Rule 1 — missing module-level logger)
**Impact on plan:** Necessary correctness fix. No scope creep.

## Known Stubs

None. All dispatch paths are fully implemented. No hardcoded empty values or placeholder text.

## Threat Surface Scan

No new network endpoints or auth paths introduced. The scheduler hook is purely internal — it calls the dispatcher after the scan is committed, and all outbound connections are made by the channel senders (already covered by ISEC-01 SSRF controls in Plan 03). No new schema changes (IntegrationDelivery table added in Plan 01). No new threat surface beyond what is documented in the plan's threat model (T-101-10 through T-101-13 — all mitigated).

## Self-Check: PASSED

Files created/modified:
- FOUND: quirk/notify/dispatcher.py
- FOUND: quirk/notify/__init__.py
- FOUND: quirk/cli/scheduler_cmd.py
- FOUND: tests/test_notify_dispatcher.py
- FOUND: docs/configuration.md
- FOUND: docs/UAT-SERIES.md

Commits verified in git log:
- FOUND: 198b5b1 (test(101-04): add failing dispatcher tests)
- FOUND: a275d45 (feat(101-04): implement dispatcher)
- FOUND: f74e92b (feat(101-04): wire notification dispatch hook)
- FOUND: 7b8e148 (docs(101-04): add Notifications section + UAT-101 series)

Acceptance criteria:
- `grep -c 'safe_str' quirk/notify/dispatcher.py` = 12 (>= 1 required)
- `grep -c 'config_path' quirk/notify/dispatcher.py` = 0
- `python -m pytest tests/test_notify_dispatcher.py -q` = 12 passed
- `python -m pytest tests/test_notify*.py tests/test_integration_deliveries_schema.py -q` = 105 passed
- `python -m compileall quirk/ -q` = exits 0
- Phase 101 Obsidian note: FOUND at /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-101-Notification-Fan-Out-Security-Foundation.md
- UAT-Series.md synced to vault
