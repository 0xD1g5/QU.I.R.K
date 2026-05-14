---
status: complete
phase: 66-dashboard-scan-history-clone-compare
source: [66-VERIFICATION.md]
started: 2026-05-14T12:16:39Z
updated: 2026-05-14T12:38:44Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Scan history table renders with all columns
expected: `/scans` page shows a table with columns for target, profile, calibration, score, finding counts, scanned_at, and Clone button for each row
result: passed

### 2. Sticky compare bar appears after 2 selections
expected: After checking 2 scan rows, a sticky bar appears at the bottom of the page with a "Compare" button
result: passed

### 3. FIFO auto-uncheck on 3rd selection
expected: When a 3rd scan checkbox is checked, the oldest of the 3 is automatically unchecked (FIFO), keeping selection at exactly 2
result: passed

### 4. Clone preload — dashboard-launched scan (no amber notice)
expected: Clicking Clone on a scan that was launched from the dashboard pre-fills scan-new with target/profile/calibration; no amber reconstruction notice appears
result: passed

### 5. Clone preload — CLI-launched scan (amber notice visible)
expected: Clicking Clone on a scan that was launched from the CLI pre-fills scan-new with reconstructed target; amber "Targets reconstructed from evidence" notice is visible
result: passed

### 6. Compare page — score header card with delta badge colors and icons
expected: `/compare` shows a score header card with Scan A score, Scan B score, and a delta badge that is green (▲) for positive delta, red (▼) for negative, neutral for zero
result: passed

### 7. Compare page — subscores tab shows all 6 pillar rows including zero-delta rows
expected: Subscores tab lists all 6 quantum-readiness pillars with their individual deltas, including rows where delta is ±0 (not hidden)
result: passed

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
