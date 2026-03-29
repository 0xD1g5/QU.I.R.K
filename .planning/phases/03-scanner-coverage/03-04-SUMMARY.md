---
phase: 03-scanner-coverage
plan: "04"
subsystem: cbom-pipeline
tags: [cbom, classifier, builder, orchestrator, jwt, container, source, aws, azure]
dependency_graph:
  requires: [03-02, 03-03]
  provides: [cbom-pipeline-complete, scanner-orchestration-complete]
  affects: [run_scan, write_reports, build_cbom]
tech_stack:
  added: []
  patterns:
    - Multi-protocol branching in CBOM passes (explicit elif chain replaces binary SSH/TLS)
    - _extract_algo_from_rule_id for semgrep rule hint extraction
    - _normalize_cloud_key_spec for AWS KMS/Azure Key Vault key spec normalization
    - Guarded phase blocks with _phase_timer instrumentation for all five new scanners
key_files:
  created: []
  modified:
    - quirk/cbom/classifier.py
    - quirk/cbom/builder.py
    - run_scan.py
    - tests/test_cbom_classifier.py
    - tests/test_cbom_builder.py
decisions:
  - JWT algorithm entries map to (CryptoPrimitive.SIGNATURE, 0, bits) or (CryptoPrimitive.MAC, 0, bits) per RFC 7518; alg:none maps to (UNKNOWN, 0, 0)
  - CONTAINER and SOURCE endpoints produce no protocol component (not TLS/SSH network protocols)
  - AWS/AZURE endpoints get no protocol component; algorithms extracted from cloud_scan_json KeySpec/key_type
  - Pass 2 skips CONTAINER/SOURCE since they have no X.509 cert data; JWT/AWS/AZURE cert fields are optional
  - bom_ref is a BomRef object, not string; tests use str(c.bom_ref) for substring checks
metrics:
  duration_minutes: 10
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_modified: 5
---

# Phase 03 Plan 04: CBOM Pipeline Wiring Summary

CBOM pipeline wired to all five new scanner surfaces: JWT/JOSE algorithm classification via RFC 7518 table entries in classifier.py, explicit multi-protocol branching in builder.py passes (no TLS fallthrough), and guarded phase blocks in run_scan.py for jwt/container/source/aws/azure scanners.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend CBOM classifier and builder for new protocol types | 5b06120 | quirk/cbom/classifier.py, quirk/cbom/builder.py, tests/test_cbom_classifier.py, tests/test_cbom_builder.py |
| 2 | Wire all scanners into run_scan.py orchestrator | c94b689 | run_scan.py |

## Implementation Details

### Task 1: CBOM Classifier and Builder

**quirk/cbom/classifier.py** — Added 14 JWT/JOSE algorithm entries to `_ALGORITHM_TABLE`:
- RS256/RS384/RS512/PS256/PS384/PS512 → `(SIGNATURE, 0, 112)` (RSA-based, 112-bit classical)
- ES256/ES384/ES512 → `(SIGNATURE, 0, 128/192/256)` (ECDSA, P-curve bit strength)
- HS256/HS384/HS512 → `(MAC, 0, 128/192/256)` (HMAC)
- EdDSA → `(SIGNATURE, 0, 128)`
- none → `(UNKNOWN, 0, 0)` — critical vulnerability marker

**quirk/cbom/builder.py** — Restructured all three passes:
- Pass 1: `elif` chain replaces binary `is_ssh / else(TLS)`. JWT uses `cert_pubkey_alg`, CONTAINER is a no-op, SOURCE extracts hint from rule_id, AWS/AZURE parse `cloud_scan_json` for KeySpec/key_type.
- Pass 2: Guard extended from SSH-only skip to `("SSH", "CONTAINER", "SOURCE")` skip.
- Pass 3: Explicit `elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE"): continue` prevents TLS fallthrough (pitfall 6).
- Two new helper functions: `_extract_algo_from_rule_id()` and `_normalize_cloud_key_spec()`.

### Task 2: run_scan.py Orchestrator

Five guarded phase blocks added after the existing SSH phase block, each following the established pattern:
- `jwt_scanning` — enabled by `cfg.connectors.enable_jwt` + `jwt_targets`
- `container_scanning` — enabled by `cfg.connectors.enable_container` + `container_targets`
- `source_scanning` — enabled by `cfg.connectors.enable_source` + `source_targets`
- `aws_scanning` — enabled by `cfg.connectors.enable_aws`
- `azure_scanning` — enabled by `cfg.connectors.enable_azure`

Endpoint merge updated to include all five new endpoint lists before `evaluate_endpoints()`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed BomRef string containment check in test assertions**
- **Found during:** Task 1 GREEN phase
- **Issue:** Plan's test code used `"algorithm" in (c.bom_ref or "")` which fails because `c.bom_ref` is a `BomRef` object, not a string
- **Fix:** Changed all new test assertions to use `"algorithm" in str(c.bom_ref)`
- **Files modified:** tests/test_cbom_builder.py
- **Commit:** 5b06120 (included in Task 1 GREEN commit)

## Verification

- `pytest tests/test_cbom_classifier.py tests/test_cbom_builder.py -x -q` — 52 passed
- `pytest tests/ -x -q` — 139 passed, 0 failures
- `python3 -c "import run_scan"` — no ImportError
- All five new scanner phase blocks present with `_phase_timer` instrumentation
- No new protocol value falls through to TLS else clause in builder.py

## Known Stubs

None — all five scanner modules are implemented and produce real CryptoEndpoint data. The CBOM pipeline fully processes their output.

## Self-Check: PASSED

Files exist:
- FOUND: quirk/cbom/classifier.py (contains "rs256", "es256", "hs256", "none")
- FOUND: quirk/cbom/builder.py (contains ep.protocol == "JWT", CONTAINER, SOURCE, AWS/AZURE, helpers)
- FOUND: run_scan.py (contains all five imports and phase blocks)
- FOUND: tests/test_cbom_classifier.py (contains test_jwt_rs256, test_jwt_alg_none)
- FOUND: tests/test_cbom_builder.py (contains test_container_endpoint_no_tls_fallthrough)

Commits verified:
- FOUND: 58f3f83 (RED tests)
- FOUND: 5b06120 (Task 1 GREEN)
- FOUND: c94b689 (Task 2)
