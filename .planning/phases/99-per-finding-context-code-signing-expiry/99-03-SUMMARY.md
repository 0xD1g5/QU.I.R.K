---
phase: 99-per-finding-context-code-signing-expiry
plan: "03"
subsystem: reports/renderers + chaos-lab oracle + docs
tags: [quantum-risk, render-parity, ctx-01, ctx-03, tdd, uat-series]
requires: ["99-02"]
provides:
  - Quantum Risk column in CLI markdown findings table (technical.py)
  - Quantum Risk column in HTML All Findings table (report.html.j2)
  - .quantum-risk-block in HTML Top Findings Description cell (report.html.j2)
  - CSS .quantum-risk-block + .quantum-risk-label rules in report.html.j2 style block
  - FALLBACK_QR module constant in technical.py (re-exports FALLBACK_QUANTUM_RISK)
  - Render-parity gate: tests/test_quantum_risk_render_parity.py (5 tests)
  - expected_results_v4.md ldaps section documenting both codesign detection paths
  - UAT-99-01..04 in docs/UAT-SERIES.md + Obsidian vault sync
affects:
  - quirk/reports/technical.py
  - quirk/reports/templates/report.html.j2
  - tests/test_quantum_risk_render_parity.py
  - quantum-chaos-enterprise-lab/expected_results_v4.md
  - docs/UAT-SERIES.md
tech-stack:
  added: []
  patterns:
    - FALLBACK_QR re-export from content_model.FALLBACK_QUANTUM_RISK (single source of truth)
    - | sanitize on all scanner-derived fields in Jinja2 template (T-99-06 XSS discipline)
    - .quantum-risk-block as sub-element of Description cell (no new column in narrow table)
    - FALLBACK_QR inline Jinja2 set for template-side fallback (mirrors module constant)
key-files:
  modified:
    - quirk/reports/technical.py (FALLBACK_QR + 7-column pipe-table)
    - quirk/reports/templates/report.html.j2 (CSS rules + All Findings col + Top Findings block)
    - quantum-chaos-enterprise-lab/expected_results_v4.md (ldaps codesign expiry paths)
    - docs/UAT-SERIES.md (UAT-99-01..04 + Last Updated bump)
  created:
    - tests/test_quantum_risk_render_parity.py
decisions:
  - "FALLBACK_QR in technical.py re-exports content_model.FALLBACK_QUANTUM_RISK (single source of truth)"
  - "HTML Top Findings: quantum_risk as .quantum-risk-block sub-element, not new column (narrow 4-col table)"
  - "HTML All Findings: quantum_risk as 7th column after Recommendation per UI-SPEC Interaction Contract"
  - "All scanner-derived quantum_risk values pass through | sanitize in Jinja2 (T-99-06)"
  - "Jinja2 autoescape converts apostrophes to &#39; — test uses apostrophe-free assertion fragments"
  - "FALLBACK_QR duplicated as Jinja2 set variable in template (cannot import Python module constants)"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-24"
  tasks_completed: 2
  files_modified: 4
  files_created: 1
requirements: [CTX-01, CTX-03]
---

# Phase 99 Plan 03: Render Parity + Oracle Update + UAT-SERIES Sync — Summary

**One-liner:** Quantum Risk column added to CLI markdown and HTML report surfaces via FALLBACK_QR + | sanitize discipline; render-parity gate created; chaos-lab oracle updated with both codesign detection paths; UAT-SERIES updated and synced to Obsidian vault.

## What Was Built

### Task 1: Quantum Risk rendering across CLI markdown + HTML (commits 5988ca4 RED, 6baec51 GREEN)

**`quirk/reports/technical.py` changes:**

1. Added `from quirk.reports.content_model import FALLBACK_QUANTUM_RISK` import.
2. Defined module-level `FALLBACK_QR = FALLBACK_QUANTUM_RISK` (re-exports from single source of truth).
3. Extended pipe-table header from 6 to 7 columns: added `Quantum Risk` between `Description` and `Recommendation`.
4. Extended separator row to match 7 columns.
5. In the row loop, reads `qr = (f.get("quantum_risk") or FALLBACK_QR)[:120]` and emits it via `md_cell(qr)` (T-99-07 pipe/markdown escape discipline).

**`quirk/reports/templates/report.html.j2` changes:**

1. Added two CSS rules to the `<style>` block (verbatim from 99-UI-SPEC.md §HTML/CSS Additions Contract):
   - `.quantum-risk-block { margin-top: 4px; font-size: 13px; line-height: 1.5; color: var(--text-muted); }`
   - `.quantum-risk-label { font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--accent); margin-right: 4px; }`
2. **Top Findings table:** Added `.quantum-risk-block` div inside the Description `<td>`, gated on `f.get('quantum_risk')`. Contains `.quantum-risk-label` span + `| sanitize` quantum_risk text (T-99-06).
3. **All Findings table:** Added `{% set FALLBACK_QR = "..." %}` Jinja2 variable (mirrors Python constant). Added `<th>Quantum Risk</th>` as 7th column. Added `<td>` with `.quantum-risk-label` span + `f.get('quantum_risk', FALLBACK_QR)[:200] | sanitize` (T-99-06).
4. PDF inherits HTML rendering via Playwright — no separate PDF work required.

**Acceptance criteria verification:**
- `grep -v '^#' quirk/reports/technical.py | grep -c 'Quantum Risk'` → 2 ✓
- `grep -Ec 'quantum_risk[^|]*\| sanitize' quirk/reports/templates/report.html.j2` → 3 ✓
- `grep -c 'quantum-risk-block' quirk/reports/templates/report.html.j2` → 2 (CSS rule + usage) ✓
- `python -m compileall quirk/reports/technical.py` → clean ✓

### Task 2: Render-parity test + oracle update + UAT-SERIES sync (commits b664b8d)

**`tests/test_quantum_risk_render_parity.py` (new, 5 tests):**

- `test_markdown_has_quantum_risk_column`: asserts `"Quantum Risk"` in `build_tech_markdown` output
- `test_markdown_renders_quantum_risk_text`: asserts truncated quantum_risk text appears in markdown cell
- `test_render_fallback_when_missing`: asserts FALLBACK_QR[:60] appears when `quantum_risk` absent
- `test_html_all_findings_has_quantum_risk`: asserts `"Quantum Risk"` header + apostrophe-free quantum_risk fragment in HTML
- `test_html_top_findings_risk_block`: asserts `"quantum-risk-block"` in rendered HTML

All 5 tests pass.

**`quantum-chaos-enterprise-lab/expected_results_v4.md` — ldaps codesign section:**

Added "Detection paths (Phase 99 CTX-03 update)" subsection documenting:
- Weak algorithm path (lab fixture exercises: RSA-1024/SHA-1 → HIGH)
- Certificate expired path (expired → HIGH, stacks with weak-crypto)
- Certificate approaching expiry path (≤90 days → MEDIUM, independent of weak-crypto)
- Lab fixture coverage note: 100-year-validity cert exercises only the weak-algorithm path; expiry paths covered by unit mocks in test_codesign_expiry_classification.py and test_codesign_findings_evaluator.py

**`docs/UAT-SERIES.md`:**
- Added UAT-99-01 (CLI markdown Quantum Risk column — automated)
- Added UAT-99-02 (HTML All Findings + Top Findings quantum_risk render — automated + manual visual)
- Added UAT-99-03 (code-signing expiry classification unit gate — automated)
- Added UAT-99-04 (full non-slow regression gate — automated)
- Bumped `**Last Updated:**` to 2026-05-24 with Phase 99 completion summary

**Vault sync:**
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` written via `printf` + `cp` recipe
- Verified: `ls "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md"` exits 0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion used apostrophe-containing string that Jinja2 autoescape converts to &#39;**
- **Found during:** Task 1 GREEN — `test_html_all_findings_has_quantum_risk` asserted `_QR_TEXT[:80]` which contains `"Shor's"` (apostrophe); Jinja2 autoescape renders it as `&#39;` in the HTML, making the literal string not found.
- **Issue:** Test searched for a verbatim string with apostrophe; rendered HTML uses HTML entity encoding.
- **Fix:** Changed assertion to use an apostrophe-free fragment: `"RSA key material is vulnerable to Shor"` (no apostrophe in this prefix).
- **Files modified:** `tests/test_quantum_risk_render_parity.py`
- **Commit:** 6baec51

## Verification

- `python -m compileall quirk/reports/technical.py` — PASS
- `python -m pytest tests/test_quantum_risk_render_parity.py -x -q` — 5 passed
- `python -m pytest tests/ -m "not slow" -q` — 35 pre-existing failures (identical to Plan 02 baseline per project memory); 2118 passed
- `grep -Ec 'quantum_risk[^|]*\| sanitize' quirk/reports/templates/report.html.j2` → 3 (T-99-06 XSS mitigated)
- `grep -ic 'expiry' quantum-chaos-enterprise-lab/expected_results_v4.md` → 10
- `ls "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md"` → exits 0 ✓
- `docs/UAT-SERIES.md` `**Last Updated:**` reflects 2026-05-24 and mentions "Quantum Risk" + "code-signing expiry" ✓

## Known Stubs

None — all copy is populated verbatim from 99-UI-SPEC.md locked strings. FALLBACK_QR re-exports FALLBACK_QUANTUM_RISK from content_model.py (single source of truth, no hardcoding).

## Threat Flags

None — Plan 99-03 modifies only report renderers and documentation. No new network endpoints, auth paths, schema changes, or trust boundaries. T-99-06 (XSS via quantum_risk in HTML) and T-99-07 (pipe injection in markdown) mitigations applied:
- T-99-06: all quantum_risk values in report.html.j2 pass through `| sanitize` (confirmed by grep -Ec → 3)
- T-99-07: quantum_risk in technical.py passes through `md_cell()` (confirmed by code review)

## Self-Check: PASSED

- `quirk/reports/technical.py` — exists; compiles; contains FALLBACK_QR + "Quantum Risk" column ✓
- `quirk/reports/templates/report.html.j2` — contains quantum-risk-block (CSS + usage) ✓
- `tests/test_quantum_risk_render_parity.py` — created; 5 tests pass ✓
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — contains "expiry" ≥10 times ✓
- `docs/UAT-SERIES.md` — Last Updated 2026-05-24; UAT-99-01..04 present ✓
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` — present ✓
- Commits 5988ca4, 6baec51, b664b8d — present in git log ✓
