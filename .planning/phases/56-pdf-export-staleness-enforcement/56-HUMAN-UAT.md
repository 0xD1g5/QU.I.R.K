---
status: partial
phase: 56-pdf-export-staleness-enforcement
source: [56-VERIFICATION.md]
started: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual layout of QRAMM section in Print Preview
expected: Radar SVG renders first (before executive intro paragraph), followed by dimension scorecard (4 rows + overall maturity caption), 8-row compliance coverage table, and 8 per-framework detail tables — all after Migration Roadmap on a new page
result: [pending]

### 2. No-session placeholder path
expected: When no QRAMM session is scored, the QRAMM heading appears but only the locked placeholder text renders — "No QRAMM assessment completed — run an assessment from the dashboard to populate this section."
result: [pending]

### 3. Regression check — existing sections unchanged
expected: Technical Findings, Certificate Inventory, CBOM, and Migration Roadmap sections all render correctly and are visually unchanged
result: [pending]

### 4. data-ready timing
expected: After both useScanData and useQRAMMPrintData resolve, document.body.getAttribute('data-ready') returns "true" with no transient removal between renders
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
