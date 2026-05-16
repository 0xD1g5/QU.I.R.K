---
phase: 59
plan: 02
subsystem: scanner, discovery, cbom
tags: [credential-leakage, security, safe_str, LEAK-02, tdd]
dependency_graph:
  requires: [quirk.util.safe_exc.safe_str]
  provides: [LEAK-02 regression tests, safe scan_error writes across all scanners]
  affects:
    - quirk/scanner/vault_connector.py
    - quirk/scanner/gcp_connector.py
    - quirk/scanner/tls_scanner.py
    - quirk/scanner/email_scanner.py
    - quirk/scanner/broker_scanner.py
    - quirk/scanner/ssh_scanner.py
    - quirk/discovery/tls_scanner.py
    - quirk/scanner/db_connector.py
    - quirk/cbom/writer.py
    - tests/test_credential_leakage.py
tech_stack:
  added: []
  patterns: [safe_str-via-import, two-step-variable-fix, exception-bridge-for-non-BaseException]
key_files:
  created:
    - tests/test_credential_leakage.py
  modified:
    - quirk/scanner/vault_connector.py
    - quirk/scanner/gcp_connector.py
    - quirk/scanner/tls_scanner.py
    - quirk/scanner/email_scanner.py
    - quirk/scanner/broker_scanner.py
    - quirk/scanner/ssh_scanner.py
    - quirk/discovery/tls_scanner.py
    - quirk/scanner/db_connector.py
    - quirk/cbom/writer.py
decisions:
  - "LEAK-02: all scan_error writes in quirk/scanner/, quirk/discovery/, quirk/cbom/ route through safe_str()"
  - "db_connector unified from type(exc).__name__ to safe_str(exc) — eliminates AST gate special-case predicate"
  - "cbom/writer err bridge: safe_str(Exception(str(err))) used for validate_str() return value (not a BaseException)"
  - "GCP two-step pattern fixed at variable assignment line, not at keyword-arg use site"
metrics:
  duration: "~3 minutes"
  completed: "2026-05-09"
  tasks: 2
  files: 10
---

# Phase 59 Plan 02: Mechanical safe_str Sweep — All Scanner Callsites Summary

## One-liner

Applied `safe_str()` mechanically to all 8 leaky `scan_error` callsites across 6 scanner files plus GCP two-step variable, db_connector unification, and cbom/writer.py — eliminating every credential leak path so Plan 03's AST gate finds zero violations.

## What Was Built

### Task 1: RED — Per-connector regression test corpus (4d38307)

Created `tests/test_credential_leakage.py` with 8 function-level tests:

| Test | Verifies |
|------|---------|
| `test_vault_scan_error_strips_token` | `s.` Vault token prefix triggers class-only return |
| `test_gcp_scan_error_strips_adc_path` | GCP ADC `.config/gcloud/` path triggers class-only return |
| `test_email_scan_error_strips_smtp_password` | SMTP `smtp://user:pass@host` triggers class-only return |
| `test_broker_scan_error_strips_redis_password` | Redis `redis://user:pass@host` triggers class-only return |
| `test_ssh_scan_error_class_name_only_for_creds` | `Authorization: Bearer ...` triggers class-only return |
| `test_tls_scan_error_benign_passthrough` | Benign `ConnectionRefusedError` passes through with message |
| `test_cbom_writer_scan_error_strips_creds` | CBOM validator PostgreSQL connection string triggers class-only |
| `test_all_callsites_import_safe_str` (x8 parametrized) | All 8 modified files contain `from quirk.util.safe_exc import safe_str` |

RED state confirmed: 7 behavior tests pass; 8 import-presence tests fail.

### Task 2: GREEN — Apply safe_str to all callsites (14bd4c0)

**Substitution table:**

| File | Callsite count | Pattern applied |
|------|---------------|-----------------|
| `quirk/scanner/vault_connector.py` | 2 scan_error + 2 logger.v | `safe_str(exc)` |
| `quirk/scanner/gcp_connector.py` | 1 (two-step var assignment) | `safe_str(exc)` at variable |
| `quirk/scanner/tls_scanner.py` | 1 | `f"{cat}: {safe_str(e)}"` |
| `quirk/scanner/email_scanner.py` | 2 (OSError + Exception) | `safe_str(e)` |
| `quirk/scanner/broker_scanner.py` | 1 | `safe_str(e)` |
| `quirk/scanner/ssh_scanner.py` | 1 | `f"SSH_ERROR: {safe_str(e)}"` |
| `quirk/discovery/tls_scanner.py` | 1 | `safe_str(e)` |
| `quirk/scanner/db_connector.py` | 2 (UNIFIED) | `safe_str(exc)` replaces `type(exc).__name__` |
| `quirk/cbom/writer.py` | 2 | line 78: `safe_str(Exception(str(err)))`; line 93: `safe_str(exc)` |

All 9 files received `from quirk.util.safe_exc import safe_str` import.

Verification: 23/23 tests pass (`tests/test_credential_leakage.py` 15 + `tests/test_safe_exc.py` 8).

## TDD Gate Compliance

- RED gate: `test(59-02)` commit 4d38307 — 7 behavior tests pass; 8 import-presence tests fail
- GREEN gate: `feat(59-02)` commit 14bd4c0 — all 23 tests pass

## Deviations from Plan

### Auto-fixed Issues

None — all substitutions executed exactly as specified in the plan action section.

**cbom/writer.py deviation note (within-plan scope):** The plan's action section noted that `err` from `validate_str()` is a validation error object (not a `BaseException`), and to use `safe_str(Exception(str(err)))` if a `TypeError` would surface. On inspection, `err` is a `jsonschema.ValidationError` (not a `BaseException`), so `safe_str(Exception(str(err)))` was used proactively. This is explicitly covered in the plan's action section under "inspect err's type" guidance.

## Pre-existing Test Failure (Out of Scope)

`tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success` fails before and after this plan's changes — confirmed by stash verification. The test mocks `urllib.request.urlopen` but the mock response's `read()` returns bytes that the function apparently processes differently than expected. This failure predates Plan 02 and is deferred.

## Known Stubs

None — all safe_str wrappings are fully implemented.

## Threat Flags

No new threat surface introduced. Plan closes:
- T-59-04 (vault_connector hvac error path)
- T-59-05 (gcp_connector ADC two-step var)
- T-59-06 (email/broker auth error path)
- T-59-07 (tls/ssh error categorization)
- T-59-08 (db_connector type(exc).__name__ pattern)
- T-59-14 (cbom/writer.py validator error path)

## Self-Check: PASSED

- All 10 files (9 modified + 1 created) exist on disk
- Commits 4d38307 (RED) and 14bd4c0 (GREEN) verified in git log
- 23/23 tests pass (`tests/test_credential_leakage.py` + `tests/test_safe_exc.py`)
- `python -m compileall quirk/scanner quirk/discovery quirk/cbom` exits 0
- All acceptance criteria grep gates pass (verified during Task 2 execution)
