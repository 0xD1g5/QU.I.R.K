---
phase: 69-deferred-blockers-scanner-cloud
plan: 01
subsystem: infra
tags: [resource-leak, sslyze, socket, threading, scanner, tls, ssh-fingerprint]

requires:
  - phase: 57-scanner-security-hardening
    provides: SNI placeholder line in _scan_one_sslyze (c8f89bf) — fix coexists with the SNI patch
provides:
  - sslyze Scanner deterministic cleanup via try/finally + del + gc.collect (BLOCK-01 first half)
  - fingerprint socket close on BaseException paths (BLOCK-01 second half)
  - Two new pytest files asserting cleanup runs (behavioral + structural)
affects:
  - Future scanner phases using sslyze (Phases 70+) — cleanup pattern is now codified
  - Phase 69 plans 02-06 (sibling BLOCKER fixes) — share the same monkeypatch test pattern

tech-stack:
  added: []
  patterns:
    - "try/finally + del + gc.collect for non-context-managed external resource pools (sslyze.Scanner)"
    - "try/except BaseException defense-in-depth socket cleanup for KeyboardInterrupt/SystemExit gaps"
    - "Structural source-shape pytest assertion as durable guard when CPython refcount masks behavioral leak"

key-files:
  created:
    - tests/test_tls_scanner_resource_cleanup.py
    - tests/test_fingerprint_socket_cleanup.py
    - .planning/phases/69-deferred-blockers-scanner-cloud/deferred-items.md
  modified:
    - quirk/scanner/tls_scanner.py
    - quirk/scanner/fingerprint.py

key-decisions:
  - "Assumption A1 verified against sslyze 6.2.0: Scanner exposes only get_results and queue_scans publicly — no close()/__exit__. del + gc.collect is the only cleanup path."
  - "Behavioral tests insufficient under CPython refcount semantics — added structural source-shape pytest assertions (inspect.getsource + regex) as durable guards."
  - "Plan referred to fingerprint_port but actual function is fingerprint_service — used the real symbol; updated test docstring to note the mismatch."

patterns-established:
  - "Structural test pattern: inspect.getsource(target) + regex assertions for fix markers; locks fix shape against future refactors when CPython masks the observable leak."

requirements-completed: [BLOCK-01]

duration: ~110min
completed: 2026-05-15
---

# Phase 69 Plan 01: Resource Leak Fixes Summary

**sslyze Scanner cleanup via try/finally+del+gc.collect, plus fingerprint socket close on BaseException paths — closes BLOCK-01 (CR-07, CR-08).**

## Performance

- **Duration:** ~110 min (extended by RED-test iteration to defeat CPython refcount masking)
- **Started:** 2026-05-15T00:38:00Z (approx)
- **Completed:** 2026-05-15T02:28:00Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 4 (2 source, 2 tests) + 1 deferred-items log

## Accomplishments

- `_scan_one_sslyze` now wraps `SslyzeScanner.queue_scans` / `get_results` in `try/finally` with explicit `del scanner` + `gc.collect()` — guarantees the nassl thread/process pool is released even when `get_results()` raises mid-scan.
- `fingerprint_service` now wraps the `with s:` SSH-banner span in `try/except BaseException` that closes `s` and re-raises, defending against socket leaks on KeyboardInterrupt / SystemExit between `s = _tcp_connect(...)` and entering the `with`.
- Seven new tests across two files: behavioral (monkeypatch-injected exceptions) plus structural (source-shape `inspect.getsource` + regex) guards.

## Task Commits

1. **Task 1 RED (initial):** `777ee66` — `test(69-01): add failing test for sslyze Scanner cleanup (BLOCK-01/CR-07)`
2. **Task 1 RED (strengthen):** `b2945cf` — `test(69-01): strengthen sslyze cleanup test with structural guard`
3. **Task 1 GREEN:** `6e68857` — `fix(69-01): wrap sslyze Scanner lifecycle in try/finally (BLOCK-01/CR-07)`
4. **Task 2 RED:** `e3eb1ae` — `test(69-01): add failing test for fingerprint socket cleanup (BLOCK-01/CR-08)`
5. **Task 2 GREEN:** `ca02a41` — `fix(69-01): close fingerprint socket on BaseException paths (BLOCK-01/CR-08)`

## Files Created/Modified

- `quirk/scanner/tls_scanner.py` — added try/finally + del scanner + gc.collect around the SslyzeScanner lifecycle in `_scan_one_sslyze`.
- `quirk/scanner/fingerprint.py` — added try/except BaseException wrapping the `with s:` SSH-banner span in `fingerprint_service`, with explicit `s.close()` and re-raise.
- `tests/test_tls_scanner_resource_cleanup.py` — 3 tests: exception-path __del__ fire, normal-path __del__ fire, structural source-shape guard.
- `tests/test_fingerprint_socket_cleanup.py` — 4 tests: KeyboardInterrupt close, SystemExit close, normal banner-path close, structural source-shape guard.
- `.planning/phases/69-deferred-blockers-scanner-cloud/deferred-items.md` — records pre-existing failures in test_tls_scanner_chain_verified.py (not caused by this plan, out of scope).

## Verification

- `pytest tests/test_tls_scanner_resource_cleanup.py tests/test_fingerprint_socket_cleanup.py -x -q` → **7 passed**
- `python -m compileall quirk/scanner/tls_scanner.py quirk/scanner/fingerprint.py` → **exit 0**
- Acceptance greps:
  - `grep -n 'del scanner' quirk/scanner/tls_scanner.py` → line 168 (inside `_scan_one_sslyze`'s finally)
  - `grep -n 'finally:' quirk/scanner/tls_scanner.py` → line 166
  - `grep -n 'except BaseException' quirk/scanner/fingerprint.py` → line 165
  - `grep -n 's.close()' quirk/scanner/fingerprint.py` → line 167

## Decisions Made

- **Verified Assumption A1 (sslyze.Scanner public surface).** Ran `python -c "from sslyze import Scanner; print([m for m in dir(Scanner) if not m.startswith('_')])"` against sslyze 6.2.0 → `['get_results', 'queue_scans']`. No public `close()` or `__exit__` exists, so the `del + gc.collect()` pattern is the only available deterministic-release path. Included `gc.collect()` in the finally per the RESEARCH-recommended default (Pitfall 7).
- **Added a structural test alongside the behavioral test.** CPython's eager refcount cleanup on function return masks the leak in pure-Python tests — the behavioral test passes even when the try/finally is absent. `inspect.getsource` + regex assertions for `finally:`, `del scanner`, `gc.collect()` (and `except BaseException`, `s.close()` for fingerprint) lock the fix shape against future refactors.
- **Plan-vs-code symbol mismatch.** Plan §Task 2 referred to `fingerprint_port`; the real symbol is `fingerprint_service`. Used the real symbol and documented the rename note in the test docstring.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Initial RED test for sslyze did not actually fail**
- **Found during:** Task 1 (initial RED run)
- **Issue:** The first version of `test_sslyze_scanner_deleted_on_get_results_exception` relied on a `__del__` flag flipping after the function returned. CPython's refcount-driven cleanup on function exit fires `__del__` even without the try/finally fix, so the test passed pre-fix (violated the TDD fail-fast rule).
- **Fix:** Strengthened the test to use a self-reference cycle in the fake (defeats refcount cleanup, requires cycle-collector pass) AND added a structural `inspect.getsource` test that asserts `finally:`, `del scanner`, `gc.collect()` are present in `_scan_one_sslyze`. The structural test fails RED when the source lacks the fix.
- **Files modified:** tests/test_tls_scanner_resource_cleanup.py
- **Verification:** Reverted the fix in-place, ran pytest → structural test fails. Restored fix → all 3 tests pass.
- **Committed in:** b2945cf (additional RED-strengthening commit)

**2. [Rule 3 - Blocking] Pytest not available in default Python**
- **Found during:** Task 1 (pre-RED setup)
- **Issue:** `/opt/homebrew/opt/python@3.14/bin/python3` (default `python3` alias) lacks sslyze and pytest. `/usr/bin/python3` has sslyze (system Python 3.9) but no pytest.
- **Fix:** Ran `/usr/bin/python3 -m pip install --user pytest` to install pytest 8.4.2 into the system Python user-site. All test invocations use `/usr/bin/python3 -m pytest`.
- **Files modified:** None in repo (user-site install).
- **Verification:** `/usr/bin/python3 -m pytest --version` → `pytest 8.4.2`.
- **Committed in:** Not a code change; documented here.

**3. [Rule 3 - Blocking] Worktree branch behind main (missing SNI patch and phase 69 docs)**
- **Found during:** Plan load (pre-Task 1)
- **Issue:** The agent worktree branched from a commit prior to `c8f89bf` (SNI nassl 3.14 fix) and the phase 69 docs, so the PLAN.md and CONTEXT.md were not present in the worktree, and the SNI line described in the plan was not in `tls_scanner.py`.
- **Fix:** Rebased the worktree branch onto `main` (`git rebase main`) — pulled in `c8f89bf` plus all phase 69 docs cleanly. No conflicts. The plan's instruction to "not revert" the SNI line was honored; the try/finally addition coexists with it.
- **Files modified:** None directly — rebase brought in upstream commits.
- **Verification:** `git log --oneline -1` shows worktree HEAD now ahead of `main` (with the 5 plan 69-01 commits on top); SNI placeholder line still present at tls_scanner.py:136.
- **Committed in:** Not a separate commit; rebase preserved the upstream commits.

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** None of the deviations widened scope. The strengthened RED test is a correctness fix — without it, the TDD cycle gave a false-positive RED. The pytest install and worktree rebase were environmental prerequisites.

## Issues Encountered

- Initial attempts to make the behavioral test fail RED under pytest were defeated by pytest's traceback frame retention. Even with a self-reference cycle in the fake, pytest's call-machinery held a frame ref past the `gc.collect()` calls in both test and production. Resolved by adding the structural source-shape test (which is the durable RED-failing guard) and relaxing the behavioral test to assert `__del__` fired by end of test (which works in normal runtime).

## Deferred Issues

- `tests/test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_true` and `test_sslyze_success_chain_verified_false` fail in the regression sweep but were already failing before this plan (verified via `git stash` round-trip). Out of scope per Phase 69 scope boundary; logged in `.planning/phases/69-deferred-blockers-scanner-cloud/deferred-items.md`.

## User Setup Required

None — purely internal correctness fix, no env/dashboard config changes.

## Next Phase Readiness

- BLOCK-01 (CR-07 + CR-08) closed. Phase 69 plans 02-06 (sibling BLOCKERs) can proceed independently. The monkeypatch + structural-test pattern established here is reusable for plans 02-06.
- No follow-up needed for this plan beyond standard SUMMARY/STATE/ROADMAP/REQUIREMENTS updates.

## Self-Check: PASSED

- [x] `quirk/scanner/tls_scanner.py` exists and contains `del scanner` at line 168, `finally:` at line 166, `gc.collect()` at line 172.
- [x] `quirk/scanner/fingerprint.py` exists and contains `except BaseException:` at line 165, `s.close()` at line 167.
- [x] `tests/test_tls_scanner_resource_cleanup.py` exists (3 tests, all passing).
- [x] `tests/test_fingerprint_socket_cleanup.py` exists (4 tests, all passing).
- [x] Commits 777ee66, b2945cf, 6e68857, e3eb1ae, ca02a41 present in `git log`.

---
*Phase: 69-deferred-blockers-scanner-cloud*
*Plan: 01*
*Completed: 2026-05-15*
