# Backlog 999.88 — `quirk scheduler` likely passes unsupported flags to run_scan

**Type:** bug (suspected — needs audit)
**Source:** v5.4 debug session `sensor-enroll-id-mismatch`, 2026-05-26
**Candidate for:** v5.5

## Problem

While fixing `_run_local_scan` (which passed a nonexistent `--output` flag to `run_scan`
→ argparse fatal exit 2, scan never ran), the debugger noted the `quirk scheduler` path
appears to invoke `run_scan` with the same unsupported `--output` / `--target` flags.
If so, scheduled scans exit 2 and never run — the same class of bug just fixed in
`sensor_cmd.py`, independently affecting the scheduler.

## Fix

Audit `scheduler_cmd.py`'s `run_scan` invocation against `run_scan.py`'s actual argparse
surface. Remove unsupported flags, anchor output via `cwd` + `cfg.output.db_path` as done
for the sensor path, and add a regression test that runs a scheduled scan end-to-end (or
asserts the invocation only uses supported flags).

## References

- `.planning/debug/sensor-enroll-id-mismatch.md` (orchestrator notes — out-of-scope follow-up)
- `quirk/cli/scheduler_cmd.py`
- Fix precedent: commit `84e770e` (`_run_local_scan` in `quirk/cli/sensor_cmd.py`)
