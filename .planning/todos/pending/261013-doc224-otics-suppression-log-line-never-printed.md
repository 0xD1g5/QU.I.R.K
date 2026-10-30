---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS (fork B4); ledger row DCL-OPS-B-0385 (docs/operators-guide.md §12 "Where to look when PLCs stop being fingerprinted")
priority: medium
area: quirk/cli/scheduler_cmd.py (_materialize_scan_config suppression log), run_scan.py (no logging configuration)
status: pending
resolves_phase: null
owner: "999.136"
---

# The OT/ICS suppression log line is never shown to an operator running `quirk scheduler run`

When a scheduled dispatch strips `enable_modbus`/`enable_bacnet` (cadence floor or no opt-in), the only signal is
`logging.getLogger(__name__).info(suppression_log_line(...))` at `quirk/cli/scheduler_cmd.py:227-229`. Nothing in
`quirk/` or `run_scan.py` calls `logging.basicConfig`/`dictConfig` or attaches a handler (grep for
`basicConfig|dictConfig` returns no matches), so the logger's effective level is WARNING (30) and the root logger has
no handlers: the INFO record is dropped.

Probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc2-ops-b4-otics-suppression-log-probe.sh`):
import `run_scan` (the real entry module), call `_materialize_scan_config` with a sub-floor schedule and a config
enabling Modbus/BACnet with the opt-in -> generated connectors `{'enable_recurring_otics': True}` (keys stripped),
effective level 30, root handlers `[]`, 0 bytes on stderr.

The operators-guide previously called this line "the single place to look first" when OT/ICS coverage silently stops.
The doc now points operators at the run's `scan-config.generated.yaml` and states the line is not printed by default.
A safety control that silently removes coverage should be visible.

- [ ] Emit the suppression at WARNING (or print it to the scheduler console / record it on the `scheduled_runs` row).
- [ ] Test that `quirk scheduler run --once` with a sub-floor schedule produces a visible message.
- [ ] Restore the operators-guide "check the scheduler output" guidance once fixed.

## Feasibility & Effort

- **CONFIRMED** by the probe above and by reading `quirk/cli/scheduler_cmd.py:216-229` (INFO-level log is the only
  signal) and `run_scan.py:1381-1384` (the `scheduler` interception calls `run_scheduler` with no logging setup).
- **LIKELY** effort **S**: change the level to `warning` or add a console print; `tests/test_otics_cadence_floor.py`
  already captures the record with `caplog` (`test_dispatch_time_sub_floor_strips_otics_keys`), so the test change is
  small. **UNKNOWN**: whether a persistent record on `scheduled_runs` is wanted (that is an M with a migration).
  No spike needed.
