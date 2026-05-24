---
phase: 98-executive-narrative-score-transparency
plan: "03"
subsystem: reports
tags: [exec-narrative, score-transparency, cross-surface-parity, uat-docs, obsidian-sync, parity-test]
requires: [98-02]
provides: [test_cross_surface_parity, UAT-98-01..07]
affects:
  - tests/test_cross_surface_parity.py
  - docs/UAT-SERIES.md
tech-stack:
  added: []
  patterns: [two-surface-identity-gate, single-exec-content-instance-shared-to-both-renderers]
key-files:
  created:
    - tests/test_cross_surface_parity.py
  modified:
    - docs/UAT-SERIES.md
decisions:
  - "FAIR-band score_raw fixture for both parity tests: no congruence guard restriction, guaranteed top_risk from RSA HIGH finding"
  - "Risk-label count gate (not HTML element count): counts occurrences of each expected_label in both outputs; stable regardless of HTML structure changes"
  - "UAT-98-07 PDF parity marked DEFERRED-acceptable: structural parity guaranteed by D-03; visual/Playwright verification is manual"
metrics:
  duration_minutes: 7
  completed: "2026-05-24"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 98 Plan 03: Cross-Surface Parity Gate and UAT-SERIES.md Update Summary

**One-liner:** Belt-and-suspenders cross-surface parity test (EXEC-04/D-03a) asserting identical narrative_lead and top_risks labels across CLI and HTML from one ExecContent instance, plus Phase 98 UAT series (UAT-98-01..07) added to docs/UAT-SERIES.md and synced to the Obsidian vault.

## What Was Built

### Task 1: Cross-surface content parity test

Created `tests/test_cross_surface_parity.py` with two test functions matching the VALIDATION.md node IDs.

**`test_narrative_content_parity`** (EXEC-04 / D-03a):
- Builds one `ExecContent` instance via `build_exec_content()` with a FAIR-band score_raw (no congruence guard restriction) and one RSA HIGH finding (guarantees a top_risk entry).
- Passes the same instance to `build_exec_markdown()` (CLI) and `render_html_report()` (HTML, rendered to tmp_path).
- Asserts `exec_content.narrative_lead` appears verbatim in BOTH outputs.
- Message format names EXEC-04 and D-03 for future debuggability.

**`test_top_risks_parity`** (EXEC-04 / D-03a):
- Builds the same `ExecContent` instance.
- Counts occurrences of each `exec_content.top_risks[].risk_label` in CLI output and HTML output.
- Asserts CLI count == HTML count == `len(exec_content.top_risks)`.
- Cross-surface label identity: each label in `expected_labels` must appear in both CLI and HTML output.

Both tests follow the `test_score_render_parity.py` two-surface identity gate pattern (PATTERNS.md §test_cross_surface_parity.py).

Commit: `708be4e`

### Task 2: Update docs/UAT-SERIES.md and sync to Obsidian vault

Updated `docs/UAT-SERIES.md`:
- `**Last Updated:**` bumped to `2026-05-24` with Phase 98 COMPLETE history entry.
- Added `## UAT Series 98: Phase 98 — Executive Narrative + Score Transparency` section with 7 test cases:
  - UAT-98-01: Readiness Assessment narrative before findings CLI (EXEC-01)
  - UAT-98-02: Priority Business Risks in CLI and HTML (EXEC-02)
  - UAT-98-03: Roadmap effort/impact priority labels (EXEC-03)
  - UAT-98-04: "How this score was computed" rollup formula in HTML (TRANS-02)
  - UAT-98-05: Congruence guard blocks GOOD/EXCELLENT headline with CRITICAL findings (TRANS-03)
  - UAT-98-06: Cross-surface narrative and risk parity automated gate (EXEC-04)
  - UAT-98-07: PDF visual parity manual verification (EXEC-04, DEFERRED/Playwright-environment-gated)

Synced to Obsidian vault per CLAUDE.md Step 3:
- Wrote frontmatter-prepended copy to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`
- Used `printf ... > /tmp/uat_vault.md && cat docs/UAT-SERIES.md >> /tmp/uat_vault.md && cp ...` pattern (not `obsidian CLI content=` — file too large for shell expansion).

Commit: `0075117`

## Decisions Made

1. **FAIR-band fixture for parity tests** — Both parity tests use `"rating": "FAIR"` score_raw. FAIR is unrestricted by the D-06 congruence guard (FAIR/POOR can coexist with any CRITICAL count), so the tests are self-contained without needing to suppress or mock the guard.

2. **Risk-label count gate via substring scan** — `test_top_risks_parity` counts how many of `expected_labels` appear in each output (not counting HTML `<li>` elements or markdown bullets by regex). This is more stable across HTML structure changes while still enforcing the parity contract.

3. **UAT-98-07 PDF marked DEFERRED-acceptable** — The manual PDF visual parity check is marked `DEFERRED (Playwright environment required)` per the VALIDATION.md §Manual-Only Verifications entry. D-03's structural single-source guarantee makes automated PDF content parity redundant; the manual check is belt-and-suspenders for visual layout only.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Both test files are fully functional. `docs/UAT-SERIES.md` Phase 98 test cases reference real automated test commands that pass. UAT-98-07 is intentionally deferred (manual, Playwright-gated) — documented explicitly in the plan.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. Test files are pure Python with no I/O outside tmp_path. UAT-SERIES.md is documentation only.

## Self-Check

Files created:
- `tests/test_cross_surface_parity.py`: FOUND (`708be4e`)
- `.planning/phases/98-executive-narrative-score-transparency/98-03-SUMMARY.md`: writing now

Files modified:
- `docs/UAT-SERIES.md`: FOUND (`0075117`)

Vault file:
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`: FOUND

Commits:
- `708be4e` test(98-03): cross-surface content parity gate (EXEC-04 / D-03a): FOUND
- `0075117` docs(98-03): update UAT-SERIES.md with Phase 98 test series and sync to vault: FOUND

Quick suite: `python -m pytest tests/test_exec_content_model.py tests/test_congruence_guard.py tests/test_exec_narrative_ordering.py tests/test_cross_surface_parity.py -q` — 23 passed

## Self-Check: PASSED
