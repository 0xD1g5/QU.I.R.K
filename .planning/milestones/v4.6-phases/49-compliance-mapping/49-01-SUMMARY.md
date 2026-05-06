---
phase: 49-compliance-mapping
plan: 01
subsystem: testing
tags: [pytest, ast, compliance, red-state, tdd]

requires:
  - phase: 48-rich-finding-context
    provides: pytest-as-CI-gate precedent, _build_finding signature, TITLE_PREFIX_ALIASES idiom
provides:
  - Five RED-state pytest gates for Phase 49 (schema, freshness, title-join, report-section, CLI)
  - tests/fixtures/chaos_lab_findings.py — AST aggregator returning 31 emitted finding titles
  - tests.fixtures namespace package marker
affects: [49-02-compliance-module, 49-03-cli, 49-04-report-section, 49-05-docs-sync]

tech-stack:
  added: []
  patterns:
    - "Lazy-import in fixture _normalize() so tests collect before quirk.compliance exists"
    - "ast.JoinedStr literal-only template join for f-string title prefix extraction"
    - "subprocess.run with timeout=30 (T-49-03 mitigation) for CLI smoke tests"

key-files:
  created:
    - tests/fixtures/__init__.py
    - tests/fixtures/chaos_lab_findings.py
    - tests/test_compliance_schema.py
    - tests/test_compliance_freshness.py
    - tests/test_compliance_title_join.py
    - tests/test_compliance_report_section.py
    - tests/test_compliance_cli.py
  modified: []

key-decisions:
  - "AST extraction over runtime engine sweep — CI must not depend on Docker chaos lab"
  - "Lazy TITLE_PREFIX_ALIASES import in fixture allows test collection before quirk.compliance exists (RED state)"
  - "Aggregator lower-bound assertion at 24 (fixed-string title floor) guards against AST-walker regression to empty set"

patterns-established:
  - "RED-state Wave 0: land all gate tests before any production code so subsequent waves land GREEN against a real failing baseline"
  - "Paired *_resolve / *_path_exists test for every gate file (catches accidental rename)"

requirements-completed: [COMPLY-01, COMPLY-02, COMPLY-03, COMPLY-04, COMPLY-05, COMPLY-06, COMPLY-07, COMPLY-08]

duration: 6min
completed: 2026-05-05
---

# Phase 49 Plan 01: Wave 0 RED-State Test Scaffold Summary

**Five failing pytest gates plus an AST-driven 31-title aggregator fixture, establishing the RED baseline for Phase 49 compliance mapping before any production code lands.**

## Performance

- **Duration:** ~6 min
- **Completed:** 2026-05-05T21:36:40Z
- **Tasks:** 2
- **Files created:** 7
- **Files modified:** 0

## Accomplishments
- `tests/fixtures/chaos_lab_findings.py` ships an AST walker that extracts every `title=` literal passed to `_build_finding(...)` in `quirk/engine/risk_engine.py` — returns **31** normalized titles (well above the 24 floor) on a fresh run.
- Three RED-state gate tests for the COMPLIANCE_MAP data invariants: required-key schema (COMPLY-06), ISO date + https://, and staleness threshold (COMPLY-07).
- Title-join gate (COMPLY-02/03/04): every emitted finding title must be in COMPLIANCE_MAP or UNMAPPED_TITLES.
- Report-render smoke (COMPLY-05) and CLI subprocess smoke (COMPLY-08) with `timeout=30` (T-49-03 mitigation).
- Wave 0 RED baseline confirmed: 9 fail (production missing), 3 pass (file/path resolution + nonempty aggregator) — exactly the expected state.

## Task Commits

1. **Task 1: chaos-lab fixture aggregator + schema/freshness/title-join tests** — `2e0abe3` (test)
2. **Task 2: report-render + CLI smoke tests** — `847896f` (test)

## Files Created/Modified
- `tests/fixtures/__init__.py` — empty marker so `tests.fixtures` is importable
- `tests/fixtures/chaos_lab_findings.py` — AST aggregator with lazy TITLE_PREFIX_ALIASES normalization
- `tests/test_compliance_schema.py` — 4 tests: imports, required keys, ISO date, https://
- `tests/test_compliance_freshness.py` — staleness threshold gate
- `tests/test_compliance_title_join.py` — nonempty + orphan title check
- `tests/test_compliance_report_section.py` — render_html_report() substring smoke (Compliance Summary, PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3, "Findings without compliance mapping")
- `tests/test_compliance_cli.py` — subprocess smoke for `quirk compliance status` (text + JSON)

## Decisions Made
- AST extraction over runtime engine sweep — CI must not depend on Docker chaos lab; `_build_finding` Call-node walking with `ast.JoinedStr` literal-only template join handles f-string titles deterministically.
- Lazy `TITLE_PREFIX_ALIASES` import in `_normalize()` — keeps the fixture collectable before `quirk.compliance` exists; the import error surfaces only at test-body time, which is the expected RED signal.
- `len(collect_emitted_titles()) >= 24` lower-bound assertion — guards against a future AST-walker regression silently returning an empty set.
- `render_html_report` is positional-arg-only; smoke test passes the full 7-arg signature with minimal `types.SimpleNamespace` cfg + empty endpoints/roadmap.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## TDD Gate Compliance

Both task commits are `test(...)` commits, establishing the RED gate. GREEN commits (`feat(...)`) for `quirk/compliance/` will land in Plans 49-02..04. This is a pure RED-scaffolding plan; no GREEN expected at this gate.

## Verification Snapshot

```
$ python -m pytest tests/test_compliance_*.py
9 failed, 3 passed in 1.18s

Passing (intentional, file-resolution + nonempty aggregator):
  - test_compliance_title_join.py::test_aggregator_returns_nonempty
  - test_compliance_report_section.py::test_template_path_exists
  - test_compliance_cli.py::test_run_scan_path_exists

Failing (intentional RED baseline):
  - test_compliance_schema.py:: 4 tests (ModuleNotFoundError: quirk.compliance)
  - test_compliance_freshness.py::test_no_entry_older_than_threshold (same)
  - test_compliance_title_join.py::test_every_emitted_title_is_mapped_or_allowlisted (same)
  - test_compliance_report_section.py::test_html_contains_compliance_summary (template missing block)
  - test_compliance_cli.py::test_status_text_smoke (unrecognized arg 'compliance')
  - test_compliance_cli.py::test_status_json_smoke (unrecognized arg 'compliance')
```

## Next Phase Readiness

- Plan 49-02 (compliance module) lands `quirk/compliance/__init__.py` with `COMPLIANCE_MAP`, `UNMAPPED_TITLES`, `TITLE_PREFIX_ALIASES`, `STALENESS_THRESHOLD_DAYS`, and `status_report` — turns 6 of the 9 failures GREEN.
- Plan 49-03 (CLI) wires `compliance status` subcommand — turns the 2 CLI smokes GREEN.
- Plan 49-04 (report section) inserts the Compliance Summary block — turns the 1 report smoke GREEN.

---
*Phase: 49-compliance-mapping*
*Plan: 01*
*Completed: 2026-05-05*

## Self-Check: PASSED

All 7 created files verified on disk. Both task commits (2e0abe3, 847896f) verified in git log.
