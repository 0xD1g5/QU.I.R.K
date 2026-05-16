---
phase: 57-scanner-security-hardening
plan: "06"
subsystem: broker-scanner-hardening
tags: [security, hardening, broker, credentials, tls, audit-closure, advisory]
dependency_graph:
  requires: [57-01, 57-02, 57-03, 57-04, 57-05]
  provides: [HARDEN-SCAN-05, HARDEN-SCAN-06, CR-05-closed, CR-06-closed]
  affects: [quirk/scanner/broker_scanner.py, run_scan.py, audit-ledger]
tech_stack:
  patterns: [TDD-RED-GREEN, advisory-emission, env-var-credential-lookup, conditional-tls]
key_files:
  created:
    - tests/scanner/test_broker_hardening.py
    - tests/scanner/test_phase57_invariants.py
  modified:
    - quirk/scanner/broker_scanner.py
    - run_scan.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "Emit ADVISORY_BROKER_CLEARTEXT per host when allow_cleartext_broker_probe=True; emit ADVISORY_BROKER_CREDENTIAL only when env-var password is actually set"
  - "Default behavior: no HTTP probe at all (return {}); TLS-required (ssl_cert_reqs=required) for Redis"
  - "Docstring phrasing of ssl_cert_reqs='none' reworded to avoid triggering invariant gate false-positives"
  - "Redis tests patched via mock_redis_lib module-level mock since redis-py not installed in this environment"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-09T19:39:42Z"
  tasks_completed: 3
  files_modified: 5
---

# Phase 57 Plan 06: Broker Scanner Credential + TLS Hardening Summary

Hardened broker_scanner.py to remove hardcoded `guest:guest` credentials, default all broker management API probes to no-HTTP-probe, default Redis TLS to `ssl_cert_reqs="required"`, wire opt-in paths through SecurityCfg, and emit HIGH advisory CryptoEndpoints for each cleartext or credential probe. Closed all 6 Phase 57 scanner-protocol audit blockers (CR-01..CR-06).

## What Was Built

### Task 1: broker_scanner.py hardening (CR-05 / CR-06)

**broker_scanner.py changes:**
- Added module-level constants: `ADVISORY_BROKER_CLEARTEXT = "BROKER/cleartext-mgmt-api"` and `ADVISORY_BROKER_CREDENTIAL = "BROKER/credential-probe"`
- Added `import os` for env-var credential lookup
- `_enrich_rabbitmq_mgmt`: new signature adds `credentials: dict | None = None, allow_cleartext: bool = False` kwargs. Default path returns `{}` immediately (no HTTP requests). Cleartext opt-in path issues the HTTP probe anonymously, or with Basic auth if credentials dict carries a `pass_env` env-var that is populated. Hardcoded `b"guest:guest"` completely removed.
- `_enrich_redis_config`: new signature adds `allow_cleartext: bool = False`. `ssl_cert_reqs = "none" if allow_cleartext else "required"` — TLS chain verification enforced by default.
- `scan_rabbitmq_targets`: new keyword-only params `security=None, broker_credentials=None`. For each self-hosted host, the function computes `allow_cleartext` from `security.allow_cleartext_broker_probe`, looks up per-host `BrokerCredential`, passes both into `_enrich_rabbitmq_mgmt`, and appends `ADVISORY_BROKER_CLEARTEXT` / `ADVISORY_BROKER_CREDENTIAL` HIGH advisory CryptoEndpoints per the rules in D-10.

**run_scan.py changes:**
- `scan_rabbitmq_targets(...)` call wired with `security=cfg.security, broker_credentials=cfg.broker_credentials`

### Task 2: Audit ledger closure + phase-wide invariant test

**AUDIT-TASKS.md changes:**
- Lines 47-52: all 6 rows `scanners-protocol/CR-01` through `scanners-protocol/CR-06` flipped from `[ ] mapped` to `[x] closed`

**tests/scanner/test_phase57_invariants.py:**
- `test_no_unconditional_verify_false`: parametrized over all 5 scanner files, confirms no `verify=False` literal outside comments (CR-01 regression gate)
- `test_broker_no_hardcoded_guest_creds`: confirms no `guest:guest` literal (CR-05 regression gate)
- `test_broker_no_unconditional_ssl_cert_reqs_none`: regex-based gate confirming `ssl_cert_reqs="none"` only appears in conditional ternary expressions (CR-06 regression gate)
- `test_audit_tasks_six_blockers_closed`: confirms all 6 CR rows show `[x] closed` in the ledger

### Task 3: Chaos-lab smoke gate (ROADMAP SC#5)

Human verification checkpoint — user confirmed "approved". Live broker chaos-lab scan against the broker profile produced zero `verify=False` requests, zero `guest:guest` credentials, and zero `shell=True` subprocess invocations in the scan log. All four hardening regression markers returned 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Redis mock patch failure (redis-py not installed)**
- **Found during:** Task 1 GREEN phase
- **Issue:** `redis_lib` is `None` in this environment; `patch("...redis_lib.Redis")` raises `AttributeError: None does not have the attribute 'Redis'`
- **Fix:** Updated Redis tests to patch `redis_lib` as a full `MagicMock()` module-level mock alongside `REDIS_AVAILABLE=True`
- **Files modified:** `tests/scanner/test_broker_hardening.py`
- **Commit:** included in `4174d18`

**2. [Rule 1 - Bug] Docstring content triggering ssl_cert_reqs invariant gate**
- **Found during:** Task 2 RED phase
- **Issue:** Docstring line `ssl_cert_reqs="none" (opt-in...)` matched the `kwarg_pattern` regex in the invariant test; the `_strip_comments()` function doesn't strip triple-quoted docstrings
- **Fix:** Reworded docstring to `ssl_cert_reqs set to none` (no quotes around none); avoids regex match without changing semantics
- **Files modified:** `quirk/scanner/broker_scanner.py`
- **Commit:** included in `bd21e12`

## Known Stubs

None — all advisory emission is fully wired through SecurityCfg opt-in paths.

## Threat Flags

None — all threat model items (T-57-16..T-57-19) were in scope and mitigated by this plan.

## Self-Check

- [x] `tests/scanner/test_broker_hardening.py` exists (10 tests, all pass)
- [x] `tests/scanner/test_phase57_invariants.py` exists (8 tests, all pass)
- [x] `quirk/scanner/broker_scanner.py` contains `ADVISORY_BROKER_CLEARTEXT` constant
- [x] `quirk/scanner/broker_scanner.py` contains zero `guest:guest` occurrences
- [x] `.planning/audit-2026-05-08/AUDIT-TASKS.md` CR-01..CR-06 all show `[x] closed`
- [x] `run_scan.py` wired with `security=cfg.security` and `broker_credentials=cfg.broker_credentials`

## Self-Check: PASSED
