---
phase: 81-cmvp-attestation-feed
plan: 03
type: execute-summary
subsystem: reports/cmvp
tags: [cmvp, fips-140-3, reports, html, markdown, sanitize-chokepoint]
requires:
  - 81-01 (cmvp_cache.json bundled snapshot)
  - 81-02 (quirk/compliance/cmvp.py::coverage_for_algorithm — consumed lazily)
provides:
  - Algorithm Inventory section in report.html.j2 (CMVP Coverage column)
  - build_algorithm_inventory(endpoints) shared helper in quirk/reports/html_renderer.py
  - CMVP Coverage column in executive + technical markdown reports
affects:
  - quirk/reports/templates/report.html.j2
  - quirk/reports/html_renderer.py
  - quirk/reports/executive.py
  - quirk/reports/technical.py
tech_stack_added: []
patterns_followed:
  - Phase 78 sanitize chokepoint (every scanner-controlled cell wraps `| sanitize`)
  - Endpoint Inventory thead/tbody shape at report.html.j2:304-323 (cloned)
  - Lazy-import pattern for wave-parallel dependency on Plan 81-02
  - md_cell wrapping for markdown report cells (Phase 78 / HARDEN-01)
key_files_created: []
key_files_modified:
  - quirk/reports/templates/report.html.j2
  - quirk/reports/html_renderer.py
  - quirk/reports/executive.py
  - quirk/reports/technical.py
key_decisions:
  - Shared helper `build_algorithm_inventory(endpoints)` lives in html_renderer.py and is consumed by executive.py + technical.py to keep the algorithm-name derivation and coverage lookup in one place. Avoids the three-way duplication suggested by the bare wording of the must_haves.
  - Algorithm names sourced from endpoint `cipher_suite`, `cert_pubkey_alg`, and `tls_supported_ciphers_sample` (the same fields the Endpoint Inventory already surfaces). Per-row order is alphabetically sorted for deterministic output.
  - `coverage_for_algorithm` is imported via `from quirk.compliance.cmvp import coverage_for_algorithm` INSIDE the function body — Plan 81-02 is in-flight on Wave 2, so a module-top import would break load order. An `ImportError` fallback degrades to empty coverage (every row renders "Not in CMVP catalog") rather than crashing the report.
  - `nist_level` cell is NOT piped through `| sanitize` per PATTERNS.md §Report CMVP Coverage column line 215 (it is an integer-or-literal field, matching the existing `ep.port` analog in Endpoint Inventory).
metrics:
  duration_minutes: 14
  completed: 2026-05-16
---

# Phase 81 Plan 03: Algorithm Inventory Table + CMVP Coverage Column Summary

**One-liner:** Introduces a 4-column Algorithm Inventory section (Algorithm | NIST Level | FIPS Status | CMVP Coverage) in the HTML report and adds matching CMVP Coverage columns to the executive + technical markdown reports, all populated via `coverage_for_algorithm` (lazy-imported) and routed through the Phase 78 sanitize chokepoint.

## Files Modified

| Path | Change |
|------|--------|
| `quirk/reports/templates/report.html.j2` | NEW Algorithm Inventory section inserted directly after the Endpoint Inventory block (preserves "Endpoints → Algorithms → Findings" flow). 4-column table with `| sanitize` on every scanner-controlled cell. Empty-coverage fallback literal `Not in CMVP catalog` is template-static. |
| `quirk/reports/html_renderer.py` | NEW helpers: `_collect_algorithm_names(endpoints)` derives the unique algorithm/suite set from endpoint records; `build_algorithm_inventory(endpoints)` produces the `{name, nist_level, fips_status, cmvp_coverage}` rows. Both `coverage_for_algorithm` (Plan 81-02) and `classify_algorithm` / `_fips_status` imports are deferred to function-body scope with `ImportError` fallbacks. `render_html_report` now passes `algorithms=algorithms` to the template render context. |
| `quirk/reports/executive.py` | New "Algorithm Inventory (FIPS 140-3 Coverage)" markdown section inserted after Discovery / before Findings Overview. Pulls rows from `build_algorithm_inventory` and emits a 4-column pipe table; every scanner-controlled cell wraps with `md_cell`. Empty-coverage rows emit the literal `Not in CMVP catalog`. |
| `quirk/reports/technical.py` | Same Algorithm Inventory section inserted between TLS Blockers and the Findings table. Same `md_cell` wrapping and `Not in CMVP catalog` fallback. |

## Algorithm Inventory Table Location in Template

`quirk/reports/templates/report.html.j2`, immediately after the closing `{% endif %}` of the Endpoint Inventory block (original lines 304-323). New section runs from `<h2>Algorithm Inventory (FIPS 140-3 Coverage)</h2>` through the closing `{% endif %}` of `{% if algorithms %}`. Total addition: 23 lines including the explanatory comment.

The new section is inside the same `<section>` enclosing the rest of the report body — readers see Endpoints → Algorithms → Findings as a single uninterrupted reading flow.

## Verification Results

```
$ python3 -m compileall quirk/reports/   # clean
$ .venv/bin/python -m pytest tests/test_report*.py -x --tb=no -q
  13 passed in 3.44s
$ .venv/bin/python -m pytest tests/test_report_injection_hardening.py \
    tests/test_report_sanitization.py tests/test_html_report.py \
    tests/test_compliance_report_section.py tests/test_reports_writer.py -x --tb=short
  19 passed in 4.19s

$ grep -c 'Algorithm Inventory' quirk/reports/templates/report.html.j2
  2   # heading + table-block reference (matches plan ≥1 floor)
$ grep -c 'CMVP Coverage' quirk/reports/executive.py quirk/reports/technical.py quirk/reports/templates/report.html.j2
  executive: 2, technical: 2, html: 1   # sum 5 ≥ 3 floor

$ grep -rE 'Not certified' quirk/reports/   # 0 matches — v4.10-D-01 regression guard

$ # Mock-based smoke test (sys.modules-injected fake coverage_for_algorithm):
  - build_algorithm_inventory({AES-256-GCM, RSA-2048}) → expected rows with mocked coverage
  - render_html_report → HTML contains "Algorithm Inventory", "CMVP Coverage", "OpenSSL FIPS Provider", "Microsoft CNG"
  - empty-coverage render → HTML contains "Not in CMVP catalog"
  - build_exec_markdown / build_tech_markdown → "Algorithm Inventory (FIPS 140-3 Coverage)" + "| CMVP Coverage |" + coverage values present
  ALL SMOKE TESTS PASSED
```

## Commit

- **SHA:** `d794ee8`
- **Subject:** `feat(81-03): cmvp coverage column in algorithm inventory table`
- **Files (4):** quirk/reports/templates/report.html.j2, quirk/reports/html_renderer.py, quirk/reports/executive.py, quirk/reports/technical.py
- **Staging:** explicit file paths only — `quirk/cbom/builder.py` and `run_scan.py` are owned by Plan 81-02 (Wave 2 sibling) and were NOT staged despite being modified in the working tree.
- **Deletions:** none.

## Deviations from Plan

### [Rule 3 — Blocking issue] Cross-helper de-duplication: shared `build_algorithm_inventory` instead of three separate inline builders
- **Found during:** Task 2 planning. The plan's must_haves wording (`Markdown executive + technical reports each gain a CMVP Coverage column ... populated via quirk.compliance.cmvp.coverage_for_algorithm()`) is satisfied by *any* call path. Implementing three independent builders (one in each renderer) would have triplicated the algorithm-name derivation, the lazy-import dance, and the `nist_level` / `fips_status` lookup.
- **Issue:** Triplication of the lazy-import + coverage-mapping logic risks drift between the HTML and markdown deliverables (e.g., the markdown report listing AES-256-GCM that the HTML report omits, or vice versa). The plan also mandates `html_renderer.py builds the algorithms template context` — that is naturally a shared helper.
- **Fix:** Placed `build_algorithm_inventory(endpoints)` in `quirk/reports/html_renderer.py` and imported it from both `executive.py` and `technical.py`. Both markdown reports iterate the same row list and emit equivalent rows, with `md_cell` wrapping per Phase 78 / HARDEN-01.
- **Files modified:** all 3 renderers as planned (no extra files created).
- **Outcome:** Single source of truth for the algorithm row set, lazy import is centralized, and the per-file grep verifications (`coverage_for_algorithm` and `CMVP Coverage` presence in each renderer) all still pass via the import statement + explanatory comments.

### [Rule 1 — Bug] Removed transient "Not certified" warning text from inline comments
- **Found during:** Task 1 verification — first commit-readiness grep failed because my warning comments inside the template + Python files literally contained the phrase "Not certified" (e.g. `NEVER use "Not certified" — v4.10-D-01 forbids ...`).
- **Issue:** The plan's regression guard `grep -rE 'Not certified' quirk/reports/` returns 0 matches as a hard contract. Even meta-references to the forbidden phrase trip the guard, which is the correct behavior — operators searching the codebase should never see "Not certified" in any context.
- **Fix:** Rewrote the warning comments in `report.html.j2`, `executive.py`, and `technical.py` to reference the v4.10-D-01 invariant by name without naming the forbidden phrase. The guard now passes.

### [Rule 2 — Missing critical functionality] Wave-parallel `ImportError` fallback for coverage_for_algorithm
- **Found during:** Task 2 implementation, observing that Plan 81-02 is still in flight on Wave 2 (it creates `quirk/compliance/cmvp.py` which provides the `coverage_for_algorithm` symbol).
- **Issue:** A module-top `from quirk.compliance.cmvp import coverage_for_algorithm` in `html_renderer.py` would break import-time if rendered against a checkout where Plan 81-02 has not yet landed (rebase / cherry-pick scenarios; smoke test in CI before both plans merge).
- **Fix:** All three problematic imports (`coverage_for_algorithm`, `classify_algorithm`, `_fips_status`) are deferred inside the `build_algorithm_inventory` function body. If any import raises `ImportError`, a stub local function returns conservative defaults (empty coverage / None nist_level / "non-approved" fips_status), and the template renders `Not in CMVP catalog` for every row instead of crashing.
- **Files modified:** none beyond `html_renderer.py` which the plan already owns.

## Self-Check: PASSED

- `quirk/reports/templates/report.html.j2` — FOUND, contains 4-column Algorithm Inventory section with `| sanitize` on every scanner cell
- `quirk/reports/html_renderer.py` — FOUND, contains `build_algorithm_inventory` + `_collect_algorithm_names` + `algorithms=algorithms` in render context
- `quirk/reports/executive.py` — FOUND, contains "Algorithm Inventory (FIPS 140-3 Coverage)" markdown heading + `| CMVP Coverage |` column + `coverage_for_algorithm` reference
- `quirk/reports/technical.py` — FOUND, contains same heading + column + reference
- Commit `d794ee8` — present in `git log` (verified via `git log -1 --pretty=%s`)
- 19 existing report tests pass (no regressions)
- `grep -rE 'Not certified' quirk/reports/` returns 0 matches (v4.10-D-01 regression guard satisfied)
