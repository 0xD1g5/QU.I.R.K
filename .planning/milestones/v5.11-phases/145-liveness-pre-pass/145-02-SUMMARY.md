---
phase: 145-liveness-pre-pass
plan: 02
subsystem: discovery
tags: [nmap, liveness-probe, batch-loop, run_scan, privilege-detection]

# Dependency graph
requires:
  - phase: 145-liveness-pre-pass (plan 01)
    provides: NmapHostStatus, parse_nmap_host_status(), run_nmap_liveness_check() primitives
affects: [146-progress-scaling-disclosure (Phase 146 consumes liveness_skip rows for undetermined-host disclosure)]
provides:
  - "_is_privileged() and _emit_liveness_fallback_advisory() in run_scan.py"
  - "Per-batch liveness pre-pass filter wired into the Phase 144 nmap batch loop"
  - "liveness_skip and privilege_fallback CryptoEndpoint categories in the scan artifact"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Separate liveness_endpoints accumulator merged into error_endpoints only after the partial-failure snapshot, keeping normal liveness skips out of ScanCheckpoint partial-failure semantics"
    - "Fail-open on liveness-primitive errors (RuntimeError -> sweep entire batch unfiltered) and on hosts absent from pre-pass results (excluded-set derivation, not included-set)"

key-files:
  created:
    - tests/test_liveness_prepass.py
  modified:
    - run_scan.py
    - quirk/models.py

key-decisions:
  - "liveness_endpoints kept as a dedicated list, distinct from error_endpoints, so _collect_stage_partial_failures never sees liveness_skip/privilege_fallback rows and the discovery ScanCheckpoint status is unaffected by normal skips (D-05)"
  - "Privilege check (_is_privileged()) evaluated exactly once per scan, only inside the nmap batch-loop branch, so the advisory never fires on cache-hit or nmap-absent branches where no pre-pass runs"
  - "Survivor set computed by excluding down hosts from the batch (not by including up hosts), so a host nmap omitted entirely from the liveness XML defaults to being swept rather than silently dropped"

requirements-completed: [DISC-03]

duration: ~20min
completed: 2026-08-10
---

# Phase 145 Plan 02: Wire Liveness Pre-Pass into the Discovery Batch Loop Summary

**Each Phase 144 discovery batch now runs a cheap nmap `-sn -PS<ports>` liveness pre-pass before its full port sweep, sweeping only responsive hosts and recording every skipped host as a `liveness_skip` CryptoEndpoint row, with a once-per-scan privilege-downgrade advisory.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-10T13:52:00Z (approx)
- **Completed:** 2026-08-10T13:59:43Z
- **Tasks:** 2 completed
- **Files modified:** 3 (2 production, 1 new test file)

## Accomplishments
- `_is_privileged()` and `_emit_liveness_fallback_advisory()` added to `run_scan.py`, implementing D-02 (getattr-guarded `os.geteuid()`, `None` on platforms without it) and D-01 (logger message + one `privilege_fallback` CryptoEndpoint advisory row per call)
- `scan_error_category`'s inline comment in `quirk/models.py` extended with `liveness_skip` and `privilege_fallback` (comment-only, no schema/migration change — verified `git diff --stat` shows exactly 1 changed line)
- The Phase 144 nmap batch loop in `run_scan.py` now runs `run_nmap_liveness_check()` per batch before `run_nmap_discovery()`, sweeping only survivors, recording down hosts as `liveness_skip` rows with real host identity, short-circuiting fully-dead batches before spawning a sweep subprocess, and failing open (sweep unfiltered) on `RuntimeError` from the pre-pass itself
- `liveness_endpoints` kept as a separate accumulator from `error_endpoints`, merged in only after `_collect_stage_partial_failures` snapshots the stage — normal liveness skips never flip the discovery `ScanCheckpoint` to `partial`
- `tests/test_liveness_prepass.py` — 11 tests covering privilege detection (3 states), advisory row shape + double-call behavior, batch-filter survivor computation, liveness_skip row shape, all-dead-batch zero-sweep-call short-circuit, fail-open on absent-from-results hosts, fail-open on pre-pass RuntimeError, and exclusion of liveness rows from `_collect_stage_partial_failures`

## Task Commits

Each task was committed atomically:

1. **Task 1: Privilege detection + fallback-advisory helper + models.py category comment** - `4a36033` (feat)
2. **Task 2: Insert the liveness pre-pass into the Phase 144 batch loop** - `9001db8` (feat)

## Files Created/Modified
- `run_scan.py` - Added `_is_privileged()`, `_emit_liveness_fallback_advisory()`; imported `run_nmap_liveness_check`; inserted the per-batch pre-pass step ahead of `run_nmap_discovery()`, changed the sweep call's `targets=` argument from `batch` to `sweep_targets`, added the once-per-scan privilege-fallback advisory call, and merged `liveness_endpoints` into `error_endpoints` after the discovery `ScanCheckpoint` write
- `quirk/models.py` - Extended the `scan_error_category` inline comment with `liveness_skip`/`privilege_fallback` and the Phase 145 D-05 provenance tag
- `tests/test_liveness_prepass.py` - New file; 11 tests across both tasks

## Decisions Made
- Followed the plan's exact accumulator-separation and once-per-scan gating design (D-02, D-05) with no deviation from the specified behavior.
- Test file mirrors `tests/test_nmap_provider.py::_run_batched_discovery`'s existing convention (a loop-shape-mirroring helper plus focused per-behavior tests) rather than invoking `main()`.

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria greps/counts matched expected values on first pass.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Every liveness-skipped host now has a queryable `CryptoEndpoint` row (`scan_error_category="liveness_skip"`) with its real host identity — ready for Phase 146's undetermined-host disclosure work (DISC-04..07).
- `privilege_fallback` advisory rows are available for the same downstream disclosure surfaces.
- Discovery `ScanCheckpoint` partial-failure semantics from Phase 144 remain unchanged for normal liveness skips.

## Verification

- `pytest tests/test_liveness_prepass.py tests/test_nmap_provider.py tests/test_nmap_parser.py tests/test_nmap_scope_args.py tests/test_jobs_nmap_scope_cap.py -x -q` — 38 passed
- `python -m compileall run_scan.py quirk/models.py quirk/discovery/` — exit 0
- Full suite (`pytest -q`, default `not slow`) — 2948 passed, 104 failed, 8 skipped, 60 deselected. All 104 failures are pre-existing baseline issues unrelated to this plan (Playwright browser-context errors, SSRF DNS-resolution blocks in sandboxed test env, stale version-string assertions, unrelated pre-existing scanner/sensor test debt) — verified via `grep -i "nmap\|liveness\|discovery"` against the failure list, which returned zero matches.

---
*Phase: 145-liveness-pre-pass*
*Completed: 2026-08-10*

## Self-Check: PASSED

All modified/created files exist on disk and both task commits (`4a36033`, `9001db8`) are present in git log.
