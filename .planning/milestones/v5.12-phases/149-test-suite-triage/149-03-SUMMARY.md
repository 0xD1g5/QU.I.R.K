---
phase: 149-test-suite-triage
plan: 03
subsystem: test-infra
tags: [triage-ledger, skip-registry, isolation-verification, playwright, pip-dry-run]
requires:
  - skip_registry_gate_green
  - pre_existing_triage_149_category
  - test-triage-149_ledger_skeleton
provides:
  - cluster_2_playwright_pollution_quarantined
  - cluster_6_pip_dryrun_flakiness_quarantined
affects:
  - tests/test_reports_writer.py
  - tests/test_report_injection_hardening.py
  - tests/test_pdf_metadata_constants.py
  - tests/test_writer.py
  - tests/test_pdf_export.py
  - tests/test_install_all_excludes_impacket.py
  - tests/test_install_all_excludes_pysnmp.py
  - tests/test_install_all_excludes_schemathesis.py
  - tests/test_install_all_includes_notify.py
  - tests/test_install_all_includes_tickets.py
  - tests/test_snmp_scanner_contract.py
  - tests/skip_registry.py
  - docs/test-triage-149.md
tech-stack:
  added: []
  patterns:
    - "skip(reason='TRIAGE-149: flaky ...') + pre_existing_triage_149 registry entry + ledger row, for full-suite-only failures that pass standalone"
key-files:
  created: []
  modified:
    - tests/test_reports_writer.py
    - tests/test_report_injection_hardening.py
    - tests/test_pdf_metadata_constants.py
    - tests/test_writer.py
    - tests/test_pdf_export.py
    - tests/test_install_all_excludes_impacket.py
    - tests/test_install_all_excludes_pysnmp.py
    - tests/test_install_all_excludes_schemathesis.py
    - tests/test_install_all_includes_notify.py
    - tests/test_install_all_includes_tickets.py
    - tests/test_snmp_scanner_contract.py
    - tests/skip_registry.py
    - docs/test-triage-149.md
decisions:
  - "All 20 Cluster 2/6 tests dispositioned quarantined-skip (not xfail), per D-03: running them under full-suite pollution is not useful signal and they are expected to run cleanly once Phase 150 fixes the shared fixture/lifecycle issue"
  - "All 20 tests re-verified individually in isolation before quarantine per Pitfall 2 — no blanket disposition applied without a per-test standalone pass"
metrics:
  duration: 25min
  completed: 2026-08-12
---

# Phase 149 Plan 03: Cluster 2 (Playwright pollution) + Cluster 6 (pip dry-run flakiness) Quarantine Summary

Isolation-verified and quarantined all 20 Cluster 2/6 failures — Playwright's
`AttributeError: PlaywrightContextManager` cross-test-pollution symptom (14 tests,
5 files) and pip `--dry-run` subprocess-contention flakiness under full-suite load
(6 tests, 6 files) — with `@pytest.mark.skip` markers, matching `pre_existing_triage_149`
registry entries, and 20 ledger rows citing the standalone-pass evidence.

## What Was Built

### Task 1: Cluster 2 — Playwright cross-test pollution (14 tests, 5 files)

Re-ran RESEARCH.md's isolation check plus 3 additional standalone runs before
touching any code: `pytest tests/test_reports_writer.py tests/test_writer.py -q -m ""`
(7 passed), `pytest tests/test_report_injection_hardening.py -q -m ""` (4 passed),
`pytest tests/test_pdf_metadata_constants.py -q -m ""` (3 passed), and
`pytest tests/test_pdf_export.py -q -m ""` (2 passed) — all green standalone,
confirming the full-suite-only `AttributeError: PlaywrightContextManager` failures
are a shared-singleton test-isolation artifact, not per-test regressions. Added
`@pytest.mark.skip(reason="TRIAGE-149: flaky (Playwright PlaywrightContextManager
singleton torn down by earlier full-suite test, order-dependent — passes
standalone); see docs/test-triage-149.md#<slug>")` above each of the 14 failing
tests across `test_reports_writer.py` (5), `test_report_injection_hardening.py`
(4), `test_pdf_metadata_constants.py` (3), `test_writer.py` (1), and
`test_pdf_export.py` (1). Added `import pytest` to `test_writer.py` (previously
had no pytest import). Added 14 matching `ALLOWED_SKIPS` entries under a new
`# Phase 149 Plan 03: Cluster 2` banner in `tests/skip_registry.py`, category
`pre_existing_triage_149`. Result: `pytest <5 files> -q -m ""` → 2 passed, 14
skipped, 0 failed.

### Task 2: Cluster 6 — pip dry-run extras-install flakiness (6 tests, 6 files)

Re-verified each of the 6 tests individually in isolation rather than assuming a
shared cause, per Pitfall 2's explicit warning:
`test_install_all_excludes_impacket.py` (1 passed, 7.75s),
`test_install_all_excludes_pysnmp.py` (1 passed, 5.95s),
`test_install_all_excludes_schemathesis.py` (2 passed, 5.35s — the file's second
test `test_install_api_includes_schemathesis` is out of Cluster 6 scope and
unaffected), `test_install_all_includes_notify.py` (1 passed, 5.11s),
`test_install_all_includes_tickets.py` (1 passed, 7.90s), and
`test_snmp_scanner_contract.py::test_install_all_excludes_pysnmp` (1 passed,
8.20s). All 6 passed cleanly standalone — no genuine failure surfaced, so no
test required a distinct non-flaky disposition. Added the matching
`@pytest.mark.skip(reason="TRIAGE-149: flaky (pip --dry-run subprocess
contention under full-suite load, passes standalone); see
docs/test-triage-149.md#<slug>")` decorator above each of the 6 tests and 6
matching `ALLOWED_SKIPS` entries.

While adding the Cluster 2/6 decorators shifted line numbers for 3 pre-existing
`pre_existing_triage_149`-adjacent `optional_extra` registry rows that live
further down in the same edited files (`test_report_injection_hardening.py`'s
`pytest.importorskip` guards moved 240→244, 241→245, 254→258; and
`test_snmp_scanner_contract.py`'s three `pytest.skip("pysnmp not installed")`
guards moved 598→599, 631→632, 673→674), both caught and corrected in this same
task before the meta-gate was re-run. Result:
`pytest <5 excludes/includes files> -q -m ""` → 1 passed, 5 skipped, 0 failed.

### Task 3: Cluster 2 + Cluster 6 ledger rows + meta-gate verification

Added 14 rows under `## Cluster 2: Playwright cross-test pollution` in
`docs/test-triage-149.md`, each `Disposition = quarantined-skip`,
`Sub-reason = flaky (test-isolation / shared Playwright singleton)`, citing the
`AttributeError: PlaywrightContextManager` symptom and the exact standalone-pass
isolation run that confirmed it, plus the corrected `tests/skip_registry.py:<line>`
citation. Added 6 rows under `## Cluster 6: pip dry-run extras-install
flakiness`, each `Disposition = quarantined-skip`,
`Sub-reason = flaky (pip --dry-run subprocess contention under full-suite
load)`, citing the individual standalone-pass timing evidence. Ran
`pytest tests/test_skip_registry.py -q -m ""` — 1 passed, confirming the
meta-gate stayed green after both the initial 20 new decorators and the
3 line-number registry corrections.

## Deviations from Plan

None — plan executed exactly as written. Two self-caught line-number
corrections during Task 2 (registry entries for pre-existing
`optional_extra` skips shifted by the new decorators added earlier in the same
files) were fixed in the same task before commit, not a post-hoc fix — this
mirrors the same class of arithmetic slip Plan 02 called out and caught in its
own Task 3.

## Verification

- `pytest tests/test_reports_writer.py tests/test_report_injection_hardening.py tests/test_pdf_metadata_constants.py tests/test_writer.py tests/test_pdf_export.py -q -m ""` → 2 passed, 14 skipped
- `pytest tests/test_install_all_excludes_impacket.py tests/test_install_all_excludes_pysnmp.py tests/test_install_all_excludes_schemathesis.py tests/test_install_all_includes_notify.py tests/test_install_all_includes_tickets.py -q -m ""` → 1 passed, 5 skipped
- `pytest tests/test_skip_registry.py -q -m ""` → 1 passed
- `docs/test-triage-149.md` Cluster 2 table has 14 rows, Cluster 6 table has 6 rows (confirmed via `awk`+`grep -c`)
- Combined scope run (all 12 files + meta-gate) → 4 passed, 20 skipped, 0 failed

## Self-Check

- `tests/test_reports_writer.py` modified: FOUND
- `tests/test_report_injection_hardening.py` modified: FOUND
- `tests/test_pdf_metadata_constants.py` modified: FOUND
- `tests/test_writer.py` modified: FOUND
- `tests/test_pdf_export.py` modified: FOUND
- `tests/test_install_all_excludes_impacket.py` modified: FOUND
- `tests/test_install_all_excludes_pysnmp.py` modified: FOUND
- `tests/test_install_all_excludes_schemathesis.py` modified: FOUND
- `tests/test_install_all_includes_notify.py` modified: FOUND
- `tests/test_install_all_includes_tickets.py` modified: FOUND
- `tests/test_snmp_scanner_contract.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- Commit `16621b7` (Task 1): FOUND
- Commit `6145d2d` (Task 2): FOUND
- Commit `c74f806` (Task 3): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- Full Cluster 2/6 scope: CONFIRMED (4 passed, 20 skipped, 0 failed)

## Self-Check: PASSED
