---
status: partial
phase: 101-notification-fan-out-security-foundation
source: [101-VERIFICATION.md]
started: 2026-05-24T00:00:00Z
updated: 2026-05-24T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Slack live delivery end-to-end
expected: After a scheduled scan with new HIGH findings or score regression beyond the floor, a Slack message arrives in the configured channel with score band, delta, finding counts, and dashboard link.
why_human: Requires a live Slack workspace + incoming-webhook URL; unit tests use a mocked WebhookClient transport.
result: [pending]

### 2. Email live delivery end-to-end
expected: With SMTP env vars + QUIRK_CONFIG_PATH set, a triggering scheduled scan sends an email to all configured recipients with the drift summary.
why_human: Requires a live SMTP server or test mailbox; unit tests monkeypatch smtplib.
result: [pending]

### 3. Generic webhook live delivery with HMAC verification
expected: The configured webhook endpoint receives a POST with an X-QUIRK-Signature header; body contains only whitelisted aggregate fields (no host/port/protocol).
why_human: Requires a live HTTP endpoint; unit tests mock urlopen.
result: [pending]

### 4. End-to-end scheduler dispatch
expected: With QUIRK_CONFIG_PATH set and a notification config present, running a scheduled scan that produces new HIGH findings results in an IntegrationDelivery row and a delivery attempt.
why_human: Requires the full scheduler subprocess loop plus a live DB and config file; not exercised in the unit test suite.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
