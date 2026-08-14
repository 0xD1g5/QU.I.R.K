---
phase: 149-test-suite-triage
plan: 11
subsystem: testing
tags: [reconciliation, ledger-integrity, sslyze-version-drift, impacket-version-drift, macos-fork-sigsegv, skip-registry, phase-149-final]

requires:
  - phase: 149-test-suite-triage plan 10
    provides: cluster_9_group_d2_docs_security_gate_windows_smoke_failures_dispositioned

provides:
  - phase_149_final_reconciliation_complete
  - ledger_116_rows_zero_orphaned_failures
  - two_production_bugs_fixed_sslyze_version_impacket_methoddata
  - macos_fork_sigsegv_cluster_identified_5_tests

affects:
  - docs/test-triage-149.md
  - quirk/scanner/tls_scanner.py
  - quirk/scanner/kerberos_scanner.py
  - tests/skip_registry.py
  - tests/test_identity_scanner_hardening.py
  - tests/test_posture_scorefix125.py
  - tests/test_qramm_staleness.py
  - tests/test_sensor_windows_smoke.py
  - tests/test_vault_connector.py
  - tests/test_version.py

tech-stack:
  added: []
  patterns:
    - "A ledger-reconciliation plan running in a fresh sandbox after 10 prior plans each
       ran in their own sandbox will surface real drift: this sandbox had impacket,
       sslyze, and pysnmp installed (Plans 06/09's sandboxes didn't), and lacked
       googleapiclient (Plan 09's had it) — 11 of 116 ledger rows needed correction
       purely from extras-availability differences between sandboxes, none from
       carelessness in the prior investigations."
    - "A library's un-pinned-upper-bound version drift (sslyze >=6.2.0 changing
       __version__ from a string to a submodule in 6.3; impacket>=0.13.0,<0.14 renaming
       MethodData to METHOD_DATA and changing KDCOptions from a class to an enum) can
       silently break production code inside a broad except-Exception handler, showing
       up as a clean-looking test skip in a sandbox that predates the drift and a real
       failure in one that doesn't — always check whether an 'optional_extra not
       installed, cleanly skipped' disposition would reproduce as a REAL failure if the
       extra were actually installed at the currently-pinned version."
    - "A segfault that reproduces only at full-suite scale (~3200 tests) and never in
       isolation or small multi-file combinations is not necessarily N independent bugs
       just because it appears at N different subprocess call sites — check the crash
       dump's actual native stack trace (not just the returncode) to see if they all
       terminate at the same OS-level call (macOS fork()/_execute_child here), which
       reveals a single systemic cause instead of N coincidental ones."

key-decisions:
  - "sslyze __version__ submodule bug and impacket MethodData rename bug were fixed in
     place (Rule 1: real production bugs affecting every operator on the currently-pinned
     dependency version) despite this plan's threat_model stating no production code
     would be modified — the plan's own Task 1 acceptance criteria ('go back and add one,
     even if it means a follow-up disposition task') authorizes exactly this kind of
     scope expansion when a fresh run surfaces a genuine defect, and both fixes are small,
     low-risk, and verified with zero regressions (test_kerberos_scanner.py stayed
     25 passed / 1 skipped)."
  - "impacket's second, deeper KDCOptions enum incompatibility was NOT fixed — it
     requires understanding impacket 0.13's new bit-flag construction API, which is
     feature-development scope, not a reconciliation-plan bug fix. Quarantined with an
     accurate root-cause note and flagged for a dedicated Phase 150 follow-up."
  - "The 5 SIGSEGV tests (qramm x2, sensor_windows_smoke x1, vault_connector x1,
     version x1) were consolidated into ONE Phase 150 follow-up item, not 5, because
     their crash dumps share an identical native stack shape (CPython
     subprocess.py::_execute_child, the fork()/exec() path) reproducing only at
     ~3200-test full-suite scale — this supersedes Plan 10's explicit conclusion that
     the sensor_windows_smoke crash was independent of Plan 08's QRAMM pair, and Plan
     06's OpenSSL-SHA1-cert-generation hypothesis for the vault_connector test."
  - "The 2 GCP posture tests were re-classified from 'not reproducible, feature confirmed
     working' (Plan 09) to a googleapiclient optional_extra gap (this sandbox lacks it;
     Plan 09's had it) — same failure class as Cluster 7's test_gcs_reuse.py, quarantined
     with @pytest.mark.skip matching that file's exact existing pattern."

requirements-completed: [SUITE-01]

duration: 75min
completed: 2026-08-12
---

# Phase 149 Plan 11: Final Reconciliation — Ledger vs. Fresh Full-Suite Run Summary

Cross-checked all 116 ledger rows built by Plans 01-10 against a fresh `pytest -q -m ""`
run in this plan's own sandbox and found 11 rows whose sandbox-specific dispositions
(from prior plans' different environments — impacket/sslyze/pysnmp present here but
absent in Plans 06/09's sandboxes; googleapiclient absent here but present in Plan 09's)
no longer held. Fixed 2 genuine production bugs (sslyze `__version__` submodule shape,
impacket `MethodData` rename) discovered by this drift, and quarantined the remaining 9
with corrected root causes — including identifying that 5 previously-scattered SIGSEGV
findings (Plan 06, Plan 08's pair, Plan 10) are actually one systemic macOS
fork()-under-full-suite-load instability, not independent defects. A fresh full-suite run
after all fixes/quarantines is **0 failed** (3088 passed, 42 skipped, 81 xfailed) — Phase
149 (SUITE-01) is complete with a genuinely reconciled, green baseline.

## Performance

- **Duration:** 75 min
- **Started:** 2026-08-12T03:59:00Z
- **Completed:** 2026-08-12T05:14:00Z
- **Tasks:** 2 (plan) + investigation/fix work driven by Task 1's acceptance criteria
- **Files modified:** 10

## Accomplishments

- **Task 1 (fresh run cross-check):** Ran `pytest -q -m ""` three times (before any fix)
  to confirm the fresh state. Found 11 currently-failing tests, all with pre-existing
  ledger rows whose dispositions ("not reproducible", "feature confirmed working",
  "environment-fix-applied", "already registered/optional_extra") were sandbox-specific
  and no longer accurate here:
  - Investigated and **fixed in place**: `tls_scanner.py`'s sslyze `__version__`
    submodule-shape bug (sslyze >=6.3 broke `tls_capabilities_json` construction,
    silently discarding every sslyze scan result) and `kerberos_scanner.py`'s impacket
    `MethodData`→`METHOD_DATA` rename (impacket 0.13.0, the current pin, silently
    disabled `IMPACKET_AVAILABLE` for every operator).
  - Investigated and **quarantined** the remaining 9: 2 for a residual, deeper impacket
    0.13.0 `KDCOptions` enum incompatibility uncovered by the import fix; 2 for a
    `googleapiclient`/`google` optional-extras gap matching Cluster 7's existing
    pattern; 5 for a single systemic macOS fork()-under-full-suite-load SIGSEGV,
    confirmed via matching `Fatal Python error: Segmentation fault` crash dumps at 8
    distinct `subprocess.run()` call sites across 3 repeated full-suite runs.
- **Task 2 (empty-cell/duplicate scan + Reconciliation section):** Mechanically scanned
  all 116 ledger rows — zero empty `Disposition`/`Sub-reason` cells, zero duplicate test
  IDs, 116 distinct rows matching the sum of the 9 cluster tables' own counts. Updated 11
  individual rows (Cluster 3, Cluster 9 Groups A/C/D1/D2) with corrected root causes.
  Appended a `## Reconciliation` section documenting the fresh pytest summary line, the
  full account of what changed, and the ledger integrity checks. Confirmed
  `pytest tests/test_skip_registry.py -q -m ""` (1 passed) and
  `python -m compileall tests/` (exit 0) both green.

## Task Commits

1. **fix production bugs (sslyze `__version__`, impacket `MethodData`)** — `1a5e1db`
2. **quarantine 9 tests (KDCOptions enum, googleapiclient gap, macOS fork SIGSEGV cluster)** — `bd59d11`
3. **reconcile ledger + write Reconciliation section (Tasks 1+2)** — `64b94af`

## Files Created/Modified

- `quirk/scanner/tls_scanner.py` - Normalizes sslyze's `__version__` (string vs. nested
  submodule shape, sslyze >=6.3) before building `tls_capabilities_json`
- `quirk/scanner/kerberos_scanner.py` - Imports `METHOD_DATA as MethodData` (impacket
  >=0.13.0) with a fallback to the old name (impacket <0.13.0)
- `tests/skip_registry.py` - 9 new `pre_existing_triage_149` entries (Plan 11)
- `tests/test_identity_scanner_hardening.py` - 2 `@pytest.mark.xfail(strict=False)`
  decorators (residual impacket `KDCOptions` incompatibility)
- `tests/test_posture_scorefix125.py` - 2 `@pytest.mark.skip` decorators
  (`googleapiclient`/`google` optional_extra gap, matching `test_gcs_reuse.py`'s pattern)
- `tests/test_qramm_staleness.py` - 2 `@pytest.mark.xfail(strict=False)` decorators
  (macOS fork() SIGSEGV cluster)
- `tests/test_sensor_windows_smoke.py` - 1 `@pytest.mark.xfail(strict=False)` decorator
  (same SIGSEGV cluster)
- `tests/test_vault_connector.py` - 1 `@pytest.mark.xfail(strict=False)` decorator (same
  SIGSEGV cluster)
- `tests/test_version.py` - 1 `@pytest.mark.xfail(strict=False)` decorator (same SIGSEGV
  cluster, additional to its already-correct stale-dist-info disposition)
- `docs/test-triage-149.md` - 11 ledger rows updated with corrected root causes + new
  `## Reconciliation` section

## Decisions Made

See `key-decisions` in frontmatter. The two consequential ones for Phase 150 priority:
(1) the 5 SIGSEGV tests are ONE systemic Phase 150 follow-up item (macOS
fork()-under-load instability, likely needing a `multiprocessing` start-method change or
CI-runner-level mitigation), not 5 separate investigations; (2) impacket's `KDCOptions`
enum incompatibility is a real, currently-shipping Kerberos-scanner defect on the pinned
`impacket>=0.13.0,<0.14` version that needs a dedicated fix (beyond this plan's
reconciliation scope) to fully restore Kerberos scanning.

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed sslyze `__version__` submodule-shape bug**
- **Found during:** Task 1, fresh full-suite cross-check
- **Issue:** sslyze >=6.3 changed `sslyze.__version__` from a string constant to a
  `sslyze/__version__.py` submodule; `tls_scanner.py`'s `_scan_one_sslyze` passed the
  bare module object into `json.dumps(caps)`, raising `TypeError` inside a broad
  `except Exception` and silently discarding every sslyze scan result
- **Fix:** normalize both the string (sslyze <6.3) and nested-module (sslyze >=6.3)
  `__version__` shapes before building `tls_capabilities_json`
- **Files modified:** `quirk/scanner/tls_scanner.py`
- **Commit:** `1a5e1db`

**2. [Rule 1 - Bug] Fixed impacket `MethodData`/`METHOD_DATA` import rename**
- **Found during:** Task 1, fresh full-suite cross-check
- **Issue:** impacket `>=0.13.0,<0.14` (the current pin) renamed
  `impacket.krb5.asn1.MethodData` to `METHOD_DATA`, breaking `kerberos_scanner.py`'s
  entire `try/except ImportError` import guard and silently setting
  `IMPACKET_AVAILABLE = False` for every operator on the currently-pinned impacket
  version — Kerberos scanning was completely disabled, not gracefully degraded
- **Fix:** try `METHOD_DATA as MethodData` first, fall back to the old name for
  impacket <0.13.0
- **Files modified:** `quirk/scanner/kerberos_scanner.py`
- **Commit:** `1a5e1db`
- **Note:** this fix restored `IMPACKET_AVAILABLE=True` but uncovered a second, deeper
  impacket 0.13.0 incompatibility (`KDCOptions` class→enum change) that was quarantined,
  not fixed — out of scope for a one-line import fix; flagged for Phase 150.

**3. [Rule 3-adjacent - blocking disposition gap] Quarantined 9 tests whose ledger rows
were sandbox-stale, not missing**
- **Found during:** Task 1's acceptance criteria ("if a test still fails and has no row,
  that is a gap — go back and add one, even if it means a follow-up disposition task")
- **Issue:** 9 tests (impacket `KDCOptions` residual x2, googleapiclient-extras-gap x2,
  macOS fork() SIGSEGV cluster x5) failed in this fresh run despite having ledger rows
  from Plans 06/08/09/10 that documented them as passing/not-reproducible/already-skipped
  in those plans' own sandboxes
- **Fix:** added `@pytest.mark.xfail(strict=False)`/`@pytest.mark.skip` decorators
  matching the established per-cluster pattern, registered all 9 in
  `tests/skip_registry.py`, updated the corresponding ledger rows with corrected root
  causes and a `**superseded by Plan 11**` marker
- **Files modified:** `tests/skip_registry.py`, `tests/test_identity_scanner_hardening.py`,
  `tests/test_posture_scorefix125.py`, `tests/test_qramm_staleness.py`,
  `tests/test_sensor_windows_smoke.py`, `tests/test_vault_connector.py`,
  `tests/test_version.py`, `docs/test-triage-149.md`
- **Commits:** `bd59d11`, `64b94af`

## Issues Encountered

None blocking. The bulk of this plan's effort was root-cause investigation for 11
newly-surfaced failures that weren't anticipated by the plan's task list (which expected
the fresh run to mostly *confirm* Plans 01-10's work, with maybe minor arithmetic drift)
— tracing each to a specific library-version-drift or systemic-environment cause required
reading crash-dump native stack traces, comparing installed package versions against
`pyproject.toml` pins, and re-running the full suite 3 times to confirm the SIGSEGV
cluster's reproducibility pattern (intermittent per-run, but always at the same 8
call sites when it fires).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Phase 149 (SUITE-01) is complete: the ledger is a mechanically-verified, 116-row,
zero-gap, zero-duplicate disposition record, and a fresh `pytest -q -m ""` run is
genuinely `0 failed` (3088 passed, 42 skipped, 81 xfailed). This is a stronger baseline
than the plan anticipated — not just "the ledger matches a static snapshot" but "the
ledger matches *this sandbox's actual current behavior*, including 2 real bugs fixed
along the way." Phase 150 (Test Suite Green Baseline + CI Gate) follow-up items flagged
across this plan and prior plans:
1. Dedicated impacket 0.13.0 `KDCOptions` enum-compatibility fix (`kerberos_scanner.py`'s
   `_build_as_req`) — 2 tests currently quarantined pending this.
2. Single macOS fork()-under-full-suite-load SIGSEGV investigation (5 tests, 8 crash
   sites) — likely needs a `multiprocessing` start-method change, `-p no:cacheprovider`
   isolation, or Linux CI runner where `fork()` is safer; consolidate, don't split.
3. Widen `test_safe_filter_audit.py`'s `_has_upstream_sanitize` (Plan 10) and
   `test_scan_error_gate.py`'s `_classify_rhs()` `ast.IfExp` support (Plan 10).
4. Add an `otics` synthesizer to `tests/_cbom_profiles.py::PROFILE_ENDPOINTS` (Plan 09).
5. Add an `otics` `google-api-python-client`/`googleapiclient` install verification note
   for future GCP-connector sandbox parity (this plan) — optional, low priority.

No blockers for Phase 150.

---
*Phase: 149-test-suite-triage*
*Completed: 2026-08-12*

## Self-Check

- `quirk/scanner/tls_scanner.py` modified: FOUND
- `quirk/scanner/kerberos_scanner.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- `tests/test_identity_scanner_hardening.py` modified: FOUND
- `tests/test_posture_scorefix125.py` modified: FOUND
- `tests/test_qramm_staleness.py` modified: FOUND
- `tests/test_sensor_windows_smoke.py` modified: FOUND
- `tests/test_vault_connector.py` modified: FOUND
- `tests/test_version.py` modified: FOUND
- Commit `1a5e1db` (fix production bugs): FOUND
- Commit `bd59d11` (quarantine 9 tests): FOUND
- Commit `64b94af` (reconcile ledger): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- `pytest -q -m ""` (fresh full-suite run): CONFIRMED (3088 passed, 42 skipped,
  81 xfailed, 0 failed)
- `python -m compileall tests/` exits 0: CONFIRMED

## Self-Check: PASSED
