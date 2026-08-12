---
phase: 149-test-suite-triage
plan: 08
subsystem: testing
tags: [qramm, sys-modules-pollution, api-contract-drift, staleness-cadence, db-migration-refactor, sigsegv-investigation, skip-registry]

requires:
  - phase: 149-test-suite-triage plan 07
    provides: cluster_9_group_b_dashboard_api_db_migration_failures_dispositioned

provides:
  - cluster_9_group_c_qramm_subsystem_failures_dispositioned
  - qramm_staleness_sigsegv_crash_cause_investigated

affects:
  - tests/test_qramm_evidence_bridge.py
  - tests/test_qramm_model_stale.py
  - tests/test_qramm_models.py
  - tests/skip_registry.py
  - docs/test-triage-149.md

tech-stack:
  added: []
  patterns:
    - "sys.modules-based isolation checks (`assert 'quirk.engine.risk_engine' not in sys.modules`) are only valid when the test file that owns the check is guaranteed to run before every other test file that might import the forbidden module — in alphabetical full-suite pytest ordering, an unrelated file earlier in the alphabet (test_findings_evaluator_dedupe.py < test_qramm_evidence_bridge.py) can permanently populate sys.modules and produce a false positive that has nothing to do with the module under test's own imports."
    - "Per-parametrize-case xfail via `pytest.param(..., marks=pytest.mark.xfail(reason=...))` scopes the marker to exactly the failing case without falsely marking the passing cases in the same parametrize list as expected-to-fail — but tests/test_skip_registry.py's AST walker only inspects FunctionDef/AsyncFunctionDef/ClassDef.decorator_list, so this inline marker form is invisible to the meta-gate (registered in ALLOWED_SKIPS anyway for ledger completeness, not gate compliance)."
    - "CLAUDE.md's staleness-cadence re-verification (bumping model_meta.py's last_verified to today's date every ~90 days) can silently break tests that hardcode boundary dates computed against the last_verified value at test-authoring time; boundary-date tests for a staleness gate should derive their fixture dates from the live constant, not a frozen literal."

key-files:
  created: []
  modified:
    - tests/test_qramm_evidence_bridge.py
    - tests/test_qramm_model_stale.py
    - tests/test_qramm_models.py
    - tests/skip_registry.py
    - docs/test-triage-149.md

key-decisions:
  - "The test_qramm_staleness.py SIGSEGV pair (exit=-11) does not reproduce in this sandbox under any of 3 reproduction strategies: 3/3 isolated pytest runs, a direct hand-invocation of the exact CLI command outside pytest entirely, and a representative ~550-test full-suite slice. Neither a genuine native-library crash nor a subprocess/pytest-capture artifact could be confirmed from direct evidence — the determination is recorded as NOT REPRODUCIBLE, not guessed as either category. Both tests were left unmarked (no skip/xfail) rather than quarantined, per the Plan 06 Group A precedent that marking a currently-passing test as skip would incorrectly suppress real signal for Phase 150's baseline work. Flagged HIGH-PRIORITY for Phase 150 re-verification on other Python/cryptography/OpenSSL combinations given a segfault's more severe risk category than an assertion failure."
  - "test_no_risk_engine_import's failure is a cross-test sys.modules pollution artifact, not a real QRAMM-12 evidence_bridge.py import-graph violation: evidence_bridge.py's own source never imports risk_engine (confirmed by full-file read), but test_findings_evaluator_dedupe.py::test_dedupe_via_risk_engine_shim_works (alphabetically earlier, 'f' < 'q') imports quirk.engine.risk_engine for unrelated D-05/WR-10 shim-compatibility coverage, permanently polluting sys.modules for the rest of the pytest session. Directly confirmed by running the two files together vs. in isolation."
  - "test_unconfirmed_excluded_from_score's 422 is genuine API-contract drift, not a stale test: score_session() now hard-rejects scoring with HTTPException(422, DASHBOARD-011) whenever zero QRAMMAnswer rows have answer_value set, before reaching the unconfirmed-exclusion scoring logic this test targets. This all-unconfirmed-rows guard was added by a later phase; the test predates it and still expects a 200 with CVI score=0.0."
  - "test_ensure_qramm_tables_called_after_phase46's grep-based ordering check is stale, not the ordering invariant itself: Phase 85-01 LAUNCH-04 replaced init_db()'s named per-migration call chain with a generic _ADDITIVE_MIGRATIONS loop, so the literal string '_PHASE46_COLUMNS' no longer appears inside init_db's function source text (it lives only in the module-scope tuple definition). The actual invariant — Phase 46 columns migrated before _ensure_qramm_tables runs — is still correctly upheld in _ADDITIVE_MIGRATIONS' declared order and init_db's call sequence."

requirements-completed: [SUITE-01]

duration: 40min
completed: 2026-08-12
---

# Phase 149 Plan 08: Cluster 9 Group C — QRAMM Subsystem Failures Summary

Individually investigated all 6 Cluster 9 Group C failures across 4 QRAMM-related test
files, giving the `test_qramm_staleness.py` SIGSEGV pair the dedicated crash-cause
investigation RESEARCH.md called for (exact CLI command identified, isolation vs.
full-suite reproduction attempted, native-library versions recorded) rather than folding
it into a blanket quarantine. The crash did not reproduce under any reproduction
strategy in this sandbox, so both tests were documented as NOT REPRODUCIBLE and left
unmarked; the remaining 4 failures were individually root-caused (cross-test
`sys.modules` pollution, genuine API-contract drift, a staleness-cadence boundary-date
fixture drift, and a stale grep-based assertion strategy) and quarantined with
`@pytest.mark.xfail`.

## Performance

- **Duration:** 40 min
- **Started:** 2026-08-12T02:00:00Z
- **Completed:** 2026-08-12T02:40:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- **Task 1 (SIGSEGV crash-cause investigation):**
  - Identified the exact CLI subprocess command both tests invoke:
    `subprocess.run([sys.executable, "run_scan.py", "qramm", "status"], ...)`, with the
    fresh-path test clearing `QUIRK_CI_STALENESS_OVERRIDE_DATE` and the stale-path test
    setting it to `last_verified + 100 days`.
  - Ran `tests/test_qramm_staleness.py` standalone 3 separate times — 6 passed, 0
    crashes, all 3 runs.
  - Hand-invoked the underlying CLI command directly (`python run_scan.py qramm
    status`) outside pytest entirely — exits 0, prints the expected FRESH status table.
  - Ran a representative ~550-test full-suite slice (`tests/test_p*.py tests/test_q*.py
    tests/test_r*.py`, chosen to bracket this file alphabetically and include other
    subprocess-heavy test files) — all 6 `test_qramm_staleness.py` tests passed cleanly.
  - Recorded native-library versions: `cryptography` 46.0.6, `OpenSSL` 3.6.3 (9 Jun
    2026), `Python` 3.14.6, darwin.
  - **Determination: NOT REPRODUCIBLE in this sandbox** — no evidence to confirm or
    rule out either a genuine native-library crash or a subprocess/pytest-capture
    artifact, reported as directly observed rather than guessed.
- **Task 2 (4 tests quarantined with individual root causes):**
  - `test_no_risk_engine_import`: proved via direct experiment
    (`pytest tests/test_findings_evaluator_dedupe.py tests/test_qramm_evidence_bridge.py::test_no_risk_engine_import`
    fails; same test alone or after an unrelated file passes) that the failure is
    cross-test `sys.modules` pollution from `test_findings_evaluator_dedupe.py`'s
    risk_engine shim-compat test, not a real QRAMM-12 violation in `evidence_bridge.py`
    itself (confirmed zero import statements in its source by full-file read).
  - `test_unconfirmed_excluded_from_score`: read `score_session()` in
    `quirk/dashboard/api/routes/qramm.py` and found a `HTTPException(422,
    DASHBOARD-011)` guard fires whenever zero rows have `answer_value` set — genuine
    contract drift added by a later phase, the test predates it.
  - `test_is_qramm_model_stale_boundary[today1-True]`: read
    `quirk/qramm/model_meta.py` and found `QRAMM_MODEL["last_verified"]` is now
    `"2026-08-11"` (re-verified/bumped forward by the CLAUDE.md 90-day staleness
    cadence), not the `"2026-05-05"` the test's hardcoded boundary date assumes —
    `is_qramm_model_stale()` itself computes correctly; quarantined via an inline
    `pytest.param(marks=pytest.mark.xfail(...))` scoped to only the failing
    parametrize case (the sibling case still runs and passes normally).
  - `test_ensure_qramm_tables_called_after_phase46`: read `quirk/db.py::init_db` in
    full and confirmed Phase 85-01 LAUNCH-04's `_ADDITIVE_MIGRATIONS` loop refactor
    removed the literal `_PHASE46_COLUMNS` reference from `init_db`'s function source
    text, while the actual ordering invariant (Phase 46 columns before
    `_ensure_qramm_tables`) remains correctly upheld.
  - Registered 4 new `pre_existing_triage_149` entries in `tests/skip_registry.py`.
- **Task 3 (ledger + meta-gate):** Wrote all 6 Cluster 9 Group C rows to
  `docs/test-triage-149.md`, including a dedicated crash-investigation write-up ahead
  of the table documenting the exact command, all 3 reproduction attempts, versions
  recorded, and the NOT REPRODUCIBLE determination flagged HIGH-PRIORITY for Phase 150
  re-verification. Confirmed `pytest tests/test_skip_registry.py -q -m ""` stays green
  (1 passed) and the full 4-file suite reports 54 passed, 3 xfailed, 1 xpassed
  (`test_no_risk_engine_import` XPASSes harmlessly, `strict=False`, when this file
  subset runs alone — it only genuinely fails in full-suite alphabetical order).

## Task Commits

1. **Task 1+2: Investigate SIGSEGV pair + quarantine 4 QRAMM tests** — `4b02909`
2. **Task 3: Write Cluster 9 Group C ledger rows + SIGSEGV crash investigation** — `e9ebc05`

## Files Created/Modified

- `tests/test_qramm_evidence_bridge.py` - Added 2 `@pytest.mark.xfail(strict=False)`
  decorators (`test_no_risk_engine_import`, `test_unconfirmed_excluded_from_score`)
- `tests/test_qramm_model_stale.py` - Wrapped the failing boundary-date case in
  `pytest.param(..., marks=pytest.mark.xfail(strict=False, ...))`, leaving the passing
  sibling case (`2026-08-03`) as a plain tuple
- `tests/test_qramm_models.py` - Added 1 `@pytest.mark.xfail(strict=False)` decorator
  on `TestInitDbQRAMMTables::test_ensure_qramm_tables_called_after_phase46`
- `tests/skip_registry.py` - Added 4 `pre_existing_triage_149` entries for Group C
  (no entry needed/added for the SIGSEGV pair, since it is not quarantined)
- `docs/test-triage-149.md` - Added the Group C section (6-row table + dedicated
  SIGSEGV crash-investigation write-up)

## Decisions Made

See `key-decisions` in frontmatter. The consequential one for Phase 150 priority: the
SIGSEGV pair is genuinely undetermined (not reproducible here, not ruled in or out as a
native-library crash) and is flagged HIGH-PRIORITY for re-verification on a different
Python/cryptography/OpenSSL combination — a segfault deserves more suspicion than an
assertion failure even when it fails to reproduce once.

## Deviations from Plan

1. **[Task-scope adaptation] SIGSEGV pair left unmarked instead of `@pytest.mark.skip`-quarantined.**
   The plan's Task 3 acceptance criteria call for "2 `@pytest.mark.skip` decorators + 2
   matching `ALLOWED_SKIPS` entries" for the SIGSEGV pair. Direct investigation found
   both tests currently pass cleanly in this sandbox under 3 independent reproduction
   strategies (isolated x3, direct CLI hand-invocation, representative full-suite
   slice) — no crash observed. Marking a currently-passing test `@pytest.mark.skip`
   would suppress real signal Phase 150 needs for its green-baseline work, and would
   misrepresent the investigation's actual finding (NOT REPRODUCIBLE, not "confirmed
   broken, skip it"). This mirrors the identical situation and disposition Plan 06
   established for `test_vault_connector.py::test_pki_sha1_signed_ca_high_severity`
   (Group A) — a currently-passing test documented as "not reproducible in this
   environment" with no registry entry, rather than force-quarantined to match a
   RESEARCH.md capture from a possibly different environment. The plan's higher-level
   intent — "investigated and documented, not assumed" — is fully satisfied; only the
   literal skip-marker mechanics diverge from the stated acceptance criteria, and the
   ledger explicitly documents why.
2. **[Marker-mechanics adaptation] Boundary-date xfail applied inline via
   `pytest.param(marks=...)` rather than a plain function decorator.** The plan's Task 2
   acceptance criteria describe "4 `@pytest.mark.xfail` decorators" generically;
   `test_is_qramm_model_stale_boundary` is parametrized with one passing and one failing
   case, so a function-level decorator would incorrectly mark the passing case as
   expected-to-fail too. Used `pytest.param(..., marks=pytest.mark.xfail(...))` to scope
   the marker to only the failing case. Registered in `tests/skip_registry.py` for
   ledger completeness even though `tests/test_skip_registry.py`'s AST walker (which
   only inspects `FunctionDef`/`ClassDef.decorator_list`) does not require it — this is
   noted explicitly in both the registry entry's neighboring comment and the ledger row.

Neither deviation weakens the phase's SUITE-01 goal; both keep the ledger and registry
as the accurate, evidence-based single source of truth the plan's objective requires.

## Issues Encountered

None blocking. Verifying the `test_no_risk_engine_import` cross-file pollution
hypothesis required one extra targeted experiment
(`pytest tests/test_findings_evaluator_dedupe.py tests/test_qramm_evidence_bridge.py::test_no_risk_engine_import`)
beyond the file-in-isolation run, which is expected investigative overhead for an
order-dependent artifact, not a defect.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Cluster 9 Group C is fully closed: 4/6 tests individually investigated and
quarantined with distinct root causes, ledger updated, `test_skip_registry.py`
meta-gate green. The SIGSEGV pair's crash cause has received the dedicated
investigation RESEARCH.md required — determination is NOT REPRODUCIBLE with a
HIGH-PRIORITY re-verification flag for Phase 150, rather than a silent
blanket-quarantine or an unfounded guess either way. No blockers introduced for
remaining Phase 149 clusters/groups in subsequent 149-0X plans.

---
*Phase: 149-test-suite-triage*
*Completed: 2026-08-12*

## Self-Check

- `tests/test_qramm_evidence_bridge.py` modified: FOUND
- `tests/test_qramm_model_stale.py` modified: FOUND
- `tests/test_qramm_models.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- Commit `4b02909` (Task 1+2): FOUND
- Commit `e9ebc05` (Task 3): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- `pytest tests/test_qramm_evidence_bridge.py tests/test_qramm_model_stale.py tests/test_qramm_models.py tests/test_qramm_staleness.py -q -m ""`: CONFIRMED (54 passed, 3 xfailed, 1 xpassed, 0 failed)

## Self-Check: PASSED
