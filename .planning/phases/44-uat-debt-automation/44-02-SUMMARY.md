---
phase: 44-uat-debt-automation
plan: "02"
subsystem: tests
tags: [uat-traceability, kerberos, saml, udt-25, integration-tests]
dependency_graph:
  requires: []
  provides: [UAT-25-kerberos-traceability, UAT-25-saml-traceability]
  affects: [tests/test_kerberos_scanner.py, tests/test_saml_scanner.py]
tech_stack:
  added: []
  patterns: [docstring-traceability-annotation]
key_files:
  created: []
  modified:
    - tests/test_kerberos_scanner.py
    - tests/test_saml_scanner.py
decisions:
  - "Extended existing test docstrings in-place rather than creating new dedicated files (Claude's discretion per CONTEXT.md: existing-file extension chosen over new dedicated file)"
  - "UAT-25 annotations reference plan 44-06 as the closure record point in STATE.md"
metrics:
  duration: ~5 min
  completed: 2026-05-03
  tasks_completed: 2
  files_modified: 2
---

# Phase 44 Plan 02: UAT-25 Integration Test Traceability Annotation Summary

**One-liner:** Added explicit UAT-25 traceability docstring annotations to the existing Kerberos and SAML chaos-lab integration tests, closing the Phase 25 HUMAN-UAT audit trail.

## What Was Built

### No new test files created

Per CONTEXT.md discretion and plan objective: extended existing functions in-place. No new test functions, no new skip_registry entries, no new files.

### Task 1 — Kerberos UAT-25 annotation (tests/test_kerberos_scanner.py)

`test_samba_dc_integration` docstring expanded from:
```
KERB-05: Against a running Samba DC, scan returns RC4 etype 23 in results.
```
To:
```
UAT-25 / KERB-05: Phase 25 HUMAN-UAT closure — against the running `kerberos`
chaos lab profile (Samba DC), scan_kerberos_targets returns rc4-hmac (etype 23) in
cert_pubkey_alg results. This test is the automated equivalent of the Phase 25
HUMAN-UAT scenario and supersedes the manual run; closure recorded in
.planning/STATE.md Deferred Items (plan 44-06).
```

Decorators, function signature, and all assertions unchanged.

### Task 2 — SAML UAT-25 annotation (tests/test_saml_scanner.py)

`test_chaos_lab_integration` docstring expanded from:
```
SAML-06: Full integration test against SimpleSAMLphp chaos lab at localhost:8080.
```
To:
```
UAT-25 / SAML-06: Phase 25 HUMAN-UAT + VERIFICATION closure — against the
running `saml` chaos lab profile (SimpleSAMLphp at localhost:8080),
scan_saml_targets returns at least one CryptoEndpoint with cert_pubkey_size=1024
(the seeded weak RSA-1024 cert). This test is the automated equivalent of the
Phase 25 HUMAN-UAT and VERIFICATION scenarios; closure recorded in
.planning/STATE.md Deferred Items (plan 44-06).
```

Decorators, function signature, and all assertions unchanged.

## Operator Commands to Re-run Integration Tests

```bash
# Start required chaos lab profiles
cd quantum-chaos-enterprise-lab && ./lab.sh up kerberos saml

# Run both integration tests (from repo root)
QUIRK_KERBEROS_INTEGRATION=1 QUIRK_INTEGRATION_TESTS=1 \
  python -m pytest tests/test_kerberos_scanner.py::test_samba_dc_integration \
                   tests/test_saml_scanner.py::test_chaos_lab_integration -v
```

## Deviations from Plan

None — plan executed exactly as written. Docstring-only edits; no assertion or decorator modifications.

## Known Stubs

None — no data-flow stubs introduced.

## Threat Flags

None — docstrings reference public phase IDs only; no secrets or new network surfaces.

## Pre-existing Issues (out of scope)

- `tests/test_skip_registry.py::test_no_unregistered_skips` fails due to unregistered entries in `test_cbom_classifier_coverage.py:84` and `test_cbom_motion_golden.py:195`. This is a pre-existing failure unrelated to plan 44-02. Logged to deferred tracking per deviation rules.

## Note on STATE.md Phase 25 Row Closure

STATE.md Deferred Items rows for Phase 25 (uat_gap and verification_gap) are updated in plan 44-06 — not in this plan. The annotations in both test docstrings explicitly reference `plan 44-06` as the formal closure record point.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| tests/test_kerberos_scanner.py exists with UAT-25 annotation | FOUND |
| tests/test_saml_scanner.py exists with UAT-25 annotation | FOUND |
| Task 1 commit 84fcbfe | FOUND |
| Task 2 commit 72dd521 | FOUND |
