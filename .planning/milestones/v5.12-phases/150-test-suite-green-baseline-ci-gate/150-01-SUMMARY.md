---
phase: 150-test-suite-green-baseline-ci-gate
plan: 01
subsystem: testing
tags: [impacket, kerberos, pyasn1, skip-registry, xfail, test-triage]

# Dependency graph
requires:
  - phase: 149-test-suite-triage
    provides: "116-row disposition ledger (docs/test-triage-149.md), skip_registry.py machinery, and the KDCOptions defect identification that this plan fixes"
provides:
  - "impacket>=0.13.0-tolerant _build_as_req in quirk/scanner/kerberos_scanner.py"
  - "2 permanently CI-enforced Kerberos hardening tests (no xfail)"
  - "Corrected Phase 149 ledger reflecting the fix (no stale quarantine claims)"
affects: [150-02, 150-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Capability-detected impacket API-shape branching (hasattr(constants, 'encodeFlags')) mirroring the sibling MethodData/METHOD_DATA import-guard fix already in the same file"

key-files:
  created: []
  modified:
    - quirk/scanner/kerberos_scanner.py
    - tests/test_identity_scanner_hardening.py
    - tests/skip_registry.py
    - docs/test-triage-149.md

key-decisions:
  - "Fixed _build_as_req via constants.encodeFlags([...].value) on the modern impacket path, preserving the legacy KDCOptions(...) constructor call behind an else branch for impacket <0.13.0 (Phase 150 D-05)"
  - "Rule 1 auto-fix: test_build_as_req_nonce_uses_secrets asserted secrets.randbits(31), but commit 830ad6a (Phase 71 review, D-09) had deliberately switched the scanner to a 32-bit nonce; corrected the stale assertion to randbits(32) in the same edit that removed the xfail marker"

patterns-established:
  - "Impacket API-shape drift is handled via hasattr() capability detection with a `# Phase NNN D-NN:` citation comment, not version-string parsing — matches the existing MethodData/METHOD_DATA precedent in the same file"

requirements-completed: [SUITE-02]

# Metrics
duration: 35min
completed: 2026-08-12
---

# Phase 150 Plan 01: KDCOptions Kerberos Fix + Un-Quarantine Summary

**Fixed the impacket 0.13.0 `KDCOptions` class→enum incompatibility that broke every Kerberos AS-REQ build, un-quarantined the 2 affected tests, and corrected the Phase 149 ledger.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `_build_as_req` no longer raises `pyasn1 KeyError('Bad BitString initializer type')` on impacket `>=0.13.0,<0.14` — verified end-to-end in a throwaway venv building a real AS_REQ object
- Both `test_kdc_udp_decode_failure_logs` and `test_build_as_req_nonce_uses_secrets` are permanently CI-enforced (xfail markers removed) and pass cleanly (0 failed, 0 xfailed) with impacket installed
- `tests/skip_registry.py`'s meta-gate (`test_no_unregistered_skips`) stays green after removing the 2 `pre_existing_triage_149` rows
- `docs/test-triage-149.md` no longer claims these tests are quarantined; ledger row count unchanged (116), Phase 149 history preserved, new "Phase 150 follow-up" subsection added

## Task Commits

1. **Task 1: Make _build_as_req tolerant of impacket 0.13.0's KDCOptions enum** - `0416976` (fix)
2. **Task 2: Un-quarantine the two Kerberos tests and delete their skip-registry rows** - `6785f37` (test)
3. **Task 3: Correct the Phase 149 disposition ledger for the fixed tests** - `37093eb` (docs)

## Files Created/Modified
- `quirk/scanner/kerberos_scanner.py` - `_build_as_req` now branches on `hasattr(constants, "encodeFlags")`: modern path uses `constants.encodeFlags([constants.KDCOptions.forwardable.value])`, legacy path keeps the original `constants.KDCOptions(...)` constructor call for impacket `<0.13.0`
- `tests/test_identity_scanner_hardening.py` - removed both `@pytest.mark.xfail(strict=False, ...)` decorators; corrected `mock_secrets.assert_called_once_with(31)` to `(32)` (stale assertion, unrelated Rule 1 fix, see Deviations)
- `tests/skip_registry.py` - deleted the 2 `pre_existing_triage_149` rows for `test_identity_scanner_hardening.py:85`/`:114`; the unrelated `optional_extra` row (line 80) is untouched
- `docs/test-triage-149.md` - updated 2 Cluster-9 disposition rows from "quarantined-xfail" to "fixed in Phase 150 (D-05)"; appended a "Phase 150 follow-up: KDCOptions fixed" subsection noting the CI-job doesn't-exercise-them caveat (D-01: `[all]` excludes `identity`)

## Decisions Made
- Chose `constants.encodeFlags([constants.KDCOptions.forwardable.value])` as the impacket-0.13.0+ construction, confirmed live in a throwaway venv: it returns a 32-element bit list that pyasn1's BitString field accepts directly, matching impacket's own internal idiom for this exact conversion.
- Kept capability detection (`hasattr(constants, "encodeFlags")`) rather than version-string parsing, per the plan's explicit requirement and the house pattern already established by the adjacent `MethodData`/`METHOD_DATA` import guard in the same file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected a stale nonce-bit-width assertion in test_build_as_req_nonce_uses_secrets**
- **Found during:** Task 1 verification (throwaway-venv pytest run against the fixed scanner)
- **Issue:** After the KDCOptions fix, `test_build_as_req_nonce_uses_secrets` still failed (not xfailed) with `AssertionError: expected call not found. Expected: randbits(31) / Actual: randbits(32)`. Git history showed commit `830ad6a` ("fix(71-review): use secrets.randbits(32) per D-09, drop incorrect 31-bit comment (WR-3)") deliberately changed the production code to a full 32-bit nonce, but this test's assertion (and its docstring comment "31-bit field") were never updated to match — an orphaned test-vs-code mismatch unrelated to the KDCOptions defect, discovered only because un-quarantining the test made it run for the first time since that commit.
- **Fix:** Changed `mock_secrets.assert_called_once_with(31)` to `(32)` and the docstring comment from "31-bit field" to "32-bit field", matching the reviewed, intentional D-09 production behavior.
- **Files modified:** tests/test_identity_scanner_hardening.py
- **Verification:** Throwaway-venv run: both Kerberos tests now report `PASSED` (0 failed, 0 xfailed, 0 xpassed-with-real-failure).
- **Committed in:** `6785f37` (Task 2 commit, same file already being edited for the xfail removal)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug fix)
**Impact on plan:** Necessary to satisfy the plan's own acceptance criterion that both tests pass as real (non-xfail) tests — without this fix, un-quarantining would have converted a masked xfail into a visible, permanent CI failure. No scope creep; single-line assertion + comment correction in a file already in scope for Task 2.

## Issues Encountered
None beyond the deviation above — the throwaway venv (Python 3.14, `impacket>=0.13.0,<0.14`) was created under the session scratchpad, used for verification only, and deleted at the end of Task 1/2 verification per the plan's environment note.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Task 1's fix and Task 2's un-quarantine are independent of Plans 02/03 in this phase (CI job wiring, CONTRIBUTING.md) — no blockers for those plans.
- Confirmed per D-01: since `quirk[all]` excludes the `identity` extra, these 2 tests will still take the `pytest.importorskip("impacket")` skip path in the new Linux CI job (Plan 02's scope) — this is expected and does not need further action.

## Self-Check: PASSED
All created/modified files present on disk; all 3 task commits (0416976, 6785f37, 37093eb) found in git log.
