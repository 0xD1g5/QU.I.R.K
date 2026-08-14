# Phase 149: Test Suite Triage - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Every test failing in a clean, full-suite `pytest` run (not the CI-default `-m 'not slow'` subset)
gets an explicit, written disposition — fixed, quarantined-with-reason, or deleted-as-obsolete —
recorded in a ledger whose total matches the actual failure count. Quarantined tests are marked in
a machine-checkable way that references the ledger, not silently skipped or invisibly excluded.

This phase does **not** attempt to make the suite green (that's Phase 150, SUITE-02/03) and does
not add a CI gate (also Phase 150). It produces the disposition record that determines whether
Phase 150 is small (mostly pre-applied quarantines) or large.

</domain>

<decisions>
## Implementation Decisions

### Fix-vs-defer effort split

- **D-01:** Phase 149 is **disposition-only** — the phase does not fix any failing test's
  underlying code or test logic, even when a fix looks trivial. Every one of the ~108 failures
  gets classified as fixed / quarantined / deleted based on triage judgment, not by actually
  patching code. All real fixing work is Phase 150's job, sized by this phase's ledger.
  Exception: a failure whose correct disposition **is** "fixed" only in the narrow sense that the
  test itself was asserting something already-stale (e.g. a hardcoded version string, a renamed
  constant) may be corrected as part of writing an accurate disposition — but this is boundary
  hygiene on the ledger entry, not a fix-the-implementation pass. When in doubt, quarantine and let
  Phase 150 decide.

### Quarantine mechanism

- **D-02:** Reuse `tests/skip_registry.py`'s existing `ALLOWED_SKIPS` list and its enforcing
  meta-test (`tests/test_skip_registry.py::test_no_unregistered_skips`), both built in Phase 41.
  Add a new `category` value (e.g. `"pre_existing_triage_149"`) distinct from the existing
  `"optional_extra"` / `"live_infra"` categories, so the ~108 triage-quarantined tests are
  filterable/countable separately from the pre-existing ~20-entry optional-extra/live-infra skip
  list.
- **D-03:** Quarantined tests get `pytest.mark.skip(reason=...)` or `@pytest.mark.xfail(reason=...)`
  (whichever fits the failure — `xfail` where the test still usefully documents intent and runs,
  `skip` where running it is pointless or environment-broken) with a reason string that cites the
  ledger (e.g. `"TRIAGE-149: see docs/test-triage-149.md#<test-id>"`), and a matching entry added to
  `ALLOWED_SKIPS` so the meta-gate stays green.
- **D-04 (pre-existing defect discovered during discussion, in scope for this phase to repair):**
  `test_no_unregistered_skips` is **currently failing** — it found ~15+ unregistered skip markers
  that have drifted since Phase 41 (new skips added without registry entries, and/or line-number
  drift past the ±2 tolerance). Repairing this drift (registering or deleting each stale entry) is
  necessary groundwork before D-02/D-03 can add the 149 triage entries on top of a working gate —
  do this repair as part of this phase, not as a separate unticketed fix.

### Deletion bar

- **D-05:** A failing test is deleted as obsolete **only** when the specific function, module, or
  behavior it exercises has been confirmed (via grep/read, not assumption) to no longer exist in
  the codebase — e.g. it tests a removed connector, a renamed function it still imports, or a
  behavior superseded by a different implementation. Every other failure — flaky, wrong assumption,
  outdated fixture value, environment-dependent — gets quarantined with a reason, never deleted.
  This is the conservative bar: nothing is silently lost, and every deletion's ledger entry must
  name the grep/read evidence that justified it.

### Claude's Discretion

- Exact ledger file format/location (see Specific Ideas below for the one concrete requirement:
  it must show a per-test disposition, not just per-file).
- Whether individual quarantine markers use `skip` or `xfail` per-test (D-03 gives the general rule;
  applying it to each of the ~108 is executor judgment).
- Naming convention for ledger entry IDs referenced in `reason=` strings.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` §"Test Signal Integrity" — SUITE-01 (this phase), SUITE-02/SUITE-03
  (Phase 150, depends on this phase's output).
- `.planning/ROADMAP.md` §"Phase 149: Test Suite Triage" — goal, success criteria, and the explicit
  note that Phase 150's size is unknown until this phase's ledger exists.
- `.planning/HORIZON.md` lines 140-179 — the v5.12 "Release & Verification Integrity" rationale;
  the ~102(now ~108)-failures-since-Phase-97 evidence that motivated this phase.

### Existing quarantine/skip machinery (Phase 41) — reuse target for D-02/D-03/D-04
- `tests/skip_registry.py` — `ALLOWED_SKIPS` list: `(file, line, category, reason)` tuples,
  currently 2 categories (`optional_extra`, `live_infra`), ~20 entries. Extend with the new
  `pre_existing_triage_149` category rather than building parallel machinery.
- `tests/test_skip_registry.py` — the AST-walking meta-test gate (`test_no_unregistered_skips`)
  that fails on any unregistered `pytest.skip` / `pytest.importorskip` / `@pytest.mark.skipif` in
  `tests/*.py`. **Currently failing** (see D-04) — must be repaired before/while adding the 149
  entries. Note: this gate's AST walk does NOT currently detect `@pytest.mark.xfail` — confirm
  during planning whether xfail markers need their own registry lane or stay ungated.

### Pytest configuration
- `pyproject.toml` lines ~152-156 — `markers = ["slow: ..."]` and `addopts = "-m 'not slow'"`.
  The triage run for this phase must NOT use the default addopts (it must include `slow`-marked
  tests) to match Success Criterion 1's "not just the `-m 'not slow'` default."

### CI test invocation (context for why nothing currently catches these failures)
- `.github/workflows/python-ci.yml` — runs only `test_sensor_windows_smoke.py`,
  `test_sensor_no_verify_false.py`, and packaging/build jobs. There is **no general pytest job** in
  CI today — confirms why 108 failures have been invisible; Phase 150 (not this phase) adds that
  gate.
- `.github/workflows/python-staleness.yml` — runs `pytest tests/test_install_errors.py -x -q -m
  "not slow"` as a narrow smoke check only.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/skip_registry.py` + `tests/test_skip_registry.py` — direct mechanism for D-02/D-03 (see
  above). Follow the exact `(file, line, category, reason)` tuple shape already established.

### Established Patterns
- `±2` line-number tolerance in `_allowed()` (`tests/test_skip_registry.py:32,41`) absorbs minor
  edits without re-registering — reuse this tolerance for the 149 entries rather than inventing a
  stricter/looser scheme.

### Integration Points
- Any new quarantine marker added during this phase must land inside `ALLOWED_SKIPS` in the same
  commit/plan that adds the marker, or the meta-gate (`test_no_unregistered_skips`) will fail on it
  — this is enforced today, not aspirational.

### Live full-suite run performed during this discussion (2026-08-11, ground truth — do not re-derive, re-verify if stale)
- `pytest -q` (no `-m` filter, full suite): **108 failed, 3064 passed, 8 skipped, 60 deselected,
  125 warnings, 264.58s**. Slightly above the ~102 figure cited in HORIZON.md/ROADMAP.md (drift
  since that estimate was made — expected, not a discrepancy to chase).
- Largest failure clusters by file: `test_sensor_cmd.py` (9), `test_auto_merge_trigger.py` (8),
  `test_openapi_scanner.py` (7), `test_ticketing_servicenow.py` (6), `test_jwt_scanner.py` (6),
  `test_reports_writer.py` (5), `test_notify_webhook.py` (5), `test_dashboard_scan_history.py` (5),
  `test_version.py` (4), `test_report_injection_hardening.py` (4) — remaining ~20 files have 1-3
  failures each.
- Several failures are visibly **environment-dependent in this sandbox**, not necessarily real
  regressions — e.g. `test_ticketing_servicenow.py` fails with `ValueError: SSRF blocked
  (dns_failure) for ServiceNow URL` (DNS resolution blocked in this environment), and
  `test_vault_connector.py::test_pki_sha1_signed_ca_high_severity` fails with `RuntimeError: openssl
  SHA1 cert failed`. Whether "environment-dependent" becomes its own disposition sub-flavor of
  "quarantined" (vs. a distinct category) is left to planning/research to work out against the full
  108-item list — this discussion did not enumerate all 108 individually.
- `tests/test_skip_registry.py::test_no_unregistered_skips` (the meta-gate itself) is among the 108
  failures — see D-04. Full list of its currently-unregistered violations was captured in the raw
  run log; re-run `pytest tests/test_skip_registry.py -q` at planning/execution time to get the
  current authoritative list (this discussion's snapshot may drift as other work lands).

</code_context>

<specifics>
## Specific Ideas

- The ledger's "total failure count matches the actual full-suite run" (Success Criterion 2) means
  the ledger must be a per-test disposition table (test ID → disposition → reason), not a per-file
  or per-category summary — a file-level or category-level rollup could not be checked for an exact
  count match against 108 individual pytest node IDs.

</specifics>

<deferred>
## Deferred Ideas

- Actually fixing any of the 108 failures — explicitly Phase 150's job (SUITE-02/SUITE-03), not
  this phase's, per D-01.
- Adding a CI gate that runs the full suite — Phase 150 (SUITE-03).
- Distinguishing "environment-dependent" as a formal disposition sub-category with its own registry
  category (vs. folding it into the general `pre_existing_triage_149` quarantine category) — noted
  as an open question for planning/research to resolve once the full 108-item list is enumerated;
  not decided in this discussion since it requires per-test review this session didn't do.

### Reviewed Todos (not folded)
None — no matching todos surfaced (`todo.match-phase 149` returned zero matches).

</deferred>

---

*Phase: 149-Test Suite Triage*
*Context gathered: 2026-08-11*
