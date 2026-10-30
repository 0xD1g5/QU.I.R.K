---
type: todo
created: 2026-10-25
source: Phase 231 review round R1 (WR-02, IN-01..04, IN-06), 231-REVIEW-R1.md; R1 reported BLOCKERS 0
priority: medium
area: src/dashboard/src/components/qramm/ScorecardTab.tsx, src/dashboard/src/components/qramm/ComplianceMapTab.tsx, src/dashboard/src/lib/qramm-assessment.ts, src/dashboard/src/pages/print.tsx, quirk/dashboard/api/routes/qramm.py
status: pending
resolves_phase: null
owner: "999.137"
---

# QRAMM surfaces: edge-case state truth left after Phase 231

- [ ] **WR-02:** if the question catalog fails to load (`ScorecardTab.tsx:44-71`), the page swallows the error.
  - After a successful score, every dimension then reads "Not assessed" with its scores hidden.
  - The Compliance Map tab shows real states for the same session. Before 231, the same failure only showed 0% completion.
  - Fix: show the load error, or fall back to the server's state.
- [ ] **IN-01:** before the first score, the compliance map shows "Scanner-measured" and "Self-assessed" badges next to empty score cells.
- [ ] **IN-02:** `dimensionStateFromAnswered` and `SCANNER_MEASURED_DIMENSIONS` are used only in tests, and a comment claims the scorecard uses them.
- [ ] **IN-03:** if the reload after Calculate Score fails, the "Compliance map updated." announcement stays armed and fires on a later, unrelated load.
- [ ] **IN-04:** the radar charts, on screen and in print, still plot 0.0 for "Not assessed" dimensions. Check memory `feedback_recharts_static_children` before changing chart children.
- [ ] **IN-06:** the server types `ComplianceMapRow.coverage_status` as `Optional[str]` rather than the `RowCoverageStatus` Literal, so a mistyped status value would pass validation.

## Feasibility & Effort

- **CONFIRMED** by reading; R1 traced each item.
- Effort: **S**. These are mostly dashboard edits, plus one type annotation.
- Rebuild the bundle (`npm run build`) and run the bundle-freshness gate.
