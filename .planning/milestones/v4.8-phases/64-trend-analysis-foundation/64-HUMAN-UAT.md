---
status: partial
phase: 64-trend-analysis-foundation
source: [64-VERIFICATION.md]
started: 2026-05-10
updated: 2026-05-10
---

## Current Test

[awaiting human testing]

## Tests

### 1. Multi-scan timeline chart renders on /trends
expected: Navigate to /trends with 2+ scans in DB; 7-line LineChart appears above the existing delta card; oldest scan on the left, newest on the right; hover tooltip shows full ISO timestamp + 7 score values + finding counts (HIGH/MED/LOW)
result: [pending]

### 2. Regression chip visible on dashboard home /
expected: With a scan that dropped score ≥5 pts vs previous (or added new HIGH/CRITICAL findings), navigate to /; RegressionAlertChip appears above the score gauge Card with correct message and "View trends →" link to /trends
result: [pending]

### 3. Per-session dismissal persists across page refresh
expected: Click × on the chip; chip disappears immediately without page reload; after page refresh chip stays hidden; localStorage.getItem('quirk.dismissed_regression.<session_ts>') returns "1"
result: [pending]

### 4. New scan with regression shows fresh chip after prior dismissal
expected: Dismiss chip for session S1; run a second regression scan producing session S2; navigate to /; a fresh chip appears for S2 (because the localStorage key encodes S1's timestamp, not S2's)
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
