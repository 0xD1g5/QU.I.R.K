---
status: partial
phase: 25-identity-findings-accuracy
source: [25-VERIFICATION.md]
started: 2026-04-24T23:08:10Z
updated: 2026-04-24T23:08:10Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. IDENT-02 — UI tab routing (Identity vs TLS Findings tab)
expected: With the chaos lab running (simpla-samlphp or any SAML/OIDC scan), findings from SAML/OIDC endpoints appear in the Identity tab (source="saml") and are absent from the TLS Findings tab in the dashboard UI.
result: [pending]

### 2. INFRA-03 — Live install + Kerberos enumeration
expected: `pip install -e ".[identity]"` in a clean environment installs ldap3>=2.9.1 without conflicts; a scan against samba-dc chaos lab produces Kerberos findings (rc4-hmac HIGH) that are no longer always-inert.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
