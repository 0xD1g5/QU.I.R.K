---
phase: 149-test-suite-triage
plan: 04
subsystem: testing
tags: [version-consistency, dist-info, pytest, skip-registry, optional-extra]

requires:
  - phase: 149-test-suite-triage plan 01
    provides: skip_registry_gate_green, pre_existing_triage_149_category, test-triage-149_ledger_skeleton
provides:
  - cluster_3_version_staleness_environment_resolved
  - cluster_4_stale_version_assertions_dispositioned
  - cluster_7_gcp_optional_extra_quarantined
affects:
  - tests/test_packaging.py
  - tests/test_v41_gap_closure.py
  - tests/test_cli_correctness.py
  - tests/test_gcs_reuse.py
  - tests/skip_registry.py
  - docs/test-triage-149.md

tech-stack:
  added: []
  patterns:
    - "Deriving hardcoded version-consistency assertions from quirk.__version__ instead of a fixed literal, to avoid the every-release-hand-edit anti-pattern while preserving cross-module drift detection"

key-files:
  created: []
  modified:
    - tests/test_packaging.py
    - tests/test_v41_gap_closure.py
    - tests/test_cli_correctness.py
    - tests/test_gcs_reuse.py
    - tests/skip_registry.py
    - docs/test-triage-149.md

key-decisions:
  - "Reassigned test_cli_correctness.py::test_version_consistency from the plan's stated Cluster 3 (environment) grouping to Cluster 4 (stale assertion), per RESEARCH.md row 4 ground truth — its failure was a hardcoded TARGET literal, not stale dist-info, and pip install -e . alone did not fix it"
  - "Deleted test_packaging.py::test_version_is_4_2_0 and test_v41_gap_closure.py::test_pyproject_version_field_is_4_1_0 as obsolete-by-design (sole assertion was a pinned historical version string with no other coverage)"
  - "Kept and fixed test_cli_correctness.py::test_version_consistency rather than deleting it, since it exercises real cross-module consistency (PLATFORM_VERSION/INTELLIGENCE_VERSION/CBOM_VERSION/IntelligenceCfg vs quirk.__version__) beyond a bare version string; TARGET now derives from quirk.__version__ itself"
  - "Environment fix for Cluster 3 was applied inside .venv (not the system Homebrew Python that python/pip resolve to by default) — confirmed via which pytest before touching anything"

requirements-completed: [SUITE-01]

duration: 25min
completed: 2026-08-12
---

# Phase 149 Plan 04: Version Staleness (Clusters 3 & 4) + GCP Optional Extra (Cluster 7) Summary

Refreshed the `.venv` editable install's stale `quirk-scanner` dist-info to resolve 5 genuine
environment-caused version-mismatch failures, corrected/deleted 3 genuinely stale hardcoded
version-literal test assertions (2 deleted as anti-pattern, 1 fixed to derive from
`quirk.__version__` instead of a fixed string), and quarantined 2 tests requiring the
uninstalled optional `googleapiclient`/`google` (`[cloud]`) extra — 10 ledger rows total.

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-12T00:10:00Z
- **Completed:** 2026-08-12T00:36:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Diagnosed that `python`/`pip` on `PATH` resolve to the system Homebrew Python (where `quirk`
  isn't installed at all), while the project's actual `pytest` runs under `.venv`, which had a
  genuinely stale `quirk-scanner==5.10.0` editable install vs `pyproject.toml`'s `5.11.0` —
  matching RESEARCH.md's Cluster 3 finding exactly once the correct interpreter was used.
- `pip install -e .` inside `.venv` refreshed the dist-info with zero source/test edits;
  `tests/test_version.py` went from 6 passed/1 failed to 7 passed.
- Corrected the plan's cluster miscount: `test_cli_correctness.py::test_version_consistency`
  is a Cluster 4 (stale-assertion) failure per RESEARCH.md's own table, not Cluster 3
  (environment) — it still failed with `TARGET = "5.5.0"` after the dist-info refresh, since its
  root cause is unrelated to package metadata.
- Dispositioned all 3 Cluster 4 tests: deleted 2 single-purpose stale-literal tests, fixed the
  third (which has genuine multi-constant coverage) by deriving `TARGET` from
  `quirk.__version__` rather than hardcoding a version string that goes stale every release.
- Quarantined both `test_gcs_reuse.py` tests that require `googleapiclient`/`google` with
  `@pytest.mark.skip` + matching `optional_extra` registry entries — same category shape as the
  existing `broker_scanner`/`sslyze` entries, no new machinery.
- Wrote 10 ledger rows across Clusters 3, 4, and 7 in `docs/test-triage-149.md`.

## Task Commits

1. **Task 1: Resolve Open Question 1 — refresh stale dist-info for Cluster 3** — no commit
   (environment-only; `pip install -e .` inside `.venv`, no source/test file changed, per plan's
   own acceptance criterion)
2. **Task 2: Correct or delete Cluster 4's genuinely stale version assertions** - `45f0368` (fix)
3. **Task 3: Quarantine Cluster 7 + ledger rows for Clusters 3/4/7** - `c276b8f` (test)

_Note: Task 1 intentionally has no commit — the plan's own acceptance criteria require "No file
in tests/ or quirk/ was modified by this task."_

## Files Created/Modified

- `tests/test_packaging.py` - Deleted `test_version_is_4_2_0` (stale-literal-only test)
- `tests/test_v41_gap_closure.py` - Deleted `test_pyproject_version_field_is_4_1_0` (stale-literal-only test)
- `tests/test_cli_correctness.py` - Fixed `test_version_consistency` to derive `TARGET` from `quirk.__version__` instead of a hardcoded string
- `tests/test_gcs_reuse.py` - Added `@pytest.mark.skip` to the 2 tests requiring `googleapiclient`/`google`
- `tests/skip_registry.py` - Added 2 `optional_extra` entries for `test_gcs_reuse.py`
- `docs/test-triage-149.md` - Added 5 Cluster 3 rows, 3 Cluster 4 rows, 2 Cluster 7 rows (10 total)

## Decisions Made

See `key-decisions` in frontmatter. The most consequential one: the plan's Task 1 description
grouped `test_cli_correctness.py::test_version_consistency` with Cluster 3 and claimed all 6
listed tests would pass "with zero code/test changes" after the dist-info refresh. Running the
tests after the fix showed this was false for that one test — it kept failing with its hardcoded
`TARGET = "5.5.0"`. Cross-checking RESEARCH.md's own Cluster table (row 4) confirmed this test
was always meant to be Cluster 4 material (3 tests: `test_packaging.py`, `test_v41_gap_closure.py`,
`test_cli_correctness.py::test_version_consistency`), and the plan's task breakdown simply
miscounted which cluster it belonged to. The total (5+3+2=10) still matches the plan's stated
"10 tests total" — only the cluster assignment for one test moved. No user input needed; this is
squarely a scope-preserving correction, not an architectural change (Rule 1).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected Cluster 3/4 test miscount in the plan's task breakdown**
- **Found during:** Task 1 (verifying all 6 stated "Cluster 3" tests pass post-fix)
- **Issue:** The plan's Task 1 grouped `test_cli_correctness.py::test_version_consistency` into
  Cluster 3 (environment-fixable), but it is a genuinely stale hardcoded-literal test
  (`TARGET = "5.5.0"`) per RESEARCH.md's own Cluster 4 table — `pip install -e .` alone could
  never fix it.
- **Fix:** Verified `test_version.py`'s 5 tests are the true Cluster 3 set (all pass after
  `pip install -e .`); moved `test_version_consistency` into Task 2/Cluster 4's disposition
  (fixed by deriving `TARGET` from `quirk.__version__`).
- **Files modified:** tests/test_cli_correctness.py (part of Task 2's edits)
- **Verification:** `pytest tests/test_version.py -q -m ""` → 7 passed (Cluster 3 alone);
  `pytest tests/test_cli_correctness.py::test_version_consistency -q -m ""` → 1 passed after fix
- **Committed in:** 45f0368 (Task 2 commit)

**2. [Scope boundary] Logged an unrelated pre-existing failure to deferred-items.md**
- **Found during:** Task 2 (re-running `tests/test_cli_correctness.py` for verification)
- **Issue:** `test_cli_correctness.py::test_no_quirk_scan_references` fails (stale `quirk scan`
  references in docs), independent of Clusters 3/4/7 (RESEARCH.md line 213 documents it
  separately).
- **Action:** Not fixed — out of scope per the executor's scope-boundary rule. Logged to
  `.planning/phases/149-test-suite-triage/deferred-items.md` (not committed — `.planning/` is
  gitignored per the public-repo policy).

---

**Total deviations:** 2 (1 auto-fixed scope correction, 1 out-of-scope item logged and deferred)
**Impact on plan:** The scope-correction deviation kept the plan's declared 10-test total intact
while fixing an internal inconsistency between its Task 1 claim and RESEARCH.md's own ground
truth. No scope creep — the deferred item was explicitly left untouched.

## Issues Encountered

- Bare `python`/`pip` on this machine resolve to the externally-managed Homebrew system Python
  (PEP 668-blocked, no `quirk` install at all), not the project's `.venv`. Running
  `pip install -e .` against the wrong interpreter would have silently done nothing useful (or
  errored on `externally-managed-environment`). Resolved by explicitly `source .venv/bin/activate`
  and confirming `which pytest` resolves to `.venv/bin/pytest` before making any environment
  change — this is the same interpreter the plan's own verification commands run under.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Clusters 3, 4, and 7 are fully closed (10/10 tests dispositioned, ledger updated,
`test_skip_registry.py` meta-gate green). Remaining clusters (5, 8 partial, 9, and any others)
continue in subsequent 149-0X plans per the phase's wave sequencing. No blockers introduced for
Phase 150 (test suite green baseline).

---
*Phase: 149-test-suite-triage*
*Completed: 2026-08-12*

## Self-Check

- `tests/test_gcs_reuse.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- `tests/test_packaging.py` modified: FOUND
- `tests/test_v41_gap_closure.py` modified: FOUND
- `tests/test_cli_correctness.py` modified: FOUND
- Commit `45f0368` (Task 2): FOUND
- Commit `c276b8f` (Task 3): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- Combined verification (`test_version.py`, `test_cli_correctness.py::test_version_consistency`, `test_packaging.py`, `test_v41_gap_closure.py`, `test_gcs_reuse.py`): CONFIRMED (24 passed, 2 skipped, 0 failed)

## Self-Check: PASSED
