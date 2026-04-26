---
status: partial
phase: 31-trend-analysis
source: [31-VERIFICATION.md]
started: 2026-04-26T00:00:00Z
updated: 2026-04-26T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Trends page baseline state
expected: Navigate to /trends with 0 or 1 scan session — centered "Baseline scan" headline with "Run another scan..." subtext, no cards shown
result: [pending]

### 2. Trends page two-session state
expected: With 2+ scan sessions — Score Delta card with green (positive) / red (negative) / muted (zero) badge; New Findings card; Resolved Findings card; scan error row; collapsible sample tables showing Host/Port/Protocol/Severity with coloured severity badges
result: [pending]

### 3. Trends page error state
expected: Stop backend, refresh /trends — single muted error text line, no blank/crashed screen, no React error boundary
result: [pending]

### 4. DevTools console on /trends
expected: No React errors or warnings in browser DevTools console
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
