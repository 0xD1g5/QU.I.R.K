---
phase: 149-test-suite-triage
plan: 09
subsystem: testing
tags: [cli, compliance, install-errors, logging-signature, chaos-lab-drift, cr01-guard, skip-registry]

requires:
  - phase: 149-test-suite-triage plan 08
    provides: cluster_9_group_c_qramm_subsystem_failures_dispositioned

provides:
  - cluster_9_group_d1_cli_compliance_posture_failures_dispositioned

affects:
  - tests/test_cbom_schema_validation.py
  - tests/test_cli_correctness.py
  - tests/test_cli_init.py
  - tests/test_compliance_title_join.py
  - tests/test_email_run_scan_wiring.py
  - tests/test_install_errors.py
  - tests/skip_registry.py
  - docs/test-triage-149.md

tech-stack:
  added: []
  patterns:
    - "CR-01/D-13's CWD-containment guard on quirk/cli/init_cmd.py::run_init treats pytest's tmp_path fixture (which resolves under /private/var/folders/.../pytest-of-*/...) as a path-traversal escape and silently no-ops rather than writing the file — any subprocess-based CLI test that writes to tmp_path via --output must either monkeypatch.chdir(tmp_path) or accept the guard is a genuine security control, not a bug."
    - "Lazy imports inside a function body (server.py's `import uvicorn` inside serve(), not at module scope) make module-import-only test tricks (patching builtins.__import__ then bare-importing the module) structurally unable to exercise the guarded code path — the import statement is never reached unless the function that owns it is actually called."
    - "Investigation before quarantine can find a test's target failure genuinely does not reproduce (POSTURE-02's GCP 403 scan_error emission already works correctly in this sandbox) — the not-reproducible disposition established in Plans 06/08 extends naturally to 'my own file's docstring says RED scaffold, but the fix already landed'."

key-files:
  created: []
  modified:
    - tests/test_cbom_schema_validation.py
    - tests/test_cli_correctness.py
    - tests/test_cli_init.py
    - tests/test_compliance_title_join.py
    - tests/test_email_run_scan_wiring.py
    - tests/test_install_errors.py
    - tests/skip_registry.py
    - docs/test-triage-149.md

key-decisions:
  - "test_cbom_schema_validation.py::test_parametrize_set_matches_docker_compose_profiles found a genuine chaos-lab-maintenance gap, not a stale test: docker-compose.yml's 'otics' profile (Phase 141-07 Modbus/BACnet lab) never got a corresponding synthesizer in tests/_cbom_profiles.py::PROFILE_ENDPOINTS when it shipped, violating CLAUDE.md's Chaos Lab Maintenance rule. Flagged explicitly for a Phase 150 follow-up (add an otics endpoint synthesizer) rather than silently absorbed into the quarantine."
  - "test_email_run_scan_wiring.py's Logger.info signature check is testing a signature that was deliberately widened, not regressed: commit 01411acc (89-02 LAB-06, 2026-05-22) intentionally changed Logger.info(self, msg: str) to Logger.info(self, msg: object, *args) to fix a real live-lab crash where scanner internals passed it printf-style args like a stdlib logger. The test predates that fix and enforces the old, now-incorrect contract."
  - "test_install_errors.py's 2 failures do NOT share a root cause despite living in the same file and area (per the plan's explicit instruction to verify, not assume, shared causation): test_port_conflict_format fails because this sandbox lacks the uvicorn/dashboard optional extra, so serve() exits via QRK-INSTALL-002 before ever reaching the port-bind/QRK-INSTALL-004 path; test_dashboard_missing_uvicorn_format fails because it only imports quirk.dashboard.server (never calls serve()), and server.py's uvicorn import is lazy (inside serve(), not module scope) — the two failures are structurally independent even though they superficially look like 'the install-error catalog is broken'."
  - "3 of the plan's originally-scoped 11 tests (test_errors_cmd.py::test_lookup_single_known_returns_zero and test_posture_scorefix125.py's 2 GCP-403 tests) were investigated but found NOT REPRODUCIBLE in this sandbox — all pass cleanly under isolated, combined-4-file, and broad full-suite reproduction attempts. Per the Plan 06/08 precedent, these were left unmarked rather than force-quarantined; for the GCP tests this is a positive finding (POSTURE-02's scan_error emission on 403/IAM-denied already works correctly, contradicting the file's stale 'RED scaffold' docstring)."

requirements-completed: [SUITE-01]

duration: 45min
completed: 2026-08-12
---

# Phase 149 Plan 09: Cluster 9 Group D1 — CLI/Compliance/Posture Failures Summary

Individually investigated all 11 Cluster 9 Group D1 failures across 8 files with no
shared root cause (per RESEARCH.md's clustering pass). Investigation converged on 9
distinct sub-reasons: 1 genuine chaos-lab profile-drift gap (flagged for Phase 150), 1
stale-doc grep, 2 instances of a legitimate CR-01/D-13 path-traversal guard rejecting
pytest's `tmp_path`, 1 genuine compliance-mapping coverage gap left over from Phase 95,
1 intentional Logger signature widening from a real bug fix, 2 independently-root-caused
install-error failures (verified NOT to share a cause despite superficial similarity),
and 3 tests confirmed not reproducible in this sandbox — including 2 GCP-403 tests whose
own file docstring says "RED scaffold" but whose target fix (POSTURE-02's scan_error
emission) is already correctly implemented.

## Performance

- **Duration:** 45 min
- **Started:** 2026-08-12T02:45:00Z
- **Completed:** 2026-08-12T03:30:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- **Task 1 (5 tests quarantined):**
  - `test_cbom_schema_validation.py::test_parametrize_set_matches_docker_compose_profiles`:
    diffed the test's own output to find `otics` is the sole drifted profile —
    `docker-compose.yml` has it, `PROFILE_ENDPOINTS` doesn't. Confirmed via CLAUDE.md's
    Chaos Lab Maintenance rule that this is a genuine follow-up gap from Phase 141-07,
    not a stale test.
  - `test_cli_correctness.py::test_no_quirk_scan_references`: grepped the test's own
    diagnostic output — all 3 offending files (`docs/UAT-SERIES.md`,
    `docs/chaos-lab.md`, `docs/release-notes/4.6.0.md`) are historical/frozen prose,
    not live CLI documentation.
  - `test_cli_init.py::test_init_creates_config` / `test_init_no_overwrite`: read
    `quirk/cli/init_cmd.py::run_init` in full and found the CR-01/D-13 CWD-containment
    guard (lines 24-33) rejects pytest's `tmp_path` (resolves outside repo CWD),
    silently no-oping with a printed WARNING instead of raising — confirmed by
    hand-invoking the exact subprocess command.
  - `test_compliance_title_join.py::test_every_emitted_title_is_mapped_or_allowlisted`:
    the test's own diff lists 3 missing titles verbatim; grepped
    `quirk/engine/findings_evaluator.py` to confirm they're Phase 95 CSIGN-01 codesign
    findings (lines 1026, 1045, 1080) that were never added to `COMPLIANCE_MAP` or
    `UNMAPPED_TITLES`.
  - Registered 5 new `pre_existing_triage_149` entries in `tests/skip_registry.py`.
- **Task 2 (3 of 6 quarantined; 3 found not reproducible):**
  - `test_email_run_scan_wiring.py::test_email_branch_logger_calls_use_real_logger_signatures`:
    read `quirk/logging_util.py::Logger.info`'s current signature and used
    `git log --follow -p` to find commit `01411acc` deliberately widened it from
    `(self, msg: str)` to `(self, msg: object, *args)` for a real 89-02 LAB-06 bug fix
    (identity connectors crashing against the live lab). Test predates the fix.
  - `test_errors_cmd.py::test_lookup_single_known_returns_zero`: ran in isolation
    (12/12 passed), inside the combined 4-file Task-2 run, and inside a broader
    298-test `test_e*/test_i*` run — passed cleanly every time. No failure to
    diagnose; left unmarked per the not-reproducible precedent.
  - `test_install_errors.py::test_port_conflict_format` /
    `test_dashboard_missing_uvicorn_format`: read `quirk/dashboard/server.py::serve()`
    in full and confirmed these do NOT share a root cause — the port-conflict test
    fails because this sandbox lacks the uvicorn/dashboard extra (serve() exits via
    QRK-INSTALL-002 before reaching the port-bind path), while the
    missing-uvicorn-format test fails because it only imports the module (never calls
    `serve()`) and server.py's `import uvicorn` is lazy (inside `serve()`, not module
    scope).
  - `test_posture_scorefix125.py::test_gcp_kms_403_emits_scan_error` /
    `test_gcp_sql_403_emits_scan_error`: ran in isolation (3/3 passed), inside the
    combined 4-file run, and inside a 143-test `test_p*.py` run — passed cleanly
    every time. Read `quirk/scanner/gcp_connector.py::_scan_kms`/`_scan_cloud_sql` and
    confirmed POSTURE-02's scan_error-on-403 fix is already implemented and working,
    despite the file's "RED scaffolds" docstring.
  - Registered 3 new `pre_existing_triage_149` entries in `tests/skip_registry.py`.
- **Task 3 (ledger + meta-gate):** Wrote all 11 Cluster 9 Group D1 rows to
  `docs/test-triage-149.md` (8 quarantined, 3 not-reproducible), with the
  `test_cbom_schema_validation.py` row explicitly flagging the `otics` chaos-lab
  profile drift for a Phase 150 `lab.sh`/`PROFILE_ENDPOINTS` follow-up. Confirmed
  `pytest tests/test_skip_registry.py -q -m ""` stays green (1 passed) and the full
  8-file suite reports 110 passed, 8 xfailed, 0 failed.

## Task Commits

1. **Task 1: Investigate + quarantine 5 CLI/compliance tests** — `faf7c5e`
2. **Task 2: Investigate + quarantine 3 of 6 email/install tests** — `12c342b`
3. **Task 3: Write Cluster 9 Group D1 ledger rows** — `f8fe376`

## Files Created/Modified

- `tests/test_cbom_schema_validation.py` - Added 1 `@pytest.mark.xfail(strict=False)`
  decorator (chaos-lab `otics` profile drift)
- `tests/test_cli_correctness.py` - Added `import pytest` + 1
  `@pytest.mark.xfail(strict=False)` decorator (stale `quirk scan` doc refs)
- `tests/test_cli_init.py` - Added 2 `@pytest.mark.xfail(strict=False)` decorators
  (CR-01/D-13 path-traversal guard vs. pytest `tmp_path`)
- `tests/test_compliance_title_join.py` - Added `import pytest` + 1
  `@pytest.mark.xfail(strict=False)` decorator (Phase 95 codesign coverage gap)
- `tests/test_email_run_scan_wiring.py` - Added 1 `@pytest.mark.xfail(strict=False)`
  decorator (intentional Logger signature widening)
- `tests/test_install_errors.py` - Added 2 `@pytest.mark.xfail(strict=False)`
  decorators (2 independently-root-caused install-error failures)
- `tests/skip_registry.py` - Added 8 `pre_existing_triage_149` entries for Group D1
  (no entries needed/added for the 3 not-reproducible tests, matching the SIGSEGV-pair
  precedent from Plan 08)
- `docs/test-triage-149.md` - Added the Group D1 section (11-row table)

## Decisions Made

See `key-decisions` in frontmatter. The two consequential ones for Phase 150 priority:
(1) `test_cbom_schema_validation.py`'s drift finding is a real gap — the `otics` chaos
lab profile shipped without a CBOM synthesizer, which needs a small follow-up fix, not
just a quarantine; (2) the GCP-403 posture tests reveal POSTURE-02's fix is already
correctly in place in this sandbox — no silent-swallow security concern needs carrying
forward, despite the file's stale "RED scaffold" self-description.

## Deviations from Plan

1. **[Investigation-driven scope adjustment] 3 of the plan's 11 originally-scoped tests
   left unmarked instead of quarantined.** The plan's acceptance criteria for Task 2
   describe quarantining all 6 tests in that task's scope (11 total across both tasks).
   Direct investigation found `test_errors_cmd.py::test_lookup_single_known_returns_zero`
   and `test_posture_scorefix125.py`'s 2 GCP-403 tests all pass cleanly under 3
   independent reproduction strategies each (isolated, combined-4-file, and a broad
   full-suite slice) — no failure occurred in this sandbox to diagnose or quarantine.
   Marking currently-passing tests `xfail` would suppress real Phase 150 baseline signal
   and misrepresent the investigation's actual finding. This directly mirrors the
   identical situation and disposition this phase already established in Plan 06
   (`test_vault_connector.py::test_pki_sha1_signed_ca_high_severity`) and Plan 08 (the
   `test_qramm_staleness.py` SIGSEGV pair) — both left unmarked with a documented
   not-reproducible determination rather than force-quarantined to match a RESEARCH.md
   capture from a possibly different environment. The plan's higher-level intent — "each
   test individually investigated with distinct, evidence-backed dispositions" — is
   fully satisfied; the verification command in the plan's `<verification>` block
   (expecting "11 xfailed, 0 failed") does not match the actual, evidence-backed outcome
   (8 xfailed, 3 confirmed not reproducible, 0 failed) for this reason. The ledger
   documents each of the 3 not-reproducible tests individually with full investigation
   evidence, satisfying the plan's must_haves truth that "each ... has an
   individually-investigated disposition."
2. **[Investigation correction] `test_install_errors.py`'s 2 failures explicitly verified
   NOT to share a root cause**, per the plan's own instruction to check this rather than
   assume. Both tests target the install-error catalog area and superficially look like
   one shared catalog/formatting defect, but reading `quirk/dashboard/server.py::serve()`
   in full showed two structurally independent causes (missing uvicorn extra in this
   sandbox vs. a stale lazy-import test-construction assumption) — documented distinctly
   in both the xfail reason strings and the ledger rows, per the plan's acceptance
   criteria.

Neither deviation weakens the phase's SUITE-01 goal; both keep the ledger and registry
as the accurate, evidence-based single source of truth the plan's objective requires.

## Issues Encountered

None blocking. Confirming the `test_install_errors.py` two-tests-are-independent finding
and the GCP-403 not-reproducible determination required extra targeted verification runs
(combined-file + broader full-suite slices) beyond isolated per-file runs — expected
investigative overhead for order-dependent/environment-dependent hypotheses, not a defect.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Cluster 9 Group D1 is fully closed: 8/11 tests individually investigated and quarantined
with distinct, evidence-backed root causes; 3/11 investigated and confirmed not
reproducible in this sandbox (documented, not silently dropped). Ledger updated,
`test_skip_registry.py` meta-gate green. One genuine follow-up item is flagged for
Phase 150: add an `otics` synthesizer to `tests/_cbom_profiles.py::PROFILE_ENDPOINTS`
per CLAUDE.md's Chaos Lab Maintenance rule. No blockers introduced for the remaining
Phase 149 clusters/groups in subsequent 149-1X plans.

---
*Phase: 149-test-suite-triage*
*Completed: 2026-08-12*

## Self-Check

- `tests/test_cbom_schema_validation.py` modified: FOUND
- `tests/test_cli_correctness.py` modified: FOUND
- `tests/test_cli_init.py` modified: FOUND
- `tests/test_compliance_title_join.py` modified: FOUND
- `tests/test_email_run_scan_wiring.py` modified: FOUND
- `tests/test_install_errors.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- Commit `faf7c5e` (Task 1): FOUND
- Commit `12c342b` (Task 2): FOUND
- Commit `f8fe376` (Task 3): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- `pytest tests/test_cbom_schema_validation.py tests/test_cli_correctness.py tests/test_cli_init.py tests/test_compliance_title_join.py tests/test_email_run_scan_wiring.py tests/test_errors_cmd.py tests/test_install_errors.py tests/test_posture_scorefix125.py -q -m ""`: CONFIRMED (110 passed, 8 xfailed, 0 failed)

## Self-Check: PASSED
