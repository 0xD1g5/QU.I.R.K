---
status: partial
phase: 103-siem-export
source: [103-VERIFICATION.md]
started: 2026-05-25T00:00:00Z
updated: 2026-05-25T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live syslog/CEF delivery
expected: Run `quirk export --siem` against a local receiver (e.g. `nc -ul 514`) and confirm CEF events arrive with `<12>CEF:0|QUIRK|scanner|...` prefix, correct `dhost=`/`dpt=`/`cs1=`/`cs2=`/`msg=` extension fields, severity mapped to 10/8/5/3, and NO cert PEM / SANs / compliance data in the payload. One event per finding.
why_human: Automated tests monkeypatch the socket send; the actual datagram bytes over a real socket to a real collector need manual confirmation.
result: [pending]

### 2. After-scan scheduler hook
expected: With `siem.export_after_scan: true` and a `[siem]` target configured, trigger a scheduled scan and confirm CEF events auto-arrive at the receiver; confirm `scheduled_runs.status='completed'` even when the receiver is unreachable (failure isolation — scan record uncorrupted).
why_human: Requires the full scheduler subprocess loop + a live receiver.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
