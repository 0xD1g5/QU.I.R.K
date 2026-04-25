---
status: complete
phase: 25-identity-findings-accuracy
source: [25-01-SUMMARY.md, 25-02-SUMMARY.md, 25-03-SUMMARY.md]
started: 2026-04-24T23:45:00Z
updated: 2026-04-24T23:51:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Acceptance tests pass GREEN
expected: Run `python -m pytest tests/test_identity_findings_accuracy.py -v`. All 4 tests PASS: test_rs256_oidc_produces_identity_finding, test_rs384_oidc_produces_identity_finding, test_saml_endpoint_absent_from_tls_findings, test_pyproject_ldap3_in_identity_extras.
result: pass

### 2. No new test regressions
expected: Run `python -m pytest tests/ -v`. Result is 363+ passed, exactly 3 pre-existing failures (unchanged from before Phase 25), and 0 new failures introduced.
result: pass

### 3. ldap3 dependency in identity extras
expected: Run `grep '"ldap3>=2.9.1"' pyproject.toml`. Returns a match inside the `[project.optional-dependencies]` identity section alongside impacket.
result: pass

### 4. Expected results oracle — three identity sections present
expected: Open `quantum-chaos-enterprise-lab/expected_results_v3.md`. Three new Phase 25 sections are present: (a) DNSSEC bind9 profile with 4 zones including RSASHA1 CRITICAL and NSEC MEDIUM, (b) SAML/OIDC simpla-samlphp profile with RSA-1024 CRITICAL and SHA-1 URI HIGH, (c) Kerberos samba-dc profile with rc4-hmac HIGH and aes128-cts-hmac-sha1-96 HIGH.
result: pass

### 5. UI — SAML/OIDC findings appear in Identity tab (not TLS Findings tab)
expected: With the dashboard running and a scan that includes a SAML or RS256 OIDC endpoint, open the scan detail. Findings from those endpoints (source="saml") appear in the Identity Findings tab. The TLS Findings tab shows zero entries for those same endpoints.
result: skipped
reason: chaos lab not running

### 6. Live install — ldap3 resolves cleanly with pip
expected: In a clean venv, run `pip install -e ".[identity]"`. Install completes without conflicts; `pip show ldap3` confirms version >= 2.9.1 is installed alongside impacket.
result: pass

## Summary

total: 6
passed: 5
issues: 0
pending: 0
skipped: 1
blocked: 0

## Gaps

