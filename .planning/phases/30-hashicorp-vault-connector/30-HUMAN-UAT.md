---
status: partial
phase: 30-hashicorp-vault-connector
source: [30-VERIFICATION.md]
started: 2026-04-26T00:00:00Z
updated: 2026-04-26T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Vault Chaos Lab End-to-End — 5 Expected Findings

expected: Boot `docker compose --profile vault up -d` in `quantum-chaos-enterprise-lab/`, wait for `vault-30-seed` container to exit successfully, run quirk with `enable_vault: true`, `vault_addr: http://localhost:28200`, `vault_token: root`. Expected: exactly 5 `protocol="VAULT"` CryptoEndpoint rows: `transit/rsa-2048-classification` (severity=None), `transit/rsa-2048-exportable` (severity=MEDIUM), `PKI/pki` (severity=HIGH, RSA-2048 root CA), `auth/token` (severity=HIGH), `auth/userpass` (severity=MEDIUM). `dar_vault_weak_count` in evidence summary = 2 (HIGH-only: PKI + token). `data_at_rest` subscore lower than clean baseline. Tear down with `docker compose --profile vault down -v`.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
