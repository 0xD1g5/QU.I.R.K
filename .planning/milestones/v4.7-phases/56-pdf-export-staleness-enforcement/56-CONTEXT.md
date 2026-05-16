---
phase: 56-pdf-export-staleness-enforcement
type: context
status: active
source: /gsd-discuss-phase 56
updated: 2026-05-08
milestone: v4.7 Governance & Compliance Platform
requirements: [QRAMM-16]
---

# Phase 56: PDF Export & Staleness Enforcement - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 56 extends the existing `/print` route in `src/dashboard/src/pages/print.tsx` to include a QRAMM governance section that starts on a new page. The section contains four sub-components: executive QRAMM summary paragraph, dimension scorecard table, static SVG radar chart, and compliance framework mapping summary (8-row overview table followed by full practice-level detail per framework). The existing Technical Findings, Certificate Inventory, CBOM, and Migration Roadmap sections must not regress.

**In scope:**
- New `useQRAMMPrintData()` hook in `src/dashboard/src/hooks/` — fetches most recent scored QRAMM session, its score, and its compliance-map
- New QRAMM section added to `print.tsx` after the Migration Roadmap section (new page via `.print-section`)
- Pure inline SVG polygon radar chart (computed from 4 dimension scores; no recharts import)
- Compliance section: 8-row summary table + full practice-area detail flowing continuously after it
- No-session placeholder copy when no scored session exists

**Out of scope:**
- Staleness enforcement CI gate — `tests/test_qramm_staleness.py` already shipped in Phase 55; no new staleness work needed
- Recharts dependency in print.tsx — explicit decision against this
- Industry benchmark overlay in radar chart — deferred to a future phase
- Interactive QRAMM compliance mapping in the dashboard (Phase 55 complete)
- Multiple QRAMM sessions / session picker UI (future phase)

</domain>

<decisions>
## Implementation Decisions

### Radar Chart Rendering

- **D-01:** The QRAMM radar chart in the PDF is a **pure inline SVG polygon** computed from the session's 4 dimension scores (CVI, SGRM, DPE, ITR). It is rendered entirely in JSX as a static `<svg>` element inside `print.tsx`. No recharts import is added to print.tsx.
  - Rationale: recharts renders SVG but carries animation state and event handlers that can produce unreliable output during browser print capture. A pure SVG polygon is deterministic and predictable at any print resolution.
  - Layout: 4 axes at compass positions (CVI=top, SGRM=right, DPE=bottom, ITR=left) on a fixed 200×200 viewBox. Polygon points computed from `score / 4 * radius` per axis. Axis labels and score values rendered as `<text>` elements.

- **D-02:** Session scores only — no industry benchmark overlay polygon. The benchmark comparison belongs in the interactive dashboard Scorecard tab. Keeping the PDF radar single-polygon makes it unambiguous for any reader.

### QRAMM Data Fetch for Print

- **D-03:** A new `useQRAMMPrintData()` hook is created in `src/dashboard/src/hooks/useQRAMMPrintData.ts`. It returns `{ scoreResult, complianceRows, loading, error }`.
  - Fetch chain: `GET /api/qramm/sessions` → find most recent session where `score_json` is populated → `GET /api/qramm/sessions/{id}/score` + `GET /api/qramm/sessions/{id}/compliance-map` in parallel.
  - The hook does NOT reuse or extend `useQRAMMSession.ts` — that hook is scoped to the live assessment UI and fetches session + answers, which are not needed for print.

- **D-04:** When multiple QRAMM sessions exist, the print page uses the **most recent scored session** (i.e., the most recent entry from `GET /api/qramm/sessions` that has `score_json !== null`). If no scored session exists, the hook returns `{ scoreResult: null, complianceRows: null, loading: false, error: null }` and the print page renders the no-session placeholder.

### No-Session Fallback

- **D-05:** The QRAMM section **always appears** in the PDF (always renders on a new page, always has an `<h2>QRAMM Governance Assessment</h2>` heading). When no scored session exists, the body of the section shows:
  > "No QRAMM assessment completed — run an assessment from the dashboard to populate this section."
  
  This keeps the PDF structure consistent across all consultant engagements and signals the capability exists without appearing broken.

### Compliance Framework Mapping Summary

- **D-06:** The compliance section has a **two-part structure**, designed to serve two audiences in one PDF:
  1. **Executive summary table** — 8 rows, one per framework. Columns: Framework Name | Coverage Tier | Source. Fits on one page. Intended for executive/board readers who need a signal, not a drill-down.
  2. **Per-framework practice detail** — Immediately below the summary table (no page break), each of the 8 frameworks gets a sub-section listing **all practice areas** relevant to it, with the practice's relevance score derived from the session's dimension scores. Intended for CISO/compliance officer readers doing gap analysis from the PDF.

- **D-07:** No forced page breaks between individual framework sections. The detail block flows continuously after the summary table. This saves pages and works cleanly in PDF reader scroll/search.

- **D-08:** Coverage Tier badge labels and Source labels in the summary table mirror the Phase 55 dashboard convention: "Scanner-informed" (CVI-relevant frameworks) vs "Manual only" (all-manual-evidence frameworks). The badge styling uses the same static CSS classes in PRINT_CSS.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 56 Requirements
- `.planning/REQUIREMENTS.md` §QRAMM-16 — locked requirement: combined PDF export includes QRAMM section; existing Technical Findings layout not regressed
- `.planning/ROADMAP.md` §"Phase 56: PDF Export & Staleness Enforcement" — goal, success criteria, dependency chain (depends on Phase 54 + 55)

### Foundation Phases (MUST READ)
- `.planning/phases/55-qramm-compliance-mapping-view/55-CONTEXT.md` — compliance-map endpoint shape (D-05/D-06), `scanner_informed` flag, SCANNER_COVERAGE dict, framework names + short keys (`NIST_PQC`, `NSM10`, `CNSA2`, `ISO27001`, `ETSI_QS`, `PCI_DSS`, `CC`, `BSI_TR`), staleness gate already shipped
- `.planning/phases/54-qramm-assessment-ui-scorecard/54-CONTEXT.md` — QRAMM dimension names (CVI/SGRM/DPE/ITR), scorecard score shape, `QRAMMContext` and `useQRAMMSession` patterns
- `.planning/phases/51-qramm-core-infrastructure/51-CONTEXT.md` — ORM models, session schema, `score_json` field, no risk_engine imports rule (D-09)

### Live Implementation (Print Route)
- `src/dashboard/src/pages/print.tsx` — existing print page; QRAMM section appended after `PrintRoadmap`; PRINT_CSS extended with new badge/table classes; static CSS-only pattern MUST be preserved
- `src/dashboard/src/hooks/useScanData.ts` — hook pattern to mirror for `useQRAMMPrintData.ts`

### Live Implementation (QRAMM API)
- `quirk/dashboard/api/routes/qramm.py` — `GET /api/qramm/sessions` (list), `GET /api/qramm/sessions/{id}/score` (score shape), `GET /api/qramm/sessions/{id}/compliance-map` (compliance-map shape with `scanner_informed`, `relevance_score`, `framework`, `practice_area`)
- `quirk/qramm/compliance_map.py` — `QRAMM_COMPLIANCE_WEIGHTS`, `SCANNER_COVERAGE` — framework/practice data source
- `quirk/qramm/model_meta.py` — `QRAMM_MODEL` dict (already has `last_verified`); staleness gate is `tests/test_qramm_staleness.py` (Phase 55 — done)

### Frontend Patterns
- `src/dashboard/src/hooks/useQRAMMSession.ts` — existing session hook (do NOT extend for print; create a separate hook per D-03)
- `src/dashboard/src/components/ui/badge.tsx` — badge component in the dashboard; print.tsx uses its own static CSS badge classes instead (no component import in print)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/dashboard/src/pages/print.tsx` — the entire print page infrastructure: PRINT_CSS static string, `.print-section` pattern for page breaks, `PrintFindings` / `PrintCerts` / `PrintCbom` / `PrintRoadmap` sub-components. QRAMM section follows the same sub-component shape (`PrintQRAMM`).
- `src/dashboard/src/hooks/useScanData.ts` — `{ data, loading, error }` return shape; `useQRAMMPrintData.ts` mirrors this exactly.
- `quirk/dashboard/api/routes/qramm.py:GET /api/qramm/sessions` — returns a list; most-recent-scored session is the first entry with non-null `score_json`.

### Established Patterns
- **Static CSS-only in print.tsx** — The `PRINT_CSS` constant is a pure string; no Tailwind class names, no CSS variables, no dynamic interpolation. Any new badge or table styles for the QRAMM section must be added as string entries to the `PRINT_CSS` array. This is mandatory — the print route does not go through the Tailwind JIT pipeline.
- **`.print-section` = new page** — The CSS rule `break-before: page` is applied to every `.print-section` div (except the first child). Adding `<div className="print-section">` automatically starts the QRAMM content on a new page. No inline styles needed for pagination.
- **No recharts in print.tsx** — Explicit decision (D-01). The print page has no chart library imports. Radar chart is raw SVG.
- **`data-ready` attribute on body** — `print.tsx` sets `document.body.setAttribute('data-ready', 'true')` when data loads. The QRAMM hook must participate in this gate: `data-ready` should only be set once BOTH `useScanData` and `useQRAMMPrintData` have resolved (loading = false for both).

### Integration Points
- `src/dashboard/src/pages/print.tsx` — extend `PrintPage()` to call `useQRAMMPrintData()` alongside `useScanData()`; add `<div className="print-section"><PrintQRAMM ... /></div>` after `PrintRoadmap`
- `src/dashboard/src/hooks/` — new `useQRAMMPrintData.ts` file alongside existing hooks
- `PRINT_CSS` array — extend with QRAMM-specific classes (radar SVG container sizing, compliance tier badge colors matching Phase 55 convention)

</code_context>

<specifics>
## Specific Ideas

- **Radar SVG layout:** CVI at top (12 o'clock), SGRM at right (3 o'clock), DPE at bottom (6 o'clock), ITR at left (9 o'clock). Each axis score label printed adjacent to its axis endpoint. Polygon filled with a semi-transparent color using `fill-opacity`.
- **Compliance summary table columns:** `Framework` | `Coverage Tier` | `Source` (Scanner-informed / Manual only) — mirrors Phase 55's dashboard badge convention.
- **No-session placeholder text:** "No QRAMM assessment completed — run an assessment from the dashboard to populate this section." — fixed string, not dynamic.
- **`data-ready` gate:** Both `useScanData()` and `useQRAMMPrintData()` must have `loading = false` before `data-ready` is set on body. This ensures headless PDF generators (if used in future) capture a fully-loaded page.
- **Practice-area detail rendering:** Each of the 8 framework sub-sections is an `<h3>` heading followed by a table with columns: `Practice Area` | `Dimension` | `Relevance Score` | `Scanner-Informed`. All practice rows for that framework flow consecutively.

</specifics>

<deferred>
## Deferred Ideas

- **Industry benchmark overlay in radar** — User chose session-only polygon for simplicity. A future phase could overlay a dashed benchmark polygon once the benchmark data model matures.
- **`/print?session=<id>` URL parameter** — Would allow printing a specific QRAMM session rather than the most recent. Not needed in v4.7; the hook always picks most-recent-scored.
- **Staleness enforcement** — Already shipped in Phase 55 (`tests/test_qramm_staleness.py`). No further work needed in Phase 56.

</deferred>

---

*Phase: 56-pdf-export-staleness-enforcement*
*Context gathered: 2026-05-08*
