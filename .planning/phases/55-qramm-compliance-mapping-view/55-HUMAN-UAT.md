---
status: partial
phase: 55-qramm-compliance-mapping-view
source: [55-VERIFICATION.md]
started: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Unscored state renders correctly
expected: Banner "Run and score a QRAMM assessment to see session-derived relevance scores." visible; all 12 practice area rows show em-dashes; Coverage Tiers legend and footnote visible; no "fully compliant" in DOM; no coverage % indicators
result: [pending]

### 2. Scored state renders correctly
expected: After scoring a session via Scorecard tab, CVI rows (1.1–1.3) show numeric relevance scores; SGRM/DPE/ITR rows (2.x–4.x) show 0.00; unscored banner NOT visible; session previously scored in DB shows correctly on fresh page load
result: [pending]

### 3. Keyboard accessibility
expected: Tab key reaches the Compliance Map trigger; focus ring is visible
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
