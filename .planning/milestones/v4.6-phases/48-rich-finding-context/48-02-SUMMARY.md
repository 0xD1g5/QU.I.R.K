---
phase: 48-rich-finding-context
plan: 2
subsystem: reports + dashboard
tags: [phase-48, reports, dashboard, html, markdown, json-export, FIPS-203, NIST-IR-8547]
requires:
  - phase: 48
    plan: 1
    provides: "_build_finding chokepoint emitting non-empty description on every finding dict"
provides:
  - "HTML report All Findings table renders Description column (before Recommendation)"
  - "Technical Markdown report Findings table renders Description column (between Title and Recommendation)"
  - "DO NOT UNIFY guardrail comment on FindingItem documenting recommendation/remediation asymmetry"
  - "End-to-end test asserting JSON export carries description for every finding"
  - "End-to-end test asserting HTML report contains <th>Description</th> in Top + All Findings"
affects:
  - "Plan 48-03 (CI gate + docs): consumer wiring is now complete; CI gate may proceed against stable surface"
tech-stack:
  added: []
  patterns:
    - "Module-level intelligence-mock pattern (mirrors tests/test_cbom_integration.py) for write_reports E2E tests"
    - "Inline guardrail comment chokepoint preserving intentional schema-field asymmetry"
key-files:
  created:
    - tests/test_reports_writer.py
  modified:
    - quirk/reports/templates/report.html.j2
    - quirk/reports/technical.py
    - quirk/dashboard/api/schemas.py
decisions:
  - "[48-02] HTML and Markdown All Findings tables truncate Description and Recommendation at 200 chars (with ellipsis) — consistent visual budget for both columns; matches plan spec"
  - "[48-02] Guardrail comment placed immediately above FindingItem class declaration — visible to anyone reading or editing the DTO before any rename refactor"
  - "[48-02] No code change in quirk/reports/writer.py — _json_dump passes findings list through unprojected; description flows automatically from Plan 48-01's _build_finding"
  - "[48-02] dashboard routes/scan.py _derive_findings audit: all 7 FindingItem(...) construction sites already populate non-None description= (verified by code reading; no patch needed)"
metrics:
  duration: ~10 minutes
  completed: 2026-05-04
  tasks: 2
  files: 4
---

# Phase 48 Plan 02: Rich Finding Context — Consumer Wiring Summary

One-liner: Wired the Plan 48-01 `description` field through every consumer — HTML All Findings table, technical Markdown report, dashboard DTO guardrail, JSON export — and added an end-to-end test asserting the field reaches `findings-{stamp}.json` and the rendered HTML.

## What Was Built

### HTML All Findings table (`quirk/reports/templates/report.html.j2:223-243`)

Inserted a `<th>Description</th>` cell **before** `<th>Recommendation</th>` in
the All Findings table header (line 226), and a corresponding `<td>` cell
sourced from `f.get('description','')` truncated at 200 characters with
ellipsis (line 234). Recommendation cell width was extended from 160 → 200
chars to keep both columns visually balanced.

The Top Findings table (lines 172-187) was already populating `description`
from a prior phase — unchanged.

After the edit:
- `grep -c '<th>Description</th>' quirk/reports/templates/report.html.j2` → **2**
  (Top Findings + All Findings)
- `grep -c "f.get('description','')\[:200\]" quirk/reports/templates/report.html.j2` → **1**

### Technical Markdown report (`quirk/reports/technical.py:88-97`)

Header row updated from
```
| Severity | Host | Port | Title | Recommendation |
```
to
```
| Severity | Host | Port | Title | Description | Recommendation |
```

Row-format string now reads `description` from each finding dict and
emits it between Title and Recommendation. Per-row `desc = f.get("description", "")`
preserves the empty-string fallback used by every other field accessor in the
file (consistent style).

### Dashboard DTO guardrail (`quirk/dashboard/api/schemas.py:42-48`)

Added a 5-line `# DO NOT UNIFY` block immediately above the `FindingItem`
class declaration explaining that:

- the dashboard DTO uses `remediation`,
- the risk-engine `_build_finding` dicts use `recommendation`,
- the asymmetry is intentional and pre-existing,
- routes/scan.py's `_derive_findings` constructs FindingItem from
  `CryptoEndpoint` state, not from risk-engine dicts,
- the canonical reference is Phase 48 PATTERNS §3.

`grep -c 'DO NOT UNIFY' quirk/dashboard/api/schemas.py` → **1**.

### Audit of `routes/scan.py::_derive_findings`

Walked every `FindingItem(...)` construction site inside `_derive_findings`
(`quirk/dashboard/api/routes/scan.py:65-181`):

| Line | Branch | description= populated? |
|---|---|---|
| 65-76 | Unencrypted HTTP service | YES — "Service is accessible over plaintext HTTP without TLS." |
| 80-91 | Legacy TLS version | YES — f-string with version |
| 95-106 | Weak cipher suites enabled | YES — RC4/DES/NULL/EXPORT explanation |
| 115-126 | Certificate expired | YES — days-ago f-string |
| 128-139 | Certificate expiring soon | YES — within-30-days |
| 148-159 | Weak RSA key | YES — bits f-string |
| 168-179 | Quantum-vulnerable algorithm | YES — algorithm + classification |

**Outcome:** every existing branch already passes a non-None
`description=` argument. No code patch required in `routes/scan.py` for
Plan 48-02. The guardrail comment in `schemas.py` is the only schema-side
change.

### End-to-end test file: `tests/test_reports_writer.py`

Three new tests using the same intelligence-mock fixture pattern as
`tests/test_cbom_integration.py`:

| Test | Assertion |
|---|---|
| `test_json_export_preserves_description` | `findings-*.json` exists; every entry contains a non-empty `description` |
| `test_json_export_preserves_deprecation_phrase` | The RSA-titled finding's `recommendation` retains the literal `Per NIST IR 8547` and `FIPS 203` substrings through JSON serialization |
| `test_html_report_has_description_column` | The rendered `report-*.html` contains `<th>Description</th>` at least twice (Top Findings + All Findings) |

All three pass: `pytest tests/test_reports_writer.py -x -v` → **3 passed in 0.14s**.

The fixture stubs `build_evidence_summary`, `compute_readiness_score`,
`compute_confidence`, `build_phased_roadmap`, and `categorize_waves` to
isolate the writer-side serialization path from intelligence pipeline
changes — this matches the pattern already established in
`tests/test_cbom_integration.py`.

## Files Modified

- `quirk/reports/templates/report.html.j2` — added Description column to All Findings table
- `quirk/reports/technical.py` — added Description column between Title and Recommendation
- `quirk/dashboard/api/schemas.py` — added DO NOT UNIFY guardrail comment above FindingItem
- `tests/test_reports_writer.py` — **new** file with 3 E2E tests

## Commits

| Task | Commit | Subject |
|---|---|---|
| 1 | `7ebb4b6` | `feat(48-02): add Description column to HTML All Findings + tech Markdown report` |
| 2 | `f3f1c83` | `feat(48-02): wire description to dashboard DTO + JSON export with E2E test` |

## Deviations from Plan

None. Two minor in-scope notes:

1. **Recommendation column truncation widened (160 → 200) in All Findings**
   to keep visual parity with the new Description column (also 200). The
   plan specified 200/200 for both columns; the previous 160-char Recommendation
   cap predated this plan and was tightened to match. No regression — longer
   recommendations now render slightly more text.

2. **routes/scan.py audit yielded zero patches** because every construction
   site was already correct. The plan acknowledged this as the likely
   outcome (PATTERNS §3 cited line numbers already populating description).
   Outcome documented in the audit table above.

## Quick-verify Commands

```bash
# HTML + Markdown columns
grep -c '<th>Description</th>' quirk/reports/templates/report.html.j2     # 2
grep -c 'Description | Recommendation' quirk/reports/technical.py         # 1

# Guardrail comment
grep -c 'DO NOT UNIFY' quirk/dashboard/api/schemas.py                     # 1

# Tests
python -m pytest tests/test_reports_writer.py -v                          # 3 passed
python -m pytest tests/test_risk_engine.py -x                             # 36 passed (Plan 48-01 invariants intact)
python -m compileall quirk/reports/technical.py quirk/dashboard/api/schemas.py quirk/dashboard/api/routes/scan.py
```

## Deferred Issues

None introduced by this plan. The 19 pre-existing CBOM-schema test
failures from Plan 48-01's deferred-items list remain unchanged and out
of scope for Wave 2.

## Self-Check: PASSED

- `quirk/reports/templates/report.html.j2` — FOUND, contains `<th>Description</th>` x2
- `quirk/reports/technical.py` — FOUND, contains `Description | Recommendation`
- `quirk/dashboard/api/schemas.py` — FOUND, contains `DO NOT UNIFY`
- `tests/test_reports_writer.py` — FOUND, 3 tests pass
- Commit `7ebb4b6` — FOUND
- Commit `f3f1c83` — FOUND
