# Phase 5: Web Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-03-30
**Phase:** 05-web-dashboard
**Mode:** discuss
**Areas discussed:** Multi-scan navigation, PDF export, CBOM viewer, Frontend bundling, Data visualization

---

## Areas Discussed

### Multi-scan navigation
**Question:** Latest-scan-only vs scan selector dropdown.
**Answer:** Latest-scan-only for v1. User noted this is a v2/v3 feature and didn't want to back into a corner.
**Resolution:** API shaped for future multi-scan (returns `scan_id` in metadata, `?scan_id=` param reserved). Feature deferred to BACK-02 in ROADMAP.md.

### PDF export approach
**Question:** Playwright headless vs WeasyPrint.
**Answer:** Playwright headless selected.
**Rationale:** "What you see in the dashboard IS the PDF" — gauges, charts, and Cytoscape graphs render correctly. WeasyPrint cannot render canvas/SVG visuals from shadcn/ui. 150MB Chromium install accepted as acceptable trade-off.

### CBOM viewer format
**Question:** Structured table vs graph visualization.
**Answer:** Both — table tab AND Cytoscape.js graph tab.
**Additional scope:** User requested configurable algorithm vulnerability thresholds (organizations have different risk tolerances). Resolved as: config.yaml `algorithm_overrides` in v1, dashboard UI config panel deferred to BACK-01 in ROADMAP.md.

### Frontend bundling model
**Question:** Pre-built static assets in pip package vs separate dev server.
**Answer:** Pre-built static assets committed to `quirk/dashboard/static/`. FastAPI serves them as StaticFiles. End users need no Node.js.

### Data visualization (user-initiated topic)
**User input:** "Something like using Cytoscape.js or React Flow to visually show the algorithms in use and what systems or functions are the source. This is an example, lets take it further."
**Discussion:** Three visualization angles identified.
**Selected:**
1. Crypto landscape graph (Cytoscape.js) — algorithm nodes → source system nodes, blast radius visualization
2. Score gauges + severity breakdown — 4-subscore radial gauges + severity bar chart (already required by UI-02)
3. Migration dependency graph — directed Cytoscape.js graph from `build_phased_roadmap()` output

**Not selected:** Severity heatmap (noted as future candidate in deferred section)

---

## Backlog Items Added to ROADMAP.md

| ID | Item |
|----|------|
| BACK-01 | Dashboard UI config panel for algorithm vulnerability thresholds |
| BACK-02 | Multi-scan navigation (scan selector dropdown) |
