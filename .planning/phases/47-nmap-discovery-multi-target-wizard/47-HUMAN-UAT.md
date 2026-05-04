---
status: partial
phase: 47-nmap-discovery-multi-target-wizard
source: [47-VERIFICATION.md]
started: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Wizard CSV targets flow
expected: Entering `host1,host2,host3` at the wizard target prompt routes all three hosts correctly — scan runs against all three without error
result: [pending]

### 2. Wizard @file targets flow
expected: Entering `@/tmp/targets.txt` at the wizard target prompt loads hosts from the file; comment lines (`#`) and blank lines are silently ignored
result: [pending]

### 3. Wizard nmap y/N fires exactly once (D-06)
expected: A single global "Run nmap port discovery first? [y/N]" prompt appears once in the wizard — not per-target, not missing, exactly one prompt
result: [pending]

### 4. TTY probe-budget confirm prompt
expected: When targets × ports exceeds 10,000, a y/N confirm prompt fires before nmap runs; answering N aborts cleanly with a log message
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
