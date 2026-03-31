---
status: partial
phase: 05-web-dashboard
source: [05-VERIFICATION.md]
started: 2026-03-31T00:00:00Z
updated: 2026-03-31T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Theme toggle persistence
expected: Clicking the mode toggle switches between light/dark; preference persists across page reload (stored in localStorage key `quirk-ui-theme`)
result: [pending]

### 2. Sidebar collapse on mobile/narrow viewport
expected: Sidebar collapses to icon-only view at narrow widths; expands on hover or toggle
result: [pending]

### 3. Cytoscape CBOM bipartite graph renders
expected: Navigating to /cbom → Graph tab shows algorithm→system nodes with quantum-safety color coding (red = vulnerable, green = safe)
result: [pending]

### 4. Cytoscape Migration Roadmap DAG renders
expected: Navigating to /roadmap shows a DAG of migration steps colored by timeframe; nodes are draggable
result: [pending]

### 5. PDF export end-to-end download
expected: Clicking "Export PDF" on Executive page triggers POST /api/export/pdf and downloads a PDF file (requires Playwright Chromium installed)
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
