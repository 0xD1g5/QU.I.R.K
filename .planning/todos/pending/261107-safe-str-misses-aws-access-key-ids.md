---
type: todo
created: 2026-11-07
title: safe_str does not redact 20-character AWS access key ids (AKIA…)
source: Phase 235.3 plan 04 execution note
priority: low
area: quirk/util/safe_exc.py
status: pending
resolves_phase: null
owner: null
---

# safe_str does not redact 20-character AWS access key ids (AKIA…)

## Observed

`quirk/util/safe_exc.py::safe_str` redacts Vault tokens, URL userinfo, auth headers, API-key query params and
secret-shaped runs of 40+ base64 characters. An AWS access key id (`AKIA` / `ASIA` + 16 upper-case alphanumerics,
20 characters) matches none of these, so a botocore error message that quotes the key id passes through into scan
errors and logs. Found while 235.3 plan 04 routed S3/AWS credential failures through `safe_str`.

A key id is not a secret on its own, but it identifies the account and principal, and it does not belong in a
client deliverable.

## Fix sketch

Add `re.compile(r"\b(AKIA|ASIA|AGPA|AIDA|AROA|ANPA|ANVA|AIPA)[A-Z0-9]{16}\b")` to the redaction list, with a test
for a botocore `InvalidAccessKeyId` message.

## Feasibility & Effort

Small: one pattern plus one test. Check that the pattern does not over-redact report text (CBOM ids, hashes).

LEDGER row needed once `chore/master-ledger` merges (`.planning/LEDGER.md` is not on `v5282-open`).
