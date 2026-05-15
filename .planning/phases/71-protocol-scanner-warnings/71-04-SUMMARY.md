---
phase: 71-protocol-scanner-warnings
plan: 04
subsystem: scanners-protocol
tags: [hardening, dnssec, kerberos, saml, audit-2026-05-08]
status: complete
requires: []
provides: [PROTO-04]
affects:
  - quirk/scanner/dnssec_scanner.py
  - quirk/scanner/kerberos_scanner.py
  - quirk/scanner/saml_scanner.py
tech-stack:
  added: []
  patterns:
    - "Module-level logger + logger.warning idiom (post-Phase 70)"
    - "Algorithm-keyed minimum-length table for bounds checking (RFC-derived)"
    - "secrets.randbits for cryptographic nonces"
    - "Pre-parse byte-size cap on attacker-influenced JSON payloads"
key-files:
  created:
    - tests/test_identity_scanner_hardening.py
  modified:
    - quirk/scanner/dnssec_scanner.py
    - quirk/scanner/kerberos_scanner.py
    - quirk/scanner/saml_scanner.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "D-11 / WR-07: _DNSKEY_MIN_BYTES table with RFC-derived floors (RSA 5; ECDSA P-256 64; ECDSA P-384 96; Ed25519 32; Ed448 57)"
  - "D-08 / WR-08: Narrowed _probe_kdc_udp except to (socket.timeout, socket.error, OSError) for transport and (ValueError, TypeError, struct.error, IndexError, KeyError, PyAsn1Error) for decode — both branches log via logger.warning"
  - "D-09 / WR-09: AS-REQ nonce sourced from secrets.randbits(31), preserving the prior 31-bit field width"
  - "D-10 / WR-10: MAX_SAML_JSON_BYTES = 1_048_576 (1 MiB); oversized payloads bypass json.loads, log WARNING, and fall through to the XML-sniff path"
metrics:
  duration: "~25min"
  completed: 2026-05-15
---

# Phase 71 Plan 04: Identity Scanner Hardening Summary

One-liner: Hardens DNSSEC, Kerberos, and SAML scanners against malformed-input
DoS, weak randomness, and unbounded-payload memory exposure — closes audit
rows WR-07 / WR-08 / WR-09 / WR-10 under PROTO-04.

## What Was Built

### Task 1 — DNSSEC `_parse_dnskeys` length bound (WR-07)
- Added module-level `logger = logging.getLogger(__name__)`.
- Added `_DNSKEY_MIN_BYTES` constant keyed by algorithm number with RFC-derived
  minimum public-key byte lengths:
  - RSA family (algs 1, 5, 7, 8, 10): 5 bytes (RFC 4034 §2.1.5 encoding floor)
  - ECDSA P-256 (alg 13): 64 bytes (RFC 6605 §4)
  - ECDSA P-384 (alg 14): 96 bytes (RFC 6605 §4)
  - Ed25519 (alg 15): 32 bytes (RFC 8080 §3)
  - Ed448 (alg 16): 57 bytes (RFC 8080 §3)
- Added length guard before any `key_bytes[...]` subscript inside the per-record
  loop. Records shorter than the algorithm minimum log a WARNING and are skipped
  (graceful degradation per D-11 — DNSSEC scans no longer abort on truncation).
- Tightened the RSA RFC-3110 modulus-length parser with an additional bounds
  check on the multi-byte exponent-length header and on the modulus offset; on
  failure the parser now logs a WARNING and sets `key_size = None` (previously
  silently swallowed via bare except).
- Commit: `b34af3a`

### Task 2 — Kerberos decode logging + cryptographic nonce (WR-08, WR-09)
- Replaced the bare `except Exception` inside `_probe_kdc_udp` with two
  narrowed clauses (per D-08 boundary — WR-08 site only):
  - `(socket.timeout, socket.error, OSError)` — transport failures
  - `(ValueError, TypeError, struct.error, IndexError, KeyError, PyAsn1Error)` —
    malformed KDC response / decode failures
  - Both branches `logger.warning(...)` with the host and the exception before
    returning the existing `[]` sentinel.
- `_build_as_req` nonce now sourced from `secrets.randbits(31)` — cryptographic
  RNG (CSPRNG) per D-09. Comment cites WR-09. Preserves the prior 31-bit field
  width.
- Removed the unused `import random` (the nonce was its only consumer).
- Added a guarded `from pyasn1.error import PyAsn1Error` import alongside the
  existing impacket `try: ... except ImportError:` block so the narrowed except
  remains valid even when impacket/pyasn1 are absent.
- Commit: `67e556b`

### Task 3 — SAML JSON byte cap (WR-10)
- Added module-level `MAX_SAML_JSON_BYTES = 1_048_576` (1 MiB) and module-level
  `logger`.
- In `_classify_target`, computed the payload byte length BEFORE `json.loads`.
  Oversized payloads log a WARNING and skip the JSON parse, falling through to
  the XML-sniff path (same fallback shape a JSONDecodeError previously produced
  — return contract preserved).
- Replaced the surrounding bare `except` with a narrow
  `(JSONDecodeError, ValueError, UnicodeDecodeError, TypeError)` tuple. Demoted
  the JSON-parse-failure log to DEBUG because JSON-vs-XML sniffing routinely
  fails for legitimate SAML XML; the oversize-cap log remains at WARNING.
- Commit: `cec2193`

### Task 4 — Tests + audit-row closures
- New `tests/test_identity_scanner_hardening.py` (7 tests):
  - **DNSSEC:** truncated Ed25519 record skipped + WARNING logged; truncated
    ECDSA P-256 record skipped + WARNING logged; correctly-sized Ed25519
    record passes through unchanged (regression guard).
  - **Kerberos** (skipped when impacket absent, matching project precedent):
    `_probe_kdc_udp` patched-decoder failure logs WARNING and returns `[]`;
    `_build_as_req` nonce verified to come from `secrets.randbits` (sentinel
    propagates to AS-REQ nonce field) and `random.getrandbits` / `random.randint`
    asserted NOT called.
  - **SAML:** oversized payload (`MAX_SAML_JSON_BYTES + 1` bytes) bypasses
    `json.loads` (verified by patching `json.loads` to fail-on-call), logs
    WARNING, returns `"unknown"`; small valid OIDC JSON still classifies as
    `"oidc"` (regression guard).
- Local run: 5 passed, 2 skipped (impacket not installed in this env);
  CI environments with impacket installed will run all 7.
- Flipped `.planning/audit-2026-05-08/AUDIT-TASKS.md` rows WR-07, WR-08, WR-09,
  WR-10 from `— | [ ] open` to `Phase 71 | [x] closed`. No other rows touched.
- Commit: `5b498f6`

## Verification

- `python -m compileall quirk/scanner/dnssec_scanner.py quirk/scanner/kerberos_scanner.py quirk/scanner/saml_scanner.py` — clean.
- `pytest tests/test_identity_scanner_hardening.py` — 5 passed, 2 skipped
  (impacket-gated tests skip cleanly when the optional dep is absent).
- `pytest tests/test_dnssec_scanner.py tests/test_kerberos_scanner.py tests/test_saml_scanner.py` — pre-existing regression suites unaffected.
- `grep -cE "scanners-protocol/WR-(07|08|09|10).*Phase 71.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` → 4.

## Deviations from Plan

None — plan executed as written. Two minor planner-discretion choices:

- Picked `secrets.randbits(31)` over `int.from_bytes(secrets.token_bytes(4), "big")`
  to preserve the prior wire-format 31-bit field width (the original code used
  `random.getrandbits(31)`); both forms produce cryptographically strong nonces
  per D-09's "researcher's call" clause.
- Demoted the SAML JSON-parse-failure log to `logger.debug` (only the oversized-
  payload path logs at WARNING). Rationale: JSON-vs-XML sniffing legitimately
  fails for every well-formed SAML metadata document; WARNING-per-SAML-target
  would flood scanner logs. The WR-10 row asks for size-cap visibility and
  narrowed exception discipline, not WARNING-on-every-XML-payload.

## Threat Surface Scan

No new attacker-facing surface introduced. All three patches reduce surface:
T-71-08 (DNSSEC DoS), T-71-09 (Kerberos repudiation), T-71-10 (Kerberos replay
precomputation), T-71-11 (SAML memory DoS) all transition from `[ ] open` to
mitigated.

## Self-Check: PASSED

- quirk/scanner/dnssec_scanner.py — FOUND, contains `_DNSKEY_MIN_BYTES` + `len(key_bytes)` guard
- quirk/scanner/kerberos_scanner.py — FOUND, contains `secrets.randbits(31)` + narrowed except
- quirk/scanner/saml_scanner.py — FOUND, contains `MAX_SAML_JSON_BYTES`
- tests/test_identity_scanner_hardening.py — FOUND, 7 tests
- Commits: b34af3a, 67e556b, cec2193, 5b498f6 — all present in git log
- AUDIT-TASKS WR-07/08/09/10 — all show `Phase 71 | [x] closed`
