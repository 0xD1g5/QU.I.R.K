---
phase: 73-cbom-intel-reports-warnings
plan: 02
subsystem: intelligence
tags: [intel-02, weak-crypto, evidence, ecdsa, saml, motion-broker, motion-email]
requires:
  - quirk/util/safe_exc.py (module-shape precedent)
provides:
  - quirk/util/weak_crypto.py (is_weak_cipher, is_legacy_tls_version, _WEAK_CIPHER_TOKENS)
affects:
  - quirk/intelligence/evidence.py (ECDSA, SAML, motion_broker, motion_email predicates)
tech-stack:
  added: []
  patterns:
    - "module-private frozenset + public predicate (mirrors safe_exc.py / nmap allowlist)"
key-files:
  created:
    - quirk/util/weak_crypto.py
    - tests/test_weak_crypto_helper.py
  modified:
    - quirk/intelligence/evidence.py
    - tests/test_intelligence_evidence.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "D-02 / D-02a: helpers public, _WEAK_CIPHER_TOKENS private"
  - "D-03: evidence.py ECDSA branch uses startswith((\"EC\", \"ECDSA\")) tuple"
  - "D-10: is_legacy_tls_version co-located in weak_crypto.py (no separate tls_versions.py)"
  - "RESEARCH C-8: CBC3 added to _WEAK_CIPHER_TOKENS for parity with tls_capabilities.py:103"
metrics:
  duration: "~25 min"
  completed: 2026-05-15
  tasks: 3
  files_changed: 5
  tests_added: 13
requirements: [INTEL-02]
---

# Phase 73 Plan 02: Weak-Crypto Predicate Unification Summary

**One-liner:** Centralized weak-cipher / legacy-TLS predicates in a new `quirk/util/weak_crypto.py` module and routed evidence.py SAML, motion_broker, and motion_email predicates through it; aligned ECDSA consumer to both EC/ECDSA emitter conventions; closed audit rows WR-03/04/10/11.

## What Was Built

### 1. `quirk/util/weak_crypto.py` (new, ~55 lines)

Mirrors `quirk/util/safe_exc.py` shape (Phase 59 precedent):

- `_WEAK_CIPHER_TOKENS: Final[frozenset[str]]` — module-private (D-02a). Contains the locked D-02 token set: `DES, 3DES, RC4, MD5, NULL, EXPORT, ANON, DES-CBC, IDEA, SHA1, SHA-1`, plus `CBC3` added per RESEARCH C-8 (parity with `quirk/scanner/tls_capabilities.py:103` weak_markers).
- `_LEGACY_TLS_VERSIONS: Final[frozenset[str]]` — `{TLSV1, TLSV1.0, TLSV1.1, SSLV3}`.
- `is_weak_cipher(cipher_or_label: str | None) -> bool` — guard None/empty → False; uppercase once; substring-membership over `_WEAK_CIPHER_TOKENS`.
- `is_legacy_tls_version(tls_version: str | None) -> bool` — guard None/empty → False; uppercase once; exact membership against `_LEGACY_TLS_VERSIONS`.

### 2. `quirk/intelligence/evidence.py` — four sites unified

| Site | Lines | Before | After | Audit |
|------|-------|--------|-------|-------|
| ECDSA detection | 132 | `startswith("ECDSA")` | `startswith(("EC", "ECDSA"))` | WR-04 / D-03 |
| SAML SHA-1 | 159 | `_saml_alg == "SHA1"` | `is_weak_cipher(_saml_alg)` | WR-10 / D-02 |
| motion_broker legacy TLS | 244 | inline `tls_v in {TLSV1, ...}` | `is_legacy_tls_version(tls_v)` | WR-03 / D-10 |
| motion_broker weak cipher | 250 | inline `any(s in cipher for s in ("3DES","RC4","DES-CBC"))` | `is_weak_cipher(cipher)` (structural TLS_RSA_WITH_ + ECDHE-less-AES-SHA clauses preserved inline per D-10) | WR-03 / D-10 |
| motion_email weak cipher | 268 | inline `any(s in cipher for s in ("3DES","RC4"))` | `is_weak_cipher(cipher)` (now covers full broker token set) | WR-11 / D-02 |

### 3. Tests

- `tests/test_weak_crypto_helper.py` — new module, **27 parametrized cases** (18 cipher cases + 8 TLS version cases + 1 symmetry).
- `tests/test_intelligence_evidence.py` — extended with **7 new tests**: ECDSA EC alias, ECDSA ECDSA alias, ED25519 negative, SAML SHA-1 mixed-case (`SHA-1`/`sha1`/`#rsa-sha1`), motion_broker TLSv1.1, motion_email DES-CBC now detected, email/broker parity over the token set.
- Total: 36 tests passing under `pytest tests/test_intelligence_evidence.py tests/test_weak_crypto_helper.py`.

### 4. Audit ledger flips

`.planning/audit-2026-05-08/AUDIT-TASKS.md` rows WR-03, WR-04, WR-10, WR-11 flipped to `Phase 73 | [x] closed` with per-row evidence pointing at the helper-import, the fix-site lines, and the gating tests.

## Commits

| Hash | Subject |
|------|---------|
| a86e0ec | test(73-02): add failing tests for weak_crypto helper (RED) |
| 1e2fdbd | feat(73-02): add quirk.util.weak_crypto helper (GREEN) |
| ac5cb0c | test(73-02): add failing tests for evidence.py weak-crypto unification (RED) |
| 4447c16 | feat(73-02): route evidence.py through weak_crypto + align ECDSA detection (GREEN) |
| 6f00abc | docs(73-02): flip WR-03, WR-04, WR-10, WR-11 audit rows to closed under Phase 73 |

## Deviations from Plan

**1. [Test-only correction during RED→GREEN handoff for Task 1]** — Initial RED test asserted `is_weak_cipher("ADH-AES128-SHA")` returns True via the "ANON" token, but `ADH` is the OpenSSL shorthand and does not literally contain `ANON`. Corrected the test corpus to use literal `ANON-DH-AES256-SHA` (token match) and `TLS_ECDH_anon_WITH_AES_128_CBC_SHA` (uppercases to contain `ANON`). The helper implementation matches the D-02 locked token set exactly — no behavioural deviation. Adjustment rolled into the GREEN commit alongside the implementation.

No other deviations. CONTEXT D-14 do-not-touch list honored:
- No changes to `quirk/util/safe_exc.py`.
- No changes to `quirk/scanner/tls_capabilities.py` (its `_is_weak_cipher` remains a separate scanner-local predicate; out of audit scope for INTEL-02).
- No changes to `cbom/builder.py`, `trends.py`, `technical.py`, or any TLS-scanner emitter.
- No changes to `SCORE_WEIGHTS` values or `_apply_weighted_impacts`.
- No new `quirk/util/tls_versions.py` module — `is_legacy_tls_version` lives in `weak_crypto.py` per D-10 / Deferred Ideas.

## Decisions Made

- **D-02a:** Set private (`_WEAK_CIPHER_TOKENS`), helpers public — matches CONTEXT recommended default.
- **RESEARCH C-8 / open question 3:** `CBC3` added to the frozenset (real OpenSSL cipher token `DES-CBC3-SHA`; tls_capabilities.py:103 weak_markers parity).
- **Locked D-10 boundary:** Only token-portion unified for motion_broker — structural `TLS_RSA_WITH_` and `(AES128-SHA / AES256-SHA without ECDHE/DHE)` clauses remain inline because they are shape predicates, not single-token presence checks.

## Verification

```
$ python -m compileall quirk/util/weak_crypto.py quirk/intelligence/evidence.py
Compiling 'quirk/util/weak_crypto.py'...
Compiling 'quirk/intelligence/evidence.py'...

$ pytest tests/test_intelligence_evidence.py tests/test_weak_crypto_helper.py tests/test_intelligence_scoring.py tests/test_intelligence_confidence.py tests/test_intelligence_roadmap.py
59 passed in 0.05s
```

Acceptance grep checks (Task 2):
- `from quirk.util.weak_crypto import is_weak_cipher, is_legacy_tls_version`: 1 hit ✓
- `startswith(("EC", "ECDSA"))`: 1 hit ✓
- `is_weak_cipher(_saml_alg)`: 1 hit ✓
- `is_legacy_tls_version(tls_v)`: 1 hit ✓
- `is_weak_cipher(cipher)`: 2 hits (broker + email) ✓
- `_saml_alg == "SHA1"` (non-comment): 0 hits ✓
- `startswith("ECDSA")` (non-comment): 0 hits ✓
- WR-03/04/10/11 closed under Phase 73: 4 rows ✓

## Threat Mitigation Status

| Threat ID | Disposition | Status |
|-----------|------------|--------|
| T-73-05 (missed weak signatures in SAML / email) | mitigate | ✓ closed — `is_weak_cipher` single source of truth |
| T-73-06 (false-negative on ECDSA-emitted-as-EC) | mitigate | ✓ closed — `startswith(("EC", "ECDSA"))` |
| T-73-07 (predicate drift between email and broker) | mitigate | ✓ closed — parity test enforces |

## Self-Check: PASSED

- `quirk/util/weak_crypto.py` exists ✓
- `quirk/intelligence/evidence.py` modified with all four fix sites ✓
- `tests/test_weak_crypto_helper.py` exists (27 tests passing) ✓
- `tests/test_intelligence_evidence.py` extended (7 new tests passing) ✓
- AUDIT-TASKS.md WR-03/04/10/11 closed under Phase 73 ✓
- Commits: a86e0ec, 1e2fdbd, ac5cb0c, 4447c16, 6f00abc (all present in `git log --oneline`) ✓
