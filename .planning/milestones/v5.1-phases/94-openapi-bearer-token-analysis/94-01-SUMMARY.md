---
phase: 94-openapi-bearer-token-analysis
plan: "01"
subsystem: cli/cbom/scoring/evidence
tags: [jwt, bearer-token, analyze-token, cbom, scoring, evidence, token-01, token-02, token-03, score-01]
dependency_graph:
  requires: []
  provides:
    - quirk.cli.analyze_token_cmd.run_analyze_token
    - CBOM BEARER_TOKEN classification branch
    - SCORE_WEIGHTS 293.0/39 entries
    - evidence bearer_token_weak_alg_count/openapi_plaintext_server_count
  affects:
    - quirk/cbom/builder.py (Pass-1/2/3 BEARER_TOKEN)
    - quirk/intelligence/scoring.py (agility_weak_jwt_alg_ratio/agility_openapi_plaintext_ratio)
    - quirk/intelligence/evidence.py (_PROTOCOL_KEYS, counters, ratios)
    - run_scan.py (analyze-token intercept)
tech_stack:
  added:
    - quirk/cli/analyze_token_cmd.py (new module)
    - tests/test_analyze_token.py (new test file)
  patterns:
    - TDD RED/GREEN per task
    - Phase 93 reference-not-secret model (@file/stdin token input)
    - PyJWT unverified decode (get_unverified_header + decode(verify_signature=False))
    - SCORE_WEIGHTS invariant bump pattern (sum+count both updated atomically)
key_files:
  created:
    - quirk/cli/analyze_token_cmd.py
    - tests/test_analyze_token.py
  modified:
    - run_scan.py (analyze-token argv intercept)
    - quirk/cbom/builder.py (BEARER_TOKEN Pass-1/2/3)
    - quirk/intelligence/scoring.py (+2 weights, +10.0 sum)
    - quirk/intelligence/evidence.py (BEARER_TOKEN/OPENAPI protocol keys + counters)
    - tests/test_score_weights_invariant.py (sum 283.0->293.0, count 37->39)
decisions:
  - alg:none detected via header["alg"].lower()=="none" (dict key, not raw string search) per T-94-01
  - algorithms=[alg] always passed to jwt.decode() per PyJWT>=2.4 hardening (T-94-04)
  - BEARER_TOKEN added to Pass-2 skip (no X.509 cert) and Pass-3 skip (no ProtocolProperties)
  - bearer_token_weak_alg_count increments on all non-none algs (all currently quantum-vulnerable)
  - openapi_plaintext_server_count scaffolded here; populated by Plan 94-02
metrics:
  duration: ~45 minutes
  completed: 2026-05-23
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 5
---

# Phase 94 Plan 01: Analyze-Token Command + CBOM Bearer Classification Summary

**One-liner:** `quirk analyze-token` JWT/bearer decoder with alg:none CRITICAL detection, CBOM `declared_algorithm (unverified)` classification, and SCORE_WEIGHTS +10.0 to 293.0/39 entries via two new agility signals.

## What Was Built

### Task 1: analyze-token command + run_scan intercept (TOKEN-01, TOKEN-03)

Created `quirk/cli/analyze_token_cmd.py` implementing `run_analyze_token(argv)`:

- **Input resolution:** positional, `@file`, or stdin (Phase 93 reference-not-secret model); `@file`/stdin avoid argv/shell-history leakage
- **JWT decode:** `jwt.get_unverified_header()` + `jwt.decode(verify_signature=False, verify_exp=False, algorithms=[alg])` — always passes `algorithms` per PyJWT>=2.4 hardening (T-94-04)
- **alg:none detection:** `header["alg"].lower() == "none"` on the decoded header dict key — not raw string search — per T-94-01; prints CRITICAL banner + exits 1
- **Opaque token handling:** `jwt.exceptions.DecodeError` caught → INFO "opaque token" message + exits 0
- **Output:** human-readable by default; `--json` flag emits `{alg, is_alg_none, expired, exp, nist_level, quantum_safety}` dict
- **Security:** `safe_str(exc)` wraps all exceptions; raw token never echoed to stdout/logs; no DB writes anywhere (T-94-02)

Added three-line `analyze-token` intercept to `run_scan.py` before the `errors` intercept, delegating to `run_analyze_token`.

**Tests (TDD RED→GREEN):**
- `test_decode_rs256_token`: RS256 JWT exits 0, reports algorithm and quantum safety
- `test_json_flag`: `--json` emits dict with all 5 required keys
- `test_opaque_token_graceful`: opaque string exits 0 with "opaque" in output
- `test_alg_none_critical`: all 4 variants (none/NONE/None/NonE) exit 1 with CRITICAL in output
- `test_token_value_not_echoed_rs256` + `test_token_value_not_echoed_none`: first JWT segment absent from stdout

### Task 2: CBOM BEARER_TOKEN branch + SCORE_WEIGHTS +10.0 + evidence counters (TOKEN-02, SCORE-01)

**quirk/cbom/builder.py:**
- Pass-1: `elif ep.protocol == "BEARER_TOKEN":` branch — calls `_register_algorithm(ep.cert_pubkey_alg)` when set; appends `"bearer-token-declared-algorithm"` coverage note (hardcoded literal per T-88-03)
- Pass-2: BEARER_TOKEN added to skip tuple (no X.509 cert components for bearer tokens)
- Pass-3: BEARER_TOKEN added to skip tuple alongside JWT (no ProtocolProperties component)
- T-94-03: component never marked enforced; coverage note label explicitly `declared_algorithm (unverified)`

**quirk/intelligence/scoring.py:**
- +2 entries to SCORE_WEIGHTS: `agility_weak_jwt_alg_ratio: 6.0`, `agility_openapi_plaintext_ratio: 4.0`
- Sum: 283.0 → 293.0 (+10.0). Count: 37 → 39 (+2)
- Two new `agility_impacts` tuples consume bearer/openapi evidence counters via `-_ratio() * w[...]` pattern

**quirk/intelligence/evidence.py:**
- `_PROTOCOL_KEYS`: added `"BEARER_TOKEN"` and `"OPENAPI"`
- `bearer_token_weak_alg_count`: increments when `proto == "BEARER_TOKEN"` and `cert_pubkey_alg` is set and not "none"
- `openapi_plaintext_server_count`: increments when `proto == "OPENAPI"` and service_detail indicates plaintext (populated by Plan 94-02)
- Return dict: both raw counts + ratio keys `agility_weak_jwt_alg_ratio` / `agility_openapi_plaintext_ratio`

**Tests (TDD RED→GREEN):**
- `test_cbom_bearer_classification`: RS256 BEARER_TOKEN endpoint produces CBOM algorithm component
- `test_cbom_bearer_coverage_note`: coverage note `bearer-token-declared-algorithm` in root component
- `test_cbom_bearer_never_enforced`: components not flagged enforced
- `test_score_weights_sum_invariant`: sum == 293.0
- `test_score_weights_count_invariant`: len == 39

## Commits

| Hash | Type | Description |
|------|------|-------------|
| d555079 | test | RED: failing tests for analyze-token + CBOM bearer |
| b514b36 | feat | GREEN: analyze-token command + run_scan intercept |
| 867a296 | test | RED: update invariant test + fix FakeEndpoint attrs |
| e657400 | feat | GREEN: CBOM BEARER_TOKEN + SCORE_WEIGHTS + evidence |

## Deviations from Plan

None — plan executed exactly as written.

The FakeEndpoint in tests required additional attributes (`cert_subject`, `cert_issuer`, `cert_not_before`, `cert_serial`, `cert_fingerprint_sha256`, `tls_supported_ciphers_sample`) because `build_cbom()` Pass-2 accesses them for all endpoints before protocol-specific skips. This is expected — the BEARER_TOKEN addition to the Pass-2 skip tuple now prevents that path for bearer endpoints. Fixed inline as part of the RED phase.

## Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-94-01: alg:none spoofing | `header["alg"].lower()=="none"` on header dict; CRITICAL + exit 1 | Done |
| T-94-02: token in stdout/logs | `safe_str(exc)` wraps exceptions; token absent from stdout (test asserts) | Done |
| T-94-03: CBOM bearer enforced | Coverage note only; never marked enforced | Done |
| T-94-04: PyJWT without algorithms | `algorithms=[alg]` always passed | Done |

## Known Stubs

- `openapi_plaintext_server_count`: counter scaffolded in evidence.py; populated by Plan 94-02 (OpenAPI scanner). Currently always 0. Intentional — SCORE-01 requires the weight entry to exist before Plan 94-02 can run in the same phase.

## Self-Check: PASSED

Files created/modified exist:
- quirk/cli/analyze_token_cmd.py: FOUND
- tests/test_analyze_token.py: FOUND
- run_scan.py (analyze-token intercept): FOUND
- quirk/cbom/builder.py (BEARER_TOKEN): FOUND
- quirk/intelligence/scoring.py (293.0/39): FOUND
- quirk/intelligence/evidence.py (bearer counters): FOUND
- tests/test_score_weights_invariant.py (293.0/39): FOUND

Commits verified:
- d555079: test(94-01): FOUND
- b514b36: feat(94-01): implement analyze-token: FOUND
- 867a296: test(94-01): update invariant test: FOUND
- e657400: feat(94-01): CBOM BEARER_TOKEN + SCORE_WEIGHTS: FOUND

All 14 tests in test_analyze_token.py + test_score_weights_invariant.py: PASSED
