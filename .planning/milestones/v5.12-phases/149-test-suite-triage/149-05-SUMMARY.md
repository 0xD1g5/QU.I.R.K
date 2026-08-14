---
phase: 149-test-suite-triage
plan: 05
subsystem: testing
tags: [sensor-id-shape, audit-08, test-isolation, sqlite-shared-cache, skip-registry]

requires:
  - phase: 149-test-suite-triage plan 04
    provides: pre_existing_triage_149_category, test-triage-149_ledger_running_total
provides:
  - cluster_5_sensor_id_shape_audit08_dispositioned

affects:
  - tests/test_auto_merge_trigger.py
  - tests/test_sensor_push_id_revalidation.py
  - tests/skip_registry.py
  - docs/test-triage-149.md

tech-stack:
  added: []
  patterns:
    - "SQLite shared-cache in-memory URI (file::memory:?cache=shared&uri=true) is a single process-wide DB, not per-test-isolated — used by 13+ test files, so row counts leak across files depending on collection order"

key-files:
  created: []
  modified:
    - tests/test_auto_merge_trigger.py
    - tests/test_sensor_push_id_revalidation.py
    - tests/skip_registry.py
    - docs/test-triage-149.md

key-decisions:
  - "test_sensor_push_id_revalidation.py's 2 failures are NOT the same root cause as test_auto_merge_trigger.py's 8 (per RESEARCH.md Open Question 3 instruction) — individually investigated and confirmed to be shared in-memory SQLite cache pollution across test files, not an AUDIT-08 write-before-reject implementation defect. No source code fix required; not flagged as a Phase 150 regression."
  - "Both clusters use xfail(strict=False) rather than skip, matching Task 1's stated rationale: the tests document intended behavior (AUDIT-08 UUID guard, fixture correctness) and would legitimately pass again once fixtures are updated or the DB engine is per-test-isolated — quarantine, not permanent suppression."

requirements-completed: [SUITE-01]

duration: 20min
completed: 2026-08-12
---

# Phase 149 Plan 05: Cluster 5 — sensor_id Shape / AUDIT-08 Regression Summary

Quarantined all 10 Cluster 5 failures: 8 `test_auto_merge_trigger.py` tests fail
`quirk/dashboard/api/routes/sensor.py:494`'s AUDIT-08 UUID-shape guard because their fixtures
predate it (`"sensor-a"`/`"sensor-b"` are not valid UUIDs); 2 `test_sensor_push_id_revalidation.py`
tests were individually investigated per RESEARCH.md's Open Question 3 and traced to a distinct,
genuine root cause — SQLite shared-cache in-memory database pollution across 13+ test files, not an
AUDIT-08 implementation defect.

## Performance

- **Duration:** 20 min
- **Started:** 2026-08-12T00:40:00Z
- **Completed:** 2026-08-12T01:00:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Confirmed all 8 `test_auto_merge_trigger.py` tests fail with `400: {"detail":"Invalid sensor_id
  shape"}` via standalone run (`pytest tests/test_auto_merge_trigger.py -q -m ""` → 8 failed, 1
  passed before quarantine) — every failing test's fixtures use `"sensor-a"`/`"sensor-b"`/
  `"sensor-ghost"`, none of which match `_UUID_RE`.
- Quarantined all 8 with `@pytest.mark.xfail(strict=False)` and matching `pre_existing_triage_149`
  `skip_registry.py` entries, citing the AUDIT-08 comment context read directly from
  `quirk/dashboard/api/routes/sensor.py:485-494`.
- Individually investigated `test_sensor_push_id_revalidation.py`'s "9 SensorPush row(s) found"
  failures (Task 2, no batch-classification with Task 1's fixture explanation per plan's explicit
  instruction and RESEARCH.md Open Question 3):
  - Ran the file standalone: 3 passed — the 400 rejection and 0-new-rows assertion are both
    correct in isolation.
  - Reproduced the full-suite-order failure directly: `pytest tests/test_sensor_ingest.py
    tests/test_sensor_auth_per_sensor.py tests/test_sensor_push_id_revalidation.py -q -m ""` →
    reproduces the exact `AssertionError: AUDIT-08 RED: 9 SensorPush row(s) found` message from
    RESEARCH.md.
  - Traced the root cause: the file's DB engine URI (`sqlite:///file::memory:?cache=shared&uri=true`)
    is a SQLite shared-cache in-memory database — a single process-wide DB, not isolated per test
    function or per file. 13 other test files use the identical URI (`grep -rl` confirmed
    `test_jobs_target_validation.py`, `test_console_hardening.py`, `test_schedules_api.py`,
    `test_jobs_nmap_scope_cap.py`, `test_dashboard_auth_apikey.py`, `test_jobs_api.py`,
    `test_identity_surface.py`, `test_sensor_auth_per_sensor.py`, `test_job_trusted_targets.py`,
    `test_scan_submit_request_no_internal.py`, `test_api_auth.py`, `test_sensor_ingest.py`, plus
    `conftest.py`), and any `SensorPush` rows those files write in the same pytest worker process
    persist and are counted by this file's `db.query(SensorPush).count()` assertion.
  - Determined this is explanation (a) from the plan's decision tree — a genuinely different
    root cause than Cluster 5's fixture-ID mismatch, and NOT explanation (b) — no
    write-before-reject ordering defect exists in the AUDIT-08 guard itself. The route's actual
    behavior (400 + zero *new* rows written by the rejecting request) is correct; the assertion
    merely counts pre-existing rows from earlier tests, not rows the malformed request itself wrote.
  - Recorded this finding as NOT a real regression requiring a Phase 150 fix, distinct from Task 1's
    "outdated-fixture (AUDIT-08 UUID guard)" sub-reason.
- Quarantined both `test_sensor_push_id_revalidation.py` tests with `@pytest.mark.xfail(strict=False)`
  using a distinct reason string citing the shared-cache pollution finding, plus matching
  `skip_registry.py` entries.
- Wrote all 10 Cluster 5 ledger rows in `docs/test-triage-149.md`, with the 2
  `test_sensor_push_id_revalidation.py` rows citing Task 2's specific investigation (not reused
  Task 1 fixture wording).
- Verified `pytest tests/test_auto_merge_trigger.py tests/test_sensor_push_id_revalidation.py -q -m ""`
  → 2 passed, 8 xfailed, 2 xpassed, 0 failed (the 2 revalidation tests xpass in this isolated
  two-file run since the pollution only manifests when other SensorPush-writing files run first in
  full-suite order — `strict=False` correctly treats this as non-failing).
- Confirmed `pytest tests/test_skip_registry.py -q -m ""` meta-gate stays green (1 passed).

## Task Commits

1. **Task 1: Quarantine test_auto_merge_trigger.py's 8 outdated-fixture failures** — `f437134`
2. **Task 2: Individually investigate test_sensor_push_id_revalidation.py's row-count mismatch** —
   no commit (investigation-only per plan's own Task 2 scope; findings feed directly into Task 3's
   quarantine + ledger commit)
3. **Task 3: Quarantine test_sensor_push_id_revalidation.py + write Cluster 5 ledger rows** — `3957933`

## Files Created/Modified

- `tests/test_auto_merge_trigger.py` - Added `@pytest.mark.xfail(strict=False)` above all 8 failing tests
- `tests/test_sensor_push_id_revalidation.py` - Added `@pytest.mark.xfail(strict=False)` above the 2 row-count-mismatch tests
- `tests/skip_registry.py` - Added 10 `pre_existing_triage_149` entries (8 for auto_merge_trigger, 2 for sensor_push_id_revalidation)
- `docs/test-triage-149.md` - Filled in the 10-row Cluster 5 table

## Decisions Made

See `key-decisions` in frontmatter. The consequential one: RESEARCH.md's Open Question 3 explicitly
flagged that `test_sensor_push_id_revalidation.py`'s failure could be either a fixture-staleness
issue (same shape as the 8 `test_auto_merge_trigger.py` tests) or a genuine AUDIT-08 write-before-
reject implementation bug (a real regression). Standalone-vs-full-suite-order reproduction proved it
is neither — it is a shared in-memory SQLite cache test-isolation defect (the same defect *class* as
Cluster 2/6's shared-fixture issues, but a distinct instance/cause from either of those clusters and
from Cluster 5's own fixture-ID mismatch). This was recorded precisely per the plan's explicit
instruction, with its own ledger sub-reason text, not folded into Task 1's wording.

## Deviations from Plan

None - plan executed exactly as written. Task 2's investigation confirmed the plan's own
recommendation (RESEARCH.md's Open Question 3) that this pair needed separate, non-batched
investigation, and that investigation is what determined the disposition written in Task 3.

## Issues Encountered

None beyond the investigation itself. The full-suite-order reproduction command
(`pytest tests/test_sensor_ingest.py tests/test_sensor_auth_per_sensor.py
tests/test_sensor_push_id_revalidation.py -q -m ""`) was found empirically by identifying other
files sharing the `file::memory:?cache=shared&uri=true` URI via `grep -rl` and picking
alphabetically-earlier ones that write `SensorPush` rows — this reliably reproduced the exact "9
SensorPush row(s) found" message from RESEARCH.md, confirming the root-cause hypothesis without
guesswork.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Cluster 5 is fully closed (10/10 tests dispositioned, ledger updated, `test_skip_registry.py`
meta-gate green). The shared in-memory SQLite cache pollution finding is a candidate for Phase 150's
broader test-isolation fix (converting `file::memory:?cache=shared&uri=true` engines to per-test
unique cache names or file-backed tmp_path DBs) but is explicitly NOT flagged as an AUDIT-08 code
defect requiring a production fix. No blockers introduced for remaining Phase 149 clusters (8
partial, 9, and any others) in subsequent 149-0X plans per the phase's wave sequencing.

---
*Phase: 149-test-suite-triage*
*Completed: 2026-08-12*

## Self-Check

- `tests/test_auto_merge_trigger.py` modified: FOUND
- `tests/test_sensor_push_id_revalidation.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- Commit `f437134` (Task 1): FOUND
- Commit `3957933` (Task 3): FOUND
- `pytest tests/test_auto_merge_trigger.py tests/test_sensor_push_id_revalidation.py -q -m ""` exits 0: CONFIRMED (2 passed, 8 xfailed, 2 xpassed, 0 failed)
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)

## Self-Check: PASSED
