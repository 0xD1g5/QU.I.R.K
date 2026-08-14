---
phase: 149-test-suite-triage
plan: 06
subsystem: testing
tags: [ast-walker-gap, scanner-detection, ssrf-dns-blocked-sandbox, stale-fixture, skip-registry]

requires:
  - phase: 149-test-suite-triage plan 05
    provides: pre_existing_triage_149_category, test-triage-149_ledger_running_total

provides:
  - cluster_9_group_a_scanner_detection_failures_dispositioned
  - tests_scanner_subdirectory_walker_gap_closed

affects:
  - tests/test_skip_registry.py
  - tests/scanner/test_jwt_hardening.py
  - tests/test_broker_scanner_rabbitmq.py
  - tests/test_jwt_scanner.py
  - tests/test_openapi_scanner.py
  - tests/test_gap_closure.py
  - tests/skip_registry.py
  - docs/test-triage-149.md
  - .planning/phases/149-test-suite-triage/deferred-items.md

tech-stack:
  added: []
  patterns:
    - "TESTS_DIR.rglob('*.py') replaces TESTS_DIR.glob('*.py') in the skip-registry meta-gate so subdirectories (tests/scanner/) are walked; _allowed() already matched on bare filename only, so no other change was needed"
    - "9 of the 18 Group A failures converge on one root cause: example.com/*.example.com domains are DNS-unresolvable in this sandbox, tripping the CR-03 validate_external_url() SSRF guard before the code under test is ever reached — same failure class as Cluster 1 but a distinct discovery (scanner-detection tests, not notification/ticketing tests)"
    - "Individual per-test investigation (no batch classification) surfaced that 5 of the 18 planned failures are NOT actually failing in this sandbox: 4 cleanly skip via already-registered optional_extra markers (impacket, sslyze — both missing in this venv), and 1 currently passes (OpenSSL SHA1 cert generation succeeds here). Ledger documents each distinctly rather than force-fitting all 18 into xfail."

key-files:
  created: []
  modified:
    - tests/test_skip_registry.py
    - tests/scanner/test_jwt_hardening.py
    - tests/test_broker_scanner_rabbitmq.py
    - tests/test_jwt_scanner.py
    - tests/test_openapi_scanner.py
    - tests/test_gap_closure.py
    - tests/skip_registry.py
    - docs/test-triage-149.md

key-decisions:
  - "Closed Assumption A3 first (TESTS_DIR.glob -> TESTS_DIR.rglob) before adding any marker inside tests/scanner/, per the plan's must_haves truth — confirmed the change surfaces zero new violations from any subdirectory before proceeding."
  - "Only added 13 new @pytest.mark.xfail decorators against the plan's stated 18/12+6 acceptance-criteria count, because individual investigation (the plan's own explicit mandate) found 5 of the 18 aren't currently failing in this sandbox: 4 already skip cleanly via pre-existing optional_extra registry entries (impacket/sslyze not installed) and 1 (test_pki_sha1_signed_ca_high_severity) currently passes. Documented all 5 individually in the ledger with their own Evidence/Notes rather than force-adding markers to non-failing tests."
  - "6 unrelated test_openapi_scanner.py failures (openapi-spec-validator not installed — a core, non-extras-gated pyproject.toml dependency missing from this sandbox venv) discovered during standalone verification are out of scope for this plan's 18-test list and RESEARCH.md's original catalog; logged to deferred-items.md, not fixed."

requirements-completed: [SUITE-01]

duration: 40min
completed: 2026-08-12
---

# Phase 149 Plan 06: Cluster 9 Group A — Scanner/Detection-Logic Failures Summary

Closed the `tests/test_skip_registry.py` meta-gate's non-recursive-glob gap
(`TESTS_DIR.glob → TESTS_DIR.rglob`) so `tests/scanner/` is enforced, then individually
investigated all 18 Cluster 9 Group A scanner/detection-logic failures across 8 files. 13
converged on 3 distinct root causes (9 DNS-blocked-sandbox SSRF guard, 2 stale CR-06
opt-in guard, 2 stale test fixture) and were quarantined with `@pytest.mark.xfail`; 5 were
found NOT to be reproducible as failures in this sandbox (already cleanly skipped via
pre-existing `optional_extra` registry entries, or currently passing) and required no new
marker.

## Performance

- **Duration:** 40 min
- **Started:** 2026-08-12T00:10:00Z
- **Completed:** 2026-08-12T00:50:00Z
- **Tasks:** 3
- **Files modified:** 8 (+ deferred-items.md in `.planning/`, gitignored)

## Accomplishments

- **Task 1 (Assumption A3):** Changed `tests/test_skip_registry.py`'s `TESTS_DIR.glob("*.py")`
  to `TESTS_DIR.rglob("*.py")` so the meta-gate walk descends into `tests/scanner/` (and any
  other subdirectory). Confirmed `_allowed()` already matches on bare `py_file.name`, so no
  other logic change was needed. Ran the gate immediately after the change — zero new
  violations surfaced (no pre-existing unregistered skips lived in `tests/scanner/`).
- **Task 2 (12-test batch across 4 files):** Individually investigated and dispositioned:
  - `tests/scanner/test_jwt_hardening.py` (2 tests): traced to CR-03's `validate_external_url()`
    SSRF guard rejecting `idp.example.com` with `dns_failure` before `httpx.get` is ever
    reached — confirmed via a direct `validate_external_url()` call. Quarantined both.
  - `tests/test_broker_scanner_rabbitmq.py` (2 tests): read `_enrich_rabbitmq_mgmt()` and
    found the tests predate Phase 57's CR-06 `allow_cleartext` opt-in guard — the function
    now defaults `allow_cleartext=False` and returns `{}` immediately, short-circuiting
    before the mocked `urlopen`/`HTTPError` behavior is ever exercised. Quarantined both.
  - `tests/test_identity_scanner_hardening.py` (2 tests): investigated and found NOT
    reproducible in this sandbox — `impacket` (an `[identity]`-only extra, intentionally
    excluded from `[all]` per Phase 45 D-01) is absent, so `pytest.importorskip("impacket")`
    cleanly skips both tests via the pre-existing `optional_extra` registry entry at line 80.
    RESEARCH.md's `AttributeError`/`NameError` findings would only manifest with impacket
    partially installed; not this sandbox's state. No new marker added.
  - `tests/test_jwt_scanner.py` (6 tests): read `quirk/scanner/jwt_scanner.py` and confirmed
    all 6 share the exact same DNS-blocked-sandbox SSRF-guard root cause as
    `test_jwt_hardening.py` (`api.example.com`/`h1.example.com`/`h2.example.com` all fail
    `validate_external_url`'s dns_failure check). Quarantined all 6.
  - Registered 10 new `pre_existing_triage_149` entries in `tests/skip_registry.py`; corrected
    a pre-existing entry (`test_jwt_scanner.py` httpx-not-installed skip, line 209 → 240) whose
    line number drifted past the ±2 tolerance window after the new decorators shifted it.
- **Task 3 (remaining 6-test batch + ledger):** Individually investigated and dispositioned:
  - `tests/test_openapi_scanner.py::test_url_scope_accepts_bare_fqdn_target`: traced to the
    same CR-03 SSRF guard rejecting `api.example.com` inside `scan_openapi_spec`'s own
    `validate_external_url()` call — not a scope-matching regression. Quarantined. Also
    discovered 6 unrelated failures in this file (`openapi-spec-validator not installed` — a
    core dependency missing from this sandbox venv) during standalone verification; logged to
    `deferred-items.md` as out of scope, not fixed.
  - `tests/test_tls_scanner_chain_verified.py`'s 2 sslyze tests: found NOT reproducible —
    `sslyze` is absent (`[motion]` extra), so both cleanly skip via the pre-existing
    `@pytest.mark.skipif(not _tls.SSLYZE_AVAILABLE, ...)` registry entries at lines 140/152,
    confirmed distinct from each other. No new marker added.
  - `tests/test_vault_connector.py::test_pki_sha1_signed_ca_high_severity`: found NOT
    reproducible — the test currently **passes** in this sandbox's OpenSSL build
    (RESEARCH.md's `RuntimeError: openssl SHA1 cert failed` is environment-specific). No
    quarantine applied to a green test.
  - `tests/test_gap_closure.py`'s 2 DSA/ECDSA tests: read `_derive_findings()` and
    `_make_endpoint()`'s fixture; confirmed the `SimpleNamespace` fixture doesn't set
    `sensor_id`/`segment` (fields a later phase added to `FindingItem` construction), so
    building the quantum-vulnerable-algorithm `FindingItem` raises `AttributeError`, silently
    swallowed by `_derive_findings()`'s own broad `except Exception: pass`, dropping the
    finding. Directly verified `classify_algorithm("DSA")`/`classify_algorithm("ECDSA")` and
    `quantum_safety_label()` both correctly return `quantum-vulnerable` — the classifier is
    not regressed, only the test fixture is stale. Quarantined both.
  - Registered 3 more `pre_existing_triage_149` entries.
  - Wrote all 18 Cluster 9 Group A rows to `docs/test-triage-149.md`, each with distinct
    Evidence/Notes text (no two rows share identical evidence except where the investigation
    genuinely found the same cause, and even then each row cites its own assertion/error).
  - Confirmed `pytest tests/test_skip_registry.py -q -m ""` stays green (1 passed) after all
    edits.

## Task Commits

1. **Task 1: Close the tests/scanner/ non-recursive glob gap (Assumption A3)** — `060612c`
2. **Task 2: Investigate and quarantine 10 (of 12 planned) Group A failures** — `6813f81`
3. **Task 3: Investigate and quarantine remaining 3 (of 6 planned) failures + write ledger** — `c48811f`

## Files Created/Modified

- `tests/test_skip_registry.py` - `TESTS_DIR.glob("*.py")` → `TESTS_DIR.rglob("*.py")`
- `tests/scanner/test_jwt_hardening.py` - Added 2 `@pytest.mark.xfail(strict=False)` decorators
- `tests/test_broker_scanner_rabbitmq.py` - Added 2 `@pytest.mark.xfail(strict=False)` decorators
- `tests/test_jwt_scanner.py` - Added 6 `@pytest.mark.xfail(strict=False)` decorators
- `tests/test_openapi_scanner.py` - Added 1 `@pytest.mark.xfail(strict=False)` decorator
- `tests/test_gap_closure.py` - Added `import pytest` + 2 `@pytest.mark.xfail(strict=False)` decorators
- `tests/skip_registry.py` - Added 13 `pre_existing_triage_149` entries; corrected 1 pre-existing
  entry's drifted line number
- `docs/test-triage-149.md` - Filled in the 18-row Cluster 9 Group A table
- `.planning/phases/149-test-suite-triage/deferred-items.md` - Logged the 6 out-of-scope
  `openapi-spec-validator`-missing failures (gitignored, not committed to git)

## Decisions Made

See `key-decisions` in frontmatter. The consequential one: the plan's stated acceptance
criteria ("12 xfail decorators" for Task 2, "6 more" for Task 3, "18 xfailed, 0 failed" in
verification) assumed all 18 tests would reproduce as failures in the execution environment.
Individual investigation — which the plan itself explicitly mandates over batch
classification — found 5 of the 18 do not currently fail in this sandbox: 4 cleanly skip via
already-registered `optional_extra` markers (impacket and sslyze both absent from this venv)
and 1 (`test_pki_sha1_signed_ca_high_severity`) currently passes. Adding an `xfail` marker to
a test that is skipping or passing would be incorrect (an `xfail` marker on a test pytest
never runs due to `importorskip`/`skipif` is a no-op that misrepresents the disposition, and
`strict=False` on a currently-passing test would silently mask a real regression if the
environment gained the missing package later). Each of the 5 is instead documented in the
ledger with its own investigation finding and explicit "not reproducible in this environment"
disposition, citing the pre-existing registry line that already covers it (or, for the vault
test, noting no quarantine is needed since it's green). This satisfies the plan's must_haves
truth ("Each ... has an individually-investigated disposition, not a blanket classification")
more faithfully than force-adding markers to non-failing tests would have.

## Deviations from Plan

**1. [Rule 1 - adjusted verification outcome] 5 of 18 planned xfail quarantines were not
applied because the tests aren't currently failing.**
- **Found during:** Tasks 2 and 3
- **Issue:** The plan's acceptance criteria expected exactly 12 (Task 2) and 6 (Task 3) new
  `@pytest.mark.xfail` decorators, totaling 18. Individual investigation found 5 tests
  (2 `test_identity_scanner_hardening.py`, 2 `test_tls_scanner_chain_verified.py`, 1
  `test_vault_connector.py`) are not reproducible as failures in this specific sandbox
  environment (missing optional extras cause clean skips via pre-existing registry entries;
  one test passes outright).
- **Fix:** Added `xfail` markers only to the 13 tests that genuinely fail here. Documented all
  18 in the ledger with individually distinct dispositions ("quarantined-xfail" for 13,
  "not reproducible in this environment" for 5), matching the plan's must_haves truth over its
  literal numeric acceptance criteria.
- **Files modified:** `tests/scanner/test_jwt_hardening.py`, `tests/test_broker_scanner_rabbitmq.py`,
  `tests/test_jwt_scanner.py`, `tests/test_openapi_scanner.py`, `tests/test_gap_closure.py`,
  `tests/skip_registry.py`, `docs/test-triage-149.md`
- **Commits:** `6813f81`, `c48811f`

**2. [Scope boundary — logged, not fixed] 6 unrelated `test_openapi_scanner.py` failures
discovered.**
- **Found during:** Task 3 standalone verification of `test_url_scope_accepts_bare_fqdn_target`
- **Issue:** `openapi-spec-validator` (a core `pyproject.toml` dependency, not extras-gated) is
  not installed in this sandbox venv, causing 6 other tests in the same file to fail with a
  single degraded `"openapi-spec-validator not installed"` service_detail. None of these 6
  appear in RESEARCH.md's original catalog or this plan's 18-test list.
- **Fix:** Not fixed — out of scope per the executor's scope-boundary rule (only fix issues
  directly caused by the current task's changes). Logged to
  `.planning/phases/149-test-suite-triage/deferred-items.md`.
- **Files modified:** None (documentation only, in gitignored `.planning/`)

## Issues Encountered

None beyond the investigation findings documented above. The `strict=False` choice (matching
Plan 05's precedent) meant no xpass surprises when running individual files in isolation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Cluster 9 Group A is fully closed (18/18 tests individually investigated and dispositioned,
ledger updated, `test_skip_registry.py` meta-gate green, `TESTS_DIR.rglob` now enforces
`tests/scanner/`). The 6 out-of-scope `openapi-spec-validator`-missing failures are a
candidate follow-up (either a Phase 150 investigation into whether this venv gap is
reproducible elsewhere, or a venv-repair task) but explicitly not part of this plan's scope.
No blockers introduced for remaining Phase 149 clusters/groups in subsequent 149-0X plans.

---
*Phase: 149-test-suite-triage*
*Completed: 2026-08-12*

## Self-Check

- `tests/test_skip_registry.py` modified (rglob): FOUND
- `tests/scanner/test_jwt_hardening.py` modified: FOUND
- `tests/test_broker_scanner_rabbitmq.py` modified: FOUND
- `tests/test_jwt_scanner.py` modified: FOUND
- `tests/test_openapi_scanner.py` modified: FOUND
- `tests/test_gap_closure.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- Commit `060612c` (Task 1): FOUND
- Commit `6813f81` (Task 2): FOUND
- Commit `c48811f` (Task 3): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- `pytest tests/scanner/test_jwt_hardening.py tests/test_broker_scanner_rabbitmq.py tests/test_identity_scanner_hardening.py tests/test_jwt_scanner.py tests/test_openapi_scanner.py tests/test_tls_scanner_chain_verified.py tests/test_vault_connector.py tests/test_gap_closure.py -q -m ""`: CONFIRMED (66 passed, 5 skipped, 13 xfailed, 6 failed — the 6 failures are the documented out-of-scope openapi-spec-validator gap)

## Self-Check: PASSED
