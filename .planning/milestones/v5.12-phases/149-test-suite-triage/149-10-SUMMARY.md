---
phase: 149-test-suite-triage
plan: 10
subsystem: testing
tags: [docs-presence, safe-filter-audit, scan-error-gate, sigsegv, skip-registry, cluster-9-final]

requires:
  - phase: 149-test-suite-triage plan 09
    provides: cluster_9_group_d1_cli_compliance_posture_failures_dispositioned

provides:
  - cluster_9_group_d2_docs_security_gate_windows_smoke_failures_dispositioned
  - cluster_9_fully_closed
  - all_116_baseline_test_dispositions_complete

affects:
  - tests/test_phase135_docs_presence.py
  - tests/test_phase136_docs_presence.py
  - tests/test_safe_filter_audit.py
  - tests/test_scan_error_gate.py
  - tests/skip_registry.py
  - docs/test-triage-149.md

tech-stack:
  added: []
  patterns:
    - "Security-gate meta-tests (test_safe_filter_audit.py, test_scan_error_gate.py) can fail
       for gate-logic reasons rather than real content regressions: a Jinja-only `| safe`
       scanner cannot see Python-side pre-escaping (_html.escape()), and an AST classifier
       built from a fixed enumeration of SAFE shapes (Constant/Call/Attribute/JoinedStr/Name)
       silently treats any unlisted shape (e.g. ast.IfExp/ternary) as a VIOLATION even when
       both branches are individually safe. Both require reading the exact flagged
       file:line, tracing the value back to its Python source, and confirming safety
       independently of the gate's own pattern list before dispositioning as SECURITY vs.
       stale-detection-logic."
    - "A second, independent SIGSEGV (test_sensor_windows_smoke.py, sensor CLI dispatch) can
       coexist with Plan 08's QRAMM SIGSEGV pair without sharing a root cause — different
       subsystem, different subprocess construction (inline script vs. run_scan.py CLI),
       and running both files together in one process produces zero crashes, ruling out a
       compounding/shared native-library trigger in this sandbox."

key-files:
  created: []
  modified:
    - tests/test_phase135_docs_presence.py
    - tests/test_phase136_docs_presence.py
    - tests/test_safe_filter_audit.py
    - tests/test_scan_error_gate.py
    - tests/skip_registry.py
    - docs/test-triage-149.md

key-decisions:
  - "test_safe_filter_audit.py's 2 flagged `| safe` usages (report.html.j2:389/508) were
     individually traced to their Python source and confirmed genuinely safe, not real
     unsanitized-usage findings: narrative_lead is sourced from a small hardcoded static-
     prose dict (_NARRATIVE_LEADS) keyed by a fixed score-band enum (never scanner/user
     input); hardware_section is pre-HTML-escaped in Python by render_hardware_section()
     (_html.escape() on every dynamic field) before being marked safe, so the sanitization
     happens outside the Jinja filter chain this gate inspects. Neither is flagged SECURITY:
     per the plan's must_haves — this is an explicit gate-logic gap (Jinja-only detection
     can't see static-dict sourcing or Python-side pre-escaping), flagged for Phase 150 to
     widen the gate's recognized SAFE shapes, not a Phase 150 security fix."
  - "test_scan_error_gate.py's 1 flagged write site (kerberos_scanner.py:312) is a ternary
     (safe_str(tcp_error) if tcp_error is not None else None) whose two branches are both
     individually SAFE shapes, but _classify_rhs() has no case for ast.IfExp at all and so
     classifies the whole expression as a VIOLATION. Confirmed not a real safe_str bypass —
     no credential- or scanner-controlled text reaches scan_error unsanitized. Not flagged
     SECURITY:; flagged for Phase 150 to extend _classify_rhs() to recurse into ast.IfExp
     branches."
  - "test_sensor_windows_smoke.py's SIGSEGV (exit=-11 on KeyboardInterrupt in a subprocess-
     spawned sensor CLI script) does not reproduce in this sandbox across isolated x3 runs,
     nor when run combined with Plan 08's QRAMM SIGSEGV pair in the same pytest process (18
     tests, 0 crashes). Explicitly determined to NOT share Plan 08's root cause (different
     subsystem: sensor CLI dispatch vs. QRAMM staleness CLI; different subprocess
     construction: inline -c script vs. run_scan.py subprocess) rather than assumed related.
     Left unmarked per the Plan 06/08/09 not-reproducible precedent; flagged as a second,
     independent HIGH-PRIORITY Phase 150 SIGSEGV re-verification item."
  - "test_phase135_docs_presence.py and test_phase136_docs_presence.py's failures are both
     routine drift, not content regressions: README.md has advanced 3 version bumps past the
     v5.8.0 string the test still checks for (all other Phase 135 content intact), and
     operators-guide.md §9 legitimately gained a Phase 139 SNMPv3 subsection the Phase 136
     leak-detector (written to guard against Phase 137 scope creep) now flags as a false
     positive against genuinely-shipped, correctly-scoped functionality."

requirements-completed: [SUITE-01]

duration: 40min
completed: 2026-08-12
---

# Phase 149 Plan 10: Cluster 9 Group D2 — Docs-Presence/Security-Gate/Windows-Smoke Failures Summary

Individually investigated the final 5 Cluster 9 failures — 2 docs-presence version/content
drift tests, 2 security-gate meta-tests (Jinja `| safe` audit + `scan_error` safe_str
bypass audit), and 1 second, independent SIGSEGV in the Windows sensor smoke suite.
Investigation converged on 5 distinct sub-reasons: 1 stale version-string pin, 1 stale
leak-detector flagging a legitimate later addition, 2 gate-logic gaps in the AST/Jinja
security scanners (both individually confirmed safe — no real unsanitized-usage or
safe_str-bypass finding, neither flagged `SECURITY:`), and 1 SIGSEGV confirmed not
reproducible and explicitly not sharing Plan 08's QRAMM crash root cause. This closes
Cluster 9 and completes all 116-baseline test dispositions across Phase 149 Plans 01-10.

## Performance

- **Duration:** 40 min
- **Started:** 2026-08-12T03:47:00Z
- **Completed:** 2026-08-12T04:27:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- **Task 1 (2 of 3 tests quarantined; SIGSEGV left unmarked):**
  - `test_phase135_docs_presence.py::test_required_sections_present`: confirmed
    README.md's title/What's New content has genuinely advanced past `v5.8.0` (now
    `v5.11.0`, 3 version bumps later) — every other Phase 135 required substring intact.
    Stale version pin, not a regression.
  - `test_phase136_docs_presence.py::test_section9_deferred_topics_absent`: confirmed via
    `grep` that `snmpv3` is genuinely present in operators-guide.md §9, traced to Phase
    139's legitimate `§9.1.1 SNMPv3 Auth+Priv Scanning` subsection — a properly-scoped
    later addition documenting real shipped functionality, not a leak of Phase 137's
    deferred admin-guide content.
  - `test_sensor_windows_smoke.py::TestCleanShutdownOnKeyboardInterrupt::test_keyboard_interrupt_in_run_sensor_exits_130`:
    identified the exact code path (patched `_run_local_scan` raises `KeyboardInterrupt`
    inside `run_sensor`'s dispatch), ran isolated 3x (12/12 pass each run) and combined
    with Plan 08's QRAMM SIGSEGV pair in one process (18/18 pass, 0 crashes) — confirmed
    NOT reproducible and explicitly NOT assumed to share Plan 08's root cause (different
    subsystem/subprocess construction). Left unmarked per precedent.
  - Registered 2 new `pre_existing_triage_149` entries in `tests/skip_registry.py`.
- **Task 2 (2 security-gate meta-tests investigated, both real-vs-stale determined
  explicitly, neither SECURITY):**
  - `test_safe_filter_audit.py::test_safe_filter_paired_with_sanitize`: identified the
    exact 2 flagged template lines (`report.html.j2:389`, `:508`), traced `narrative_lead`
    to a hardcoded static-prose dict lookup (`_NARRATIVE_LEADS`) and `hardware_section` to
    a Python function (`render_hardware_section()`) that HTML-escapes every dynamic field
    before returning — both confirmed genuinely safe. Gate-logic gap (Jinja-only
    detection), not a real finding.
  - `test_scan_error_gate.py::test_scan_error_writes_use_safe_str`: identified the exact
    flagged write site (`kerberos_scanner.py:312`), confirmed it's a ternary whose two
    branches are both individually SAFE shapes (`safe_str(tcp_error)` / `None`) that
    `_classify_rhs()` doesn't recognize as a composite (`ast.IfExp` has no case). Gate-logic
    gap, not a real safe_str bypass.
  - Registered 2 new `pre_existing_triage_149` entries in `tests/skip_registry.py`.
- **Task 3 (ledger + meta-gate):** Wrote all 5 Cluster 9 Group D2 rows to
  `docs/test-triage-149.md`, explicitly stating real-vs-stale for both security-gate tests
  in the row text (neither `SECURITY:`-prefixed since neither confirmed a real finding).
  Confirmed `pytest tests/test_skip_registry.py -q -m ""` stays green (1 passed) and the
  full 5-file suite reports 44 passed, 4 xfailed, 0 failed. This closes Cluster 9 and
  completes all 116-baseline test dispositions across Plans 01-10.

## Task Commits

1. **Task 1: Investigate + quarantine 2 docs-presence tests, leave SIGSEGV unmarked** — `81b0bea`
2. **Task 2: Investigate + quarantine 2 security-gate meta-tests** — `373d37d`
3. **Task 3: Write Cluster 9 Group D2 ledger rows** — `67b71fa`

## Files Created/Modified

- `tests/test_phase135_docs_presence.py` - Added `import pytest` + 1
  `@pytest.mark.xfail(strict=False)` decorator (stale v5.8.0 version pin)
- `tests/test_phase136_docs_presence.py` - Added `import pytest` + 1
  `@pytest.mark.xfail(strict=False)` decorator (stale leak-detector vs. legitimate
  Phase 139 SNMPv3 addition)
- `tests/test_safe_filter_audit.py` - Added 1 `@pytest.mark.xfail(strict=False)`
  decorator (2 confirmed-safe `| safe` usages, gate-logic gap)
- `tests/test_scan_error_gate.py` - Added 1 `@pytest.mark.xfail(strict=False)` decorator
  (confirmed-safe ternary, gate-logic gap)
- `tests/skip_registry.py` - Added 4 `pre_existing_triage_149` entries for Group D2 (no
  entry needed/added for the not-reproducible SIGSEGV test)
- `docs/test-triage-149.md` - Added the Group D2 section (5-row table), closing Cluster 9

## Decisions Made

See `key-decisions` in frontmatter. The two consequential ones for Phase 150 priority:
(1) both security-gate meta-test failures are gate-logic gaps in the classifiers
themselves (Jinja-only `| safe` detection can't see Python-side pre-escaping or
static-dict sourcing; the AST `scan_error` classifier has no `ast.IfExp` case) — Phase 150
should widen the gates' recognized SAFE shapes rather than touch the (already-safe)
flagged code; (2) `test_sensor_windows_smoke.py`'s SIGSEGV is a second, independent
segfault-class risk (distinct from Plan 08's QRAMM pair) that needs its own Phase 150
re-verification pass, not folded into the QRAMM investigation.

## Deviations from Plan

None — plan executed exactly as written. The plan's own framing anticipated the SIGSEGV
test might not share Plan 08's root cause ("do not assume ... without evidence") and this
investigation confirmed that explicitly rather than assuming it.

## Issues Encountered

None blocking. Confirming both security-gate meta-tests as gate-logic gaps (not real
findings) required tracing each flagged value back through its full call chain
(`content_model.py` / `html_renderer.py` for the safe-filter audit; `kerberos_scanner.py`
for the scan-error gate) rather than trusting the gate's own failure message alone —
expected investigative rigor for a security-relevant disposition, not a defect.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Cluster 9 Group D2 is fully closed: 4/5 tests individually investigated and quarantined
with distinct, evidence-backed root causes; 1/5 (the SIGSEGV) investigated and confirmed
not reproducible in this sandbox, explicitly independent of Plan 08's QRAMM SIGSEGV pair.
Ledger updated, `test_skip_registry.py` meta-gate green. **This completes Cluster 9 and
all 116-baseline test dispositions across Phase 149 Plans 01-10.** Phase 150 follow-up
items flagged across this plan and prior plans: (1) widen `test_safe_filter_audit.py`'s
`_has_upstream_sanitize` to recognize static-dict-sourced and Python-pre-escaped safe
shapes; (2) extend `test_scan_error_gate.py`'s `_classify_rhs()` to recurse into
`ast.IfExp` branches; (3) two independent SIGSEGV re-verification items (Plan 08's QRAMM
pair, this plan's sensor smoke test) on a different Python/cryptography/OpenSSL
combination; (4) add an `otics` synthesizer to `tests/_cbom_profiles.py::PROFILE_ENDPOINTS`
(Plan 09 finding). No blockers for Phase 150 (Test Suite Green Baseline + CI Gate).

---
*Phase: 149-test-suite-triage*
*Completed: 2026-08-12*

## Self-Check

- `tests/test_phase135_docs_presence.py` modified: FOUND
- `tests/test_phase136_docs_presence.py` modified: FOUND
- `tests/test_safe_filter_audit.py` modified: FOUND
- `tests/test_scan_error_gate.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- Commit `81b0bea` (Task 1): FOUND
- Commit `373d37d` (Task 2): FOUND
- Commit `67b71fa` (Task 3): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- `pytest tests/test_phase135_docs_presence.py tests/test_phase136_docs_presence.py tests/test_safe_filter_audit.py tests/test_scan_error_gate.py tests/test_sensor_windows_smoke.py -q -m ""`: CONFIRMED (44 passed, 4 xfailed, 0 failed)

## Self-Check: PASSED
