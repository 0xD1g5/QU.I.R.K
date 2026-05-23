---
phase: 96-active-rest-fuzzing
plan: "02"
subsystem: scanner/fuzzer + tests
tags: [rest-fuzzer, schemathesis, dispatch-loop, crypto-probes, alg-confusion, tdd, fuzz-01, fuzz-02, fuzz-04]
dependency_graph:
  requires: [phase-96-01-gate-layer, phase-93-ephemeral-creds, phase-94-openapi-scanner]
  provides: [quirk.scanner.rest_fuzzer.run_fuzz_scan, probe_hsts, _probe_tls_downgrade, _probe_cipher_weak, _forge_hs256_token, _fetch_jwks_public_key_pem]
  affects: [quirk/scanner/rest_fuzzer.py, tests/test_rest_fuzzer_probes.py]
tech_stack:
  added: []
  patterns: [TDD RED/GREEN, schemathesis programmatic dispatch, TokenBucket rate limiting, HMAC-SHA256 manual JWT forge, stdlib ssl TLS probe]
key_files:
  created:
    - tests/test_rest_fuzzer_probes.py
  modified:
    - quirk/scanner/rest_fuzzer.py
decisions:
  - "PyJWT 2.x security check rejects PEM bytes as HMAC secret: manually build HS256 JWT using stdlib hmac/hashlib with the PEM bytes as raw HMAC key — this is the authentic alg-confusion attack vector"
  - "HTTP-only cred probe fires only for spec-declared http:// endpoints; never downgrades https:// URLs (Open Question 2 resolution)"
  - "_forge_hs256_token returns None for non-RS256 tokens (HS256, alg:none, opaque) — probe is RS256-specific"
  - "alg-confusion probe dispatches forged token at each dispatched endpoint URL when a public key is available; single INFO probe_skipped emitted when no key is found"
metrics:
  duration: "18 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  files_changed: 2
  commits: 3
---

# Phase 96 Plan 02: Fuzzer core — dispatch loop + crypto probes + alg-confusion (TDD) Summary

GET-only schemathesis dispatch loop with six guardrails, TLS/cipher/HSTS/http-cred crypto probes,
and JWT RS256→HS256 alg-confusion forge emitting CRITICAL/HIGH/INFO REST_FUZZ findings.

## What Was Built

### Task 1: Dispatch loop with five guardrails + TLS/cipher/HSTS/http-cred probes

Extended `quirk/scanner/rest_fuzzer.py` (Plan 01 gate surface) with the full `run_fuzz_scan()` function:

**`run_fuzz_scan(spec_dict, base_url, cfg, cred_ctx, budget, prompt_fn, is_tty, run_alg_confusion, _session)`**

Six guardrails enforced:
1. **GET-only**: `schemathesis.openapi.from_dict(spec_dict).include(method="GET").get_all_operations()` — POST/PUT/DELETE ops never enumerated
2. **Hard budget**: `_resolve_budget()` caps at MAX_FUZZ_BUDGET=500; budget_used increments ONLY after `session.request()` returns (Pitfall 3)
3. **Rate cap**: `TokenBucket(rate_per_sec=5.0)`.acquire() before each dispatch
4. **CONFIRM gate**: `confirm_fuzz_gate()` is the FIRST executable statement — no I/O precedes it (Pitfall 1)
5. **Scope gate**: `validate_external_url()` called before every `session.request()`; rejected URLs skipped without consuming budget (T-96-04)
6. **5xx cascade**: consecutive_5xx tracker breaks loop at 3 consecutive 5xx responses (T-96-05)

Schemathesis iteration uses `isinstance(result, _SchemaOk)` (Anti-Pattern: never `result.is_ok()` or `as_requests_kwargs`).

**Crypto probes:**
- `probe_hsts(response_headers)` — True when `strict-transport-security` absent
- `_probe_tls_downgrade(host, port)` — stdlib ssl attempt with TLSv1.1/TLSv1.0; DeprecationWarning suppressed (Pitfall 7)
- `_probe_cipher_weak(host, port)` — stdlib ssl with weak cipher string (RC4/NULL/EXPORT/DES/3DES)
- HTTP-only credential probe — fires ONLY for spec-declared `http://` endpoints (never https→http downgrade, Open Question 2)

All findings: `protocol="REST_FUZZ"`, `severity="HIGH"`.

**Graceful degradation**: when `SCHEMATHESIS_AVAILABLE=False`, returns single `missing_extra` CryptoEndpoint (follows openapi_scanner analog).

**Acceptance verified:**
- `grep -c "result.is_ok()\|as_requests_kwargs\|jku" quirk/scanner/rest_fuzzer.py` → 0
- `grep -c "isinstance(result, _SchemaOk)" quirk/scanner/rest_fuzzer.py` → 1
- `grep -c "validate_external_url" quirk/scanner/rest_fuzzer.py` → 7
- `probe_hsts({})` → True; `probe_hsts({"strict-transport-security": "max-age=1"})` → False
- `python -m compileall quirk/scanner/rest_fuzzer.py` → exit 0
- All 17 probe tests pass

### Task 2: JWT RS256→HS256 alg-confusion probe

**`_forge_hs256_token(bearer_token, public_key_pem)`**

- Reads unverified header; returns None unless `alg.upper() == "RS256"`
- Decodes claims with `verify_signature=False, verify_exp=False`
- Manually builds HS256 JWT using `stdlib hmac/hashlib` with PEM bytes as raw HMAC key
  (PyJWT 2.x security check rejects PEM bytes via `jwt.encode()` — manual build is the authentic attack vector)
- Returns forged token as bytes; None for non-RS256 (HS256, alg:none, opaque)

**`_fetch_jwks_public_key_pem(base_url, session, allow_internal)`**

- Fetches `{base_url}/.well-known/jwks.json` ONLY — no iss/jku claim following (T-96-08)
- Subject to `validate_external_url` (still scope-gated)
- Extracts first RSA/RS256 key entry → `cryptography` RSAPublicNumbers → PEM bytes
- Returns None on any failure (connection refused, non-200, malformed JWKS)

**Alg-confusion probe in `run_fuzz_scan`:**

- Pre-check before dispatch loop: fetch JWKS once, emit `INFO probe_skipped` and skip if no public key
- For each dispatched endpoint (when `run_alg_confusion=True` and bearer is RS256):
  - Forge HS256 token; dispatch with `Authorization: Bearer <forged>`
  - Scope-gate the alg-confusion request URL (T-96-04)
  - 2xx response → `CRITICAL` finding with `service_detail="alg_confusion"`
  - No raw bearer or forged token in any `CryptoEndpoint` field (T-96-06)

**Acceptance verified:**
- `_forge_hs256_token(rs256_token, pub_pem)` → bytes; decoded header `alg == "HS256"`; claims match source
- `_forge_hs256_token(hs256_token, ...)` → None; `_forge_hs256_token(alg_none_token, ...)` → None
- `run_alg_confusion=True` + 2xx → `severity="CRITICAL"`, `service_detail="alg_confusion"`
- No public key → `severity="INFO"`, `service_detail="probe_skipped"`, no forged request
- `grep -c "jku" quirk/scanner/rest_fuzzer.py` → 0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PyJWT 2.x rejects PEM bytes as HMAC secret via jwt.encode()**
- **Found during:** Task 2, GREEN phase — `_forge_hs256_token` returned None because PyJWT 2.12.1 raises `InvalidKeyError: The specified key is an asymmetric key or x509 certificate and should not be used as an HMAC secret`
- **Issue:** PATTERNS.md Pattern 6 shows `jwt.encode(claims, pub_key_pem, algorithm='HS256')` but PyJWT 2.x added a security check blocking this exact usage
- **Fix:** Manually build the JWT using `stdlib hmac.new(public_key_pem, signing_input, hashlib.sha256)` with the PEM bytes as the raw HMAC-SHA256 key. This is the authentic attack vector (exactly what the original alg-confusion CVE exploits). The RESEARCH.md note was correct about the approach but did not document the PyJWT version guard.
- **Files modified:** `quirk/scanner/rest_fuzzer.py`
- **Commit:** 5e98159

## TDD Gate Compliance

- RED gate: `test(96-02)` commit b0e2b44 — 17 failing tests written before implementation
- GREEN gate: `feat(96-02)` commit 5e98159 — all 17 tests pass
- REFACTOR: none needed (clean implementation; jku comment cleanup was part of the GREEN commit)

## Known Stubs

None — all probes are implemented. The alg-confusion probe has a graceful INFO path when no public key is available (not a stub; this is the specified behavior per Open Question 1 resolution).

## Threat Flags

None — all new network endpoints and auth paths are covered by the plan's threat model (T-96-04 through T-96-08). The alg-confusion probe JWKS fetch is the only new network endpoint introduced; it is scope-gated per T-96-08 and never follows iss/jku claims.

## Self-Check: PASSED

- `quirk/scanner/rest_fuzzer.py`: FOUND (run_fuzz_scan, probe_hsts, _probe_tls_downgrade, _forge_hs256_token)
- `tests/test_rest_fuzzer_probes.py`: FOUND (17 tests)
- Commit b0e2b44 (RED): FOUND
- Commit 5e98159 (GREEN): FOUND
- grep result.is_ok() == 0: CONFIRMED
- grep as_requests_kwargs == 0: CONFIRMED
- grep jku == 0: CONFIRMED
- grep validate_external_url >= 1: CONFIRMED (7 occurrences)
- 39 tests passing (gate + probe): CONFIRMED
- compileall exits 0: CONFIRMED
