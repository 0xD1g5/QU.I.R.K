---
status: partial
phase: 104-jira-ticketing
source: [104-VERIFICATION.md]
started: 2026-05-25T00:00:00Z
updated: 2026-05-25T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live Jira issue creation
expected: With `[ticketing]` configured (Cloud) and QUIRK_JIRA_USER/QUIRK_JIRA_TOKEN env vars set, `quirk ticket create` against a completed scan opens one Jira issue per finding, each carrying QRAMM evidence in the description and the SHA256 fingerprint as a label.
why_human: Requires a real Jira Cloud instance + API token.
result: [pending]

### 2. Idempotent dedup on re-scan
expected: Running `quirk ticket create` a second time against the same scan/findings adds a "rediscovery" comment to the existing issue (found via JQL label search) and creates ZERO duplicate issues.
why_human: Requires a live Jira instance to observe dedup behavior.
result: [pending]

### 3. Missing [tickets] extra graceful skip
expected: On an install WITHOUT the [tickets] extra (jira absent), `quirk ticket create` prints an advisory and exits cleanly (no ImportError/traceback).
why_human: Requires a minimal install environment without jira.
result: [pending]

### 4. Self-hosted Jira (token_auth / server) path
expected: With `auth_mode: server` and a self-hosted Jira base URL + PAT, issue creation works via the token_auth path; SSRF guard allows the configured host (allow_internal) without blocking.
why_human: Requires a self-hosted Jira Server/Data Center instance.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
