---
phase: 171-resume-ux-tail
plan: 01
subsystem: infra
tags: [resume, checkpoint, sqlite, cli, run_scan]

# Dependency graph
requires:
  - phase: 163-discovery-batch-checkpoint
    provides: "Per-batch discovery:batch-N checkpoint/resume-skip guard — the correct, already-working mechanism this plan deliberately does not touch"
provides:
  - "_resume_already_complete_message() helper in run_scan.py — pure function deciding whether a resume is a no-op"
  - "Stage-level short-circuit in main()'s --resume-scan-id block: resuming a scan whose 'reports' checkpoint is completed now exits 0 with a clear message and writes zero new checkpoint rows"
affects: [171-02, 171-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure decision helper + thin call-site wiring, kept adjacent to existing sibling helpers (_stage_completed, _batch_stage_completed) for discoverability"
    - "Structural (ast/regex source-position) tests alongside unit tests to make a passing mirror test unable to mask an unwired call site"

key-files:
  created:
    - tests/test_resume_already_complete_shortcircuit.py
  modified:
    - run_scan.py

key-decisions:
  - "D-01 (locked, from 171-CONTEXT.md): exit 0, not a coded error — resume is idempotent, an already-done scan is not a failure"
  - "No --force flag — rejected in CONTEXT.md as unnecessary CLI surface for a tail-end cleanup phase"
  - "Short-circuit reads reports_completed_at from the already-loaded _cps list (next(... , None) generator) rather than issuing a second DB query"

requirements-completed: [RESUME-05]

# Metrics
duration: 25min
completed: 2026-08-28
---

# Phase 171 Plan 01: Resume-already-complete short-circuit Summary

**Resuming a scan whose `reports` checkpoint is already `completed` now exits 0 with `Scan <id> is already complete (finished <timestamp>); nothing to resume.` and writes zero new checkpoint rows, instead of silently re-running discovery/inventory/reports and re-appending checkpoint rows on every resume.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-28T20:12:00Z
- **Completed:** 2026-08-28T20:37:21Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Reproduction (before fixing)

Seeded a fresh sqlite DB via `quirk.db.init_db` with three `ScanCheckpoint` rows
(`discovery`, `inventory`, `reports`, all `status="completed"`) for a synthetic
`scan_run_id`. Pointed a scratch copy of `config.yaml`'s `output.db_path` at that
same file (required — the resume query in `main()` reads `cfg.output.db_path`,
not `args.db_path`; using two different paths is a silent no-op, matching the
documented trap). Ran:

```
python run_scan.py --config <scratch-config.yaml> --db-path <seeded.db> --resume-scan-id <scan_run_id>
```

**Before the fix:** the process proceeded past the stale-checkpoint warning and
`_resumed_endpoints` load, ran fingerprinting/DNSSEC/SAML/Kerberos stages, and
re-wrote checkpoint rows — `scan_checkpoints` row count grew from 3 to 8 before
the process was killed mid-scan (it never printed any "already complete"
message and never exited early). This confirms RESUME-05 as described in
171-CONTEXT.md: the bug is real, stage-level, and reproducible from a cold
seeded DB, not just from a live scan session.

**After the fix:** the same repro now prints
`Scan 2026-08-27T12:00:00 is already complete (finished 2026-08-28T20:36:17.141525); nothing to resume.`,
exits 0, and `scan_checkpoints` row count is unchanged (3 -> 3).

**Batch-row control check:** re-seeded a second DB with only `discovery` and
`inventory` completed (no `reports` row — an in-progress scan). Resume
proceeded exactly as before the fix: no short-circuit message printed, stage
work ran, and `scan_checkpoints` row count grew (2 -> 7) — confirming the
in-progress path and the Phase 163 batch-row mechanism are bit-for-bit
unaffected by this change.

## Accomplishments
- Reproduced RESUME-05 against a seeded DB before writing any fix code
- Added `_resume_already_complete_message()` — pure helper, module-level, next to `_stage_completed`/`_batch_stage_completed`
- Wired the short-circuit into `main()`'s `--resume-scan-id` block, immediately after `_completed_stages` is computed and before the stale-checkpoint warning, `_resumed_endpoints` load, and every stage's checkpoint write
- 6 tests (3 pure-logic unit tests, 2 structural source-position tests, 1 signature-contract sanity test) — all pass, no subprocess spawned
- Verified batch-row behavior (Phase 163 DISC-08) and RVW-001/RVW-003 resume-adjacent suites are untouched (58 tests total across `test_discovery_batch_checkpoint.py`, `test_rvw003_scan_session_identity.py`, `test_rvw001_endpoint_single_persist.py`, `test_run_scan_otics_ssh_gate.py`, `test_run_scan_codesign_wiring.py`)

## Task Commits

TDD task, two commits (RED then GREEN):

1. **RED — failing test** - `d8468c0` (test): added the 6-test file; all 6 failed for the right reason (`_resume_already_complete_message` did not exist)
2. **GREEN — implementation** - `629a8cb` (feat): added the helper + call-site wiring; all 6 tests pass; also fixed 2 test-regex self-inflicted bugs (def-line self-match, multi-line `write_scan_checkpoint(` call) discovered while running the tests against the real source

**Plan metadata:** (this commit, following SUMMARY.md write)

## Files Created/Modified
- `run_scan.py` — new `_resume_already_complete_message()` helper (~15 lines, next to `_stage_completed`); short-circuit call site + `print()`/`sys.exit(0)` wired into the `--resume-scan-id` block, before the stale-checkpoint warning
- `tests/test_resume_already_complete_shortcircuit.py` — 6 tests: 3 unit (in-progress returns None, complete-with-timestamp message contents, complete-with-None-completed_at does not raise), 2 structural (call site precedes inventory/reports checkpoint writes; `sys.exit(0)` within 5 lines of the call site), 1 signature sanity check

## Decisions Made
- Read `reports_completed_at` from the already-loaded `_cps` list via `next(..., None)` rather than a second DB query — `_cps` already contains every completed/partial checkpoint row for this `scan_run_id`, so no extra I/O is needed
- Placed the short-circuit strictly between `_completed_stages = {...}` and the stale-checkpoint warning, per the plan's `<interfaces>` ordering contract — an already-complete scan should never reach the stale-checkpoint warning or the `_resumed_endpoints` load, both of which would be wasted/misleading work
- `SystemExit` from `sys.exit(0)` inside the `with get_session(...) as _db:` block is a `BaseException` subclass and is not caught by the surrounding `except Exception as exc:` — verified this by manual repro (exit code 0 observed, not routed through the "Failed to load resume state" fallback)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed two self-inflicted test-regex bugs in the RED-phase test file**
- **Found during:** GREEN implementation, first post-fix test run
- **Issue:** `test_short_circuit_call_site_precedes_stage_checkpoint_writes` and `test_short_circuit_exits_immediately` used a bare substring match for `_resume_already_complete_message(` that also matched the function's own `def` line (which appears earlier in the file than the call site), and a single-line regex for the inventory `write_scan_checkpoint(` call that didn't account for the real call being split across two lines.
- **Fix:** Excluded the `def` line from both call-site searches; loosened the inventory regex to `write_scan_checkpoint\(\s*args\.db_path, scan_run_id, "inventory"` to match across the line break.
- **Files modified:** tests/test_resume_already_complete_shortcircuit.py
- **Verification:** All 6 tests pass against the real implementation; re-ran `python -m compileall run_scan.py` with no errors
- **Committed in:** 629a8cb (part of GREEN task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1, test-only, no product code affected)
**Impact on plan:** Cosmetic — both fixes were in test assertions I wrote in the RED commit, not in the plan's contract. No scope creep; the plan's specified behavior (5 tests) was preserved, with a 6th signature-sanity test added for extra safety.

## Issues Encountered
- Manual reproduction initially showed "0 stages complete" on resume even against a seeded, populated DB — traced to the resume query in `main()` reading `cfg.output.db_path` (from `--config`) rather than `args.db_path` (from `--db-path`); these are two independently-settable paths in `run_scan.py`. Resolved by pointing a scratch copy of `config.yaml`'s `output.db_path` at the same seeded DB file used for `--db-path`. This is a pre-existing dual-path-argument quirk unrelated to RESUME-05 and out of scope for this plan — noted here for future resume-related debugging, not fixed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
RESUME-05 closed. Plan 171-02 (RESUME-06, `--list-resumable` Target column derivation) is independent of this change and can proceed. No blockers.

---
*Phase: 171-resume-ux-tail*
*Completed: 2026-08-28*

## Self-Check: PASSED

- FOUND: run_scan.py
- FOUND: tests/test_resume_already_complete_shortcircuit.py
- FOUND: .planning/phases/171-resume-ux-tail/171-01-SUMMARY.md
- FOUND commit: d8468c0 (RED)
- FOUND commit: 629a8cb (GREEN)
- FOUND commit: 0d77cc0 (docs: complete plan execution)
