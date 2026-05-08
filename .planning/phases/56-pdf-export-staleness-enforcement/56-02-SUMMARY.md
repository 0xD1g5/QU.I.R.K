---
phase: 56-pdf-export-staleness-enforcement
plan: "02"
subsystem: dashboard-print
tags: [react, print, qramm, svg, pdf, typescript]
dependency_graph:
  requires: [useQRAMMPrintData hook (56-01)]
  provides: [PrintQRAMM sub-component, QRAMM section in /print route]
  affects: [print route, PDF export, data-ready gate]
tech_stack:
  added: []
  patterns: [inline SVG radar polygon, static CSS PRINT_CSS extension, parallel hook composition, graceful error degradation]
key_files:
  created: []
  modified:
    - src/dashboard/src/pages/print.tsx
decisions:
  - "PrintQRAMM renders radar SVG FIRST then executive intro per UI-SPEC §Layout Structure"
  - "qrammError causes graceful degradation to no-session placeholder — does not block rest of PDF"
  - "data-ready gate updated to wait for both useScanData and useQRAMMPrintData (CONTEXT.md code_context)"
  - "5 new PRINT_CSS entries for tier badges and QRAMM-specific layout classes"
  - "No recharts import — pure inline SVG polygon per D-01"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-08"
  tasks_completed: 3
  files_created: 0
  files_modified: 1
requirements: [QRAMM-16]
---

# Phase 56 Plan 02: PrintQRAMM Section — Print Page Extension Summary

## One-liner

Extended `print.tsx` with a `PrintQRAMM` sub-component rendering an inline SVG radar chart, dimension scorecard, and 8-framework compliance coverage tables on a new PDF page after the Migration Roadmap.

## What Was Built

### Task 1: Extend PRINT_CSS with 5 QRAMM-specific style entries

Appended 5 new string entries to the `PRINT_CSS` array in `src/dashboard/src/pages/print.tsx`:

- `.tier-scanner{background:#4ba8a8;color:#fff}` — teal badge for Scanner-informed tier (matches Phase 55 dashboard convention)
- `.tier-manual{background:#e4e4e7;color:#52525b}` — muted badge for Manual only tier
- `.qramm-radar{margin:16px 0}` — SVG radar container spacing
- `.qramm-footnote{font-size:12px;color:#52525b;margin-top:8px;border-top:1px solid #e4e4e7;padding-top:8px}` — footnote styling
- `.qramm-detail-section{margin-top:16px}` — per-framework sub-section spacing

All entries are plain string literals matching the existing PRINT_CSS prefix conventions (`.sev-*`, `.qs-*`).

**Commit:** `c17064b`

### Task 2: Add PrintQRAMM sub-component

Added to `src/dashboard/src/pages/print.tsx`:

**Module-level constants (added after imports):**
- `FRAMEWORK_DISPLAY: Record<string, string>` — maps framework keys to display names (NIST_PQC → "NIST PQC Standards", etc.)
- `FRAMEWORK_ORDER: string[]` — ordered list of 8 framework keys
- `QRAMM_DIMS: readonly ["CVI", "SGRM", "DPE", "ITR"]`

**Imports added:**
- `import { useQRAMMPrintData } from "@/hooks/useQRAMMPrintData"`
- `import type { QRAMMScoreResponse, QRAMMComplianceMapRow } from "@/types/api"`

**`PrintQRAMM` function component (451 lines total, well above min_lines: 350):**

No-session branch: renders locked D-05 placeholder copy `<p className="meta">No QRAMM assessment completed — run an assessment from the dashboard to populate this section.</p>`

Scored-session branch renders in this exact order (per UI-SPEC §Layout Structure):
1. Inline SVG radar `<svg viewBox="0 0 200 200" width={200} height={200}>` — 4 compass axes (CVI=top, SGRM=right, DPE=bottom, ITR=left), score polygon with `fill="#4ba8a8"` + `fillOpacity={0.18}`, axis labels, score values adjacent to vertices
2. Executive intro paragraph (locked copy)
3. Dimension Scorecard h3 + 4-row table (CVI/SGRM/DPE/ITR; columns: Dimension | Raw Score | Weighted Score | Maturity)
4. Compliance Framework Coverage h3 + 8-row summary table with `.tier-scanner`/`.tier-manual` badges
5. Footnote paragraph in `.qramm-footnote` (locked copy from Phase 55 FOOTNOTE constant)
6. 8 per-framework `<div className="qramm-detail-section">` sub-sections with h3 + practice-area detail table

**Commit:** `f32c50b`

### Task 3: Wire useQRAMMPrintData into PrintPage and extend data-ready gate

Modified `PrintPage()` in `src/dashboard/src/pages/print.tsx`:

1. Added `const { scoreResult, complianceRows, loading: qrammLoading, error: qrammError } = useQRAMMPrintData()` immediately after `useScanData()` call
2. Added `console.error` for `qrammError` (graceful degradation — QRAMM errors do not block rest of PDF)
3. Updated `data-ready` useEffect: body `{ if (data && !qrammLoading) }` with dependency array `[data, qrammLoading]`
4. Inserted Section 7 after Migration Roadmap:
   ```tsx
   <div className="print-section">
     <h2>QRAMM Governance Assessment</h2>
     <PrintQRAMM
       scoreResult={qrammError ? null : scoreResult}
       complianceRows={qrammError ? null : complianceRows}
     />
   </div>
   ```
5. Dashboard build artifacts updated (new bundle hash from added QRAMM code)

Dashboard build (`npm run build`) succeeded. All existing sections (PrintFindings, PrintCerts, PrintCbom, PrintRoadmap) unchanged.

**Commit:** `d456f2f`

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria passed on first attempt.

## Threat Mitigations Applied

- **T-56-07 (Tampering):** All QRAMM values rendered through React's auto-escaping JSX text channel (`{value}` and `<text>{value}</text>`). No raw HTML insertion paths added. SVG numeric attributes coerce to strings safely.
- **T-56-08 (Information Disclosure):** No new endpoint exposes data beyond what existing `/api/qramm/*` endpoints already return. The PDF is an intentional deliverable artifact.
- **T-56-09 (DoS):** Compliance rows bounded at 96 (12 practices × 8 frameworks) by API contract; map iterations are O(rows × frameworks) = bounded constant.

## Known Stubs

None — all data flows from live `useQRAMMPrintData` hook. No hardcoded values, no placeholder data. When no scored session exists, the no-session placeholder renders per D-05 design decision (this is intentional behavior, not a stub).

## Threat Flags

None — no new trust boundary surfaces introduced beyond what was planned in the threat model. The print route is read-only; no state-changing actions added.

## Self-Check: PASSED

- `src/dashboard/src/pages/print.tsx` — FOUND (451 lines, above min_lines: 350)
- Commit `c17064b` — Task 1 (PRINT_CSS extensions)
- Commit `f32c50b` — Task 2 (PrintQRAMM sub-component)
- Commit `d456f2f` — Task 3 (PrintPage wiring + build artifacts)
- TypeScript: zero errors in print.tsx
- Dashboard build: `npm run build` exits 0
- All grep acceptance criteria: PASS
- Layout order (radar before intro): PASS
- Ordering (PrintRoadmap before PrintQRAMM): PASS

## Checkpoint Required

Task 4 is `type="checkpoint:human-verify"` — visual verification of the /print QRAMM section in browser required before this plan is marked complete.
