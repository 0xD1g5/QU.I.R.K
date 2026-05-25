---
status: partial
phase: 105-servicenow-ticketing
source: [105-VERIFICATION.md]
started: 2026-05-25T00:00:00Z
updated: 2026-05-25T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live ServiceNow incident creation
expected: With `[ticketing].servicenow` configured (https instance_url) and QUIRK_SNOW_USER/QUIRK_SNOW_PASSWORD env vars set, `quirk ticket create --backend servicenow` against a completed scan creates one ServiceNow incident per finding, each carrying QRAMM evidence in the description and the SHA256 fingerprint in the `correlation_id` field (verifiable in the ServiceNow UI).
why_human: Requires a real ServiceNow instance + credentials.
result: [pending]

### 2. Work-notes dedup on re-scan
expected: Re-running `quirk ticket create --backend servicenow` against the same findings does NOT open duplicate incidents — the existing incident (found via correlation_id) gets a `work_notes` journal entry appended (visible in the SNOW task UI; PATCH-not-POST distinction per KB0623936).
why_human: Requires a live ServiceNow instance to observe dedup + journal behavior.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
