---
type: todo
created: 2026-11-09
title: Dashboard Export PDF shows a skip-lowered score with no skip reason
source: v5.28.2 milestone audit, integration check F2 (.planning/milestones/v5.28.2-MILESTONE-AUDIT.md)
priority: medium
area: src/dashboard/src/pages/print.tsx:506, derive_dashboard_finding_items (dashboard deriver)
status: pending
resolves_phase: null
owner: null
---

# Dashboard Export PDF shows a skip-lowered score with no skip reason

Kind: product

Ledger row: `261109-dashboard-export-pdf-omits-coverage-skip-reasons` in `.planning/LEDGER.md`. Related: `999.132`
(dashboard/report divergences, Phase 236 candidate).

## Observed

The dashboard Export PDF is Playwright printing the React `/print` page. That is a different pipeline from the CLI
report (memory `project_two_report_pipelines`).

- `print.tsx:506` destructures only `meta, score, confidence, findings, certificates, cbom_components, roadmap`.
  It never reads `data.coverage` and has no Scan Coverage section.
- The dashboard finding list (`derive_dashboard_finding_items`) does not turn coverage-skip ADVISORY rows into the
  "Connector skipped" coverage_gap finding that `findings_evaluator` emits on the CLI side.

So a client deliverable exported from the dashboard carries a score that a skip lowered, and says nowhere why.
The CLI pipeline (technical/executive markdown, HTML, DOCX, and the PDF printed from HTML) does show the reason.
235.3's four-surface parity test (`tests/test_report_coverage_parity.py:659`) covers only the CLI pipeline.

The same omission already existed for `missing_binary` / `missing_extra`, so this is not a 5.28.2 regression.
It does narrow COVTRUTH-04's "the reports show the recorded skip reason" to the CLI reports.

## Fix sketch

Add a Scan Coverage section to `/print` from `/api/scan/latest.coverage`, reusing `coverage-reason.ts`. Add the
`/print` page to the coverage parity test (vitest, or the Playwright export path). Decide whether the dashboard
deriver should also emit the coverage_gap finding, for findings-list parity with the CLI.

## Feasibility & Effort

Medium (half a day). Writing the print section is straightforward. The parity test across the two pipelines is
the larger part. It needs `npm run build` and the bundle-freshness gate.
