---
phase: 147-backlog-drain-lifecycle-ledger-tail
plan: 01
subsystem: scanner
tags: [run_scan, ot-ics, modbus, bacnet, resume-scan, hardware-fingerprint, tdd]

# Dependency graph
requires:
  - phase: 141-ot-ics-fingerprinting-modbus-bacnet
    provides: "build_ot_supplemental_endpoints() + fingerprint_hardware(ot_only=True) OT/ICS supplemental fingerprint contract"
provides:
  - "run_ot_supplemental_and_persist() module-level helper in run_scan.py, hoisted above the ssh-stage if/else"
  - "Resume-path OT/ICS supplemental fingerprint coverage — DRAIN-01 fixed"
  - "Group C regression tests pinning the resume-path contract"
affects: [run_scan, hardware-fingerprinting, resume-scan-id]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hoisted phase helper called unconditionally on both branches of a stage if/else, rather than duplicated inside each branch"

key-files:
  created: []
  modified:
    - run_scan.py
    - tests/test_run_scan_otics_ssh_gate.py

key-decisions:
  - "Renamed the inner closure from _run_ot_supplemental_phase to _ot_supplemental_fn inside the new module-level helper, to keep the plan's grep-based acceptance criteria (old closure name fully removed from run_scan.py) satisfiable while still moving the closure body verbatim."
  - "ssh-stage checkpoint write reordered to occur BEFORE the hoisted hardware persist on the fresh-run branch (persist is advisory-only and already try/except-guarded, so this ordering is safe) — the checkpoint write itself was NOT moved out of the fresh-run else branch, preserving endpoint_count/partial_failure correctness on resume."

patterns-established:
  - "Resume-path parity: any run_scan.py phase whose inputs (targets/ssh_targets/confirmed_open_ports) are reconstructed identically on both the fresh-run and resume paths should be hoisted above the stage-specific if/else rather than nested inside one branch, to avoid an outer-gate skip bug on resume."

requirements-completed: [DRAIN-01]

duration: 12min
completed: 2026-08-11
---

# Phase 147 Plan 01: Resume-Path OT/ICS Supplemental Fix (DRAIN-01) Summary

**Fixed the `--resume-scan-id` outer-gate skip bug by hoisting `run_ot_supplemental_and_persist()` above `run_scan.py`'s ssh-stage if/else so a resumed scan whose ssh stage is already checkpointed complete still fingerprints OT-only (Modbus/BACnet, no-SSH) hosts.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-08-11T08:07:05-04:00
- **Completed:** 2026-08-11T08:09:18-04:00 (code) + verification/summary pass
- **Tasks:** 3 (2 code tasks + 1 full-suite regression gate)
- **Files modified:** 2

## Accomplishments
- Root-caused and fixed DRAIN-01: Phase 141 Plan 11's OT/ICS supplemental fingerprint pass previously lived only inside `run_scan.py`'s fresh-run `else` branch of the ssh-stage `if/else`, so a `--resume-scan-id` continuation whose `ssh` stage was already checkpointed complete never probed OT-only hosts.
- Extracted `run_ot_supplemental_and_persist()` as a module-level helper (adjacent to `build_ot_supplemental_endpoints()`) and moved the OT-supplemental fingerprint pass + hardware-device persist block into it verbatim.
- Called the new helper ONCE, unconditionally, immediately after the ssh-stage `if/else` closes — covering both the resume path (`if _stage_completed(...)`) and the fresh-run path (`else`).
- Preserved the invariant that the ssh-stage checkpoint (`write_scan_checkpoint(..., "ssh", ...)`) is written ONLY on the fresh-run branch, never re-written on resume (which would have reset `endpoint_count`/`partial_failure` using only the OT-only subset).
- Added 4 new Group C regression tests (RED→GREEN via TDD) pinning: (C1) the helper appends fingerprinted devices to `hw_batch` even with an empty `ssh_targets` list (the resume-path shape); (C2) the pass still routes through `_wrapped_phase` keyed `"ot_ics_supplemental"`; (C3) the helper is a no-op when both `enable_modbus`/`enable_bacnet` are False; (C4) the helper never calls `write_scan_checkpoint`.
- Verified the full test suite: only pre-existing, unrelated failures remain (confirmed via a temporary `git worktree` checkout at the pre-plan commit, running identical failing tests in isolation with identical failure messages).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Group C failing tests pinning the resume-path OT-supplemental contract** - `6abf8f7` (test) — RED state confirmed (`ImportError: cannot import name 'run_ot_supplemental_and_persist'`)
2. **Task 2: Extract run_ot_supplemental_and_persist() and hoist it above the ssh-stage if/else** - `0b4aa19` (feat) — GREEN state confirmed (11/11 tests pass)
3. **Task 3: Full-suite regression gate for the run_scan.py restructure** - no code commit (verification-only task; see below)

**Plan metadata:** committed as part of this summary/state update.

## Files Created/Modified
- `run_scan.py` - Added `run_ot_supplemental_and_persist()` module-level helper (hoisted phase + persist logic); removed the old `_run_ot_supplemental_phase` closure and its inline `if _hw_batch:` persist block from `main()`'s fresh-run `else` branch; added a single unconditional call site after the ssh-stage `if/else`; reordered the fresh-run branch so the ssh checkpoint write happens before the hoisted call (with an explanatory comment).
- `tests/test_run_scan_otics_ssh_gate.py` - Added Group C section (4 tests: C1-C4) plus a `_make_device()` fixture helper (constructs a real `HardwareDevice()` instance rather than `__new__`, since production code performs a normal attribute assignment `_dev.remediation_tier = ...` that requires SQLAlchemy instrumentation) and a module-docstring paragraph explaining the resume-path regression Group C pins.

## Decisions Made
- Renamed the inner closure `_run_ot_supplemental_phase` → `_ot_supplemental_fn` when moving it inside the new module-level helper, so the plan's acceptance criterion (`grep -n "_run_ot_supplemental_phase" run_scan.py` returns nothing) is satisfiable while still moving the closure body verbatim per the plan's `<action>` instructions.
- Kept `_ssh_pf = _collect_stage_partial_failures(...)` and `write_scan_checkpoint(args.db_path, scan_run_id, "ssh", ...)` lexically inside the fresh-run `else` branch, unmoved — this was a hard constraint from the plan (resume-checkpoint correctness) and was verified by re-reading the block post-edit.
- `db_path` is passed as `cfg.output.db_path` (matching the pre-existing behavior at the original call site) rather than `args.db_path`, since the original code used `cfg.output.db_path` for the `get_session()` call.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture `_make_device()` initially used `HardwareDevice.__new__()`, causing a downstream production-code `AttributeError`/`UnmappedInstanceError`**
- **Found during:** Task 2 verification (running Group C tests against the real implementation for the first time)
- **Issue:** The Group C test fixture originally constructed a `HardwareDevice` fixture via `HardwareDevice.__new__(HardwareDevice)` + direct `__dict__` writes (mirroring the existing Group A/B `_make_ep()` pattern for `CryptoEndpoint`). But the real helper's code performs a normal attribute assignment (`_dev.remediation_tier = assign_tier(_dev)`) on devices returned from `fingerprint_hardware()` — a SQLAlchemy-instrumented `__setattr__` that requires a properly mapped instance. A bare `__new__()` instance lacks this instrumentation, raising `UnmappedInstanceError` inside the `_wrapped_phase`-protected closure (silently swallowed as a `[]` return, causing the test's `hw_batch == [device]` assertion to fail with an empty list instead).
- **Fix:** Changed `_make_device()` to construct via the real `HardwareDevice(...)` constructor with all required non-nullable fields populated, giving it proper SQLAlchemy instrumentation.
- **Files modified:** `tests/test_run_scan_otics_ssh_gate.py`
- **Verification:** `python -m pytest tests/test_run_scan_otics_ssh_gate.py -x` — all 11 tests pass.
- **Committed in:** `0b4aa19` (part of Task 2 commit)

**2. [Rule 1 - Bug] Test `run_stats` fixtures initially missing the `"timings_sec"` key required by `_phase_timer`**
- **Found during:** Task 2 verification
- **Issue:** `_wrapped_phase` wraps calls in `_phase_timer(run_stats, phase_name)`, whose `__exit__` writes to `run_stats["timings_sec"][name]`. The Group C tests initially passed `run_stats: dict = {}`, causing a `KeyError('timings_sec')` inside the wrapped phase (silently captured as an "exception" phase result by `_wrapped_phase`'s own BaseException guard, again masking the real assertion failure as an empty `hw_batch`).
- **Fix:** Seeded all four Group C `run_stats` fixtures with `{"timings_sec": {}}`, matching the shape `main()` actually constructs.
- **Files modified:** `tests/test_run_scan_otics_ssh_gate.py`
- **Verification:** `python -m pytest tests/test_run_scan_otics_ssh_gate.py -x` — all 11 tests pass.
- **Committed in:** `0b4aa19` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — test-fixture bugs surfaced while driving the implementation to GREEN, not production-code defects)
**Impact on plan:** Both fixes were necessary to make the Group C tests actually exercise the intended code path instead of silently masking failures inside `_wrapped_phase`'s BaseException guard. No scope creep — production `run_scan.py` logic matches the plan's `<action>` instructions exactly.

## Issues Encountered
- The full `python -m pytest -q` suite reports 103 failures unrelated to this plan (SSRF/DNS-blocked network tests, missing Playwright browser binaries, stale version-string assertions expecting old release numbers, `pymodbus`/`bacpypes3` API-shape drift in `test_bacnet_scanner.py`/`test_modbus_scanner.py`, sensor-push validation-shape mismatches, etc.). Per the plan's Task 3 instructions, each was triaged against the pre-plan commit (`e973ad1`) using a temporary `git worktree add /tmp/preplan-check e973ad1 --detach` (removed after verification) — representative failing test files (`test_bacnet_scanner.py`, `test_modbus_scanner.py`, `test_qramm_staleness.py`, `test_sensor_cmd.py`, `test_openapi_scanner.py`) were re-run in isolation at the pre-plan commit and failed identically (same assertion messages, same exception types). `git diff --name-only e973ad1..HEAD` confirms this plan touched only `run_scan.py` and `tests/test_run_scan_otics_ssh_gate.py` (plus unrelated pre-existing `.planning/` docs/state changes from before this plan began). No new failures were introduced by this plan; none of the 103 pre-existing failures reference `run_scan.py`'s OT-supplemental code path.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
DRAIN-01 is fully closed: a `--resume-scan-id` continuation with `ssh` already checkpointed complete now runs the OT/ICS supplemental fingerprint pass and persists its devices, pinned by 4 new Group C regression tests, with no change to fresh-run behavior and no ssh-checkpoint re-write on resume. Ready for Phase 147 Plans 02-04 (DRAIN-02 BACnet CVE coverage, DRAIN-03 audit ledger closure, DRAIN-04 deferred-UAT re-triage) — this plan's scope was fully independent and did not touch any files those plans will need.

---
*Phase: 147-backlog-drain-lifecycle-ledger-tail*
*Completed: 2026-08-11*

## Self-Check: PASSED

All claimed files and commits verified present on disk / in git history.
