---
phase: 48-rich-finding-context
plan: 1
subsystem: risk-engine
tags: [phase-48, risk-engine, finding-schema, pqc-terminology, FIPS-203, FIPS-204, FIPS-205, NIST-IR-8547]
requires:
  - phase: 46
    plan: 4
    provides: "TLS finding branches (RSA/ECDSA/self-signed/untrusted-CA) anchored on chain_verified column"
provides:
  - "_build_finding chokepoint helper enforcing non-empty description + recommendation"
  - "NIST_IR_8547_DEPRECATION canonical constant"
  - "Rich plain-English description on every emitted finding"
  - "FIPS-only recommendation strings (FIPS 203/204/205) on quantum-vulnerable findings"
  - "Dedup-safe deterministic deprecation-phrase append (T-48-03 mitigation)"
affects:
  - "Plan 48-02 (consumer wiring): renderer/dashboard/JSON now receive description field on every finding"
  - "Plan 48-03 (CI gate): risk_engine.py contains zero forbidden substrings — gate is pre-satisfied for the producer-side file"
tech-stack:
  added: []
  patterns:
    - "_build_finding kw-only-arg chokepoint pattern"
    - "deterministic suffix append preserves dedup-key invariants"
    - "module-level canonical constant for cross-phase regulatory traceability"
key-files:
  created: []
  modified:
    - quirk/engine/risk_engine.py
    - tests/test_risk_engine.py
decisions:
  - "[48-01] _build_finding raises ValueError on empty description / empty recommendation — fail-fast at construction (D-02)"
  - "[48-01] NIST_IR_8547_DEPRECATION appended to recommendation (not description) — keeps risk-explanation/migration-deadline separate (D-06)"
  - "[48-01] Suffix append is deterministic (single constant, always same separator) — preserves _dedupe_findings tuple equality (T-48-03)"
  - "[48-01] ADVISORY coverage_gap finding receives a non-empty default recommendation when scan_error is empty — preserves non-empty contract while keeping informational status"
  - "[48-01] EMAIL/BROKER findings with RSA key exchange flagged quantum_vulnerable=True — they describe RSA-KEX which is in scope for NIST IR 8547"
metrics:
  duration: ~25 minutes
  completed: 2026-05-04
  tasks: 2
  files: 3
---

# Phase 48 Plan 01: Rich Finding Context — Producer Chokepoint Summary

One-liner: Centralized risk-engine finding construction in a `_build_finding` chokepoint enforcing non-empty `description`, FIPS-only recommendations, and a single canonical NIST IR 8547 deprecation phrase on quantum-vulnerable findings.

## What Was Built

### Module-level constant: `NIST_IR_8547_DEPRECATION`

Exact locked string (`quirk/engine/risk_engine.py:21-29`):

```
"Per NIST IR 8547, RSA and ECC are deprecated after 2030 and disallowed after 2035."
```

### Helper: `_build_finding` (`quirk/engine/risk_engine.py:32-67`)

Kw-only-arg chokepoint with the contract from CONTEXT D-02:

- `description` and `recommendation` are validated non-empty (raises `ValueError`).
- When `quantum_vulnerable=True`, `NIST_IR_8547_DEPRECATION` is appended to the
  stripped recommendation (separated by a single space).
- Returns a 6-key dict: `severity, host, port, title, description, recommendation`.

### Producer call sites migrated

All 16 dict-literal `findings.append({…})` sites in the engine were replaced
with `_build_finding(...)` calls. Final post-migration count:
`grep -c 'findings.append({' quirk/engine/risk_engine.py` → **0**.

| Finding (location after migration) | quantum_vulnerable |
|---|---|
| ADVISORY coverage_gap (post-process adds `category` key) | False |
| Scan-error: TLS handshake blocked (post-process adds `detail` key) | False |
| Scan-error: mTLS required (post-process adds `detail` key) | False |
| Scan-error: Informational protocol observation (post-process adds `detail` key) | False |
| Plaintext HTTP service detected | False |
| Legacy TLS versions allowed (TLS 1.0/1.1) | False |
| Legacy TLS cipher suites accepted | False |
| TLS certificate expired | False |
| TLS certificate expiring within 30 days | False |
| TLS certificate is self-signed | False |
| TLS certificate issued by untrusted CA | False |
| TLS certificate uses undersized RSA key | **True** |
| TLS certificate uses quantum-vulnerable RSA key | **True** |
| TLS certificate uses undersized ECDSA key | **True** |
| TLS certificate uses quantum-vulnerable ECDSA key | **True** |
| SSH quantum planning advisory | **True** |
| Container OpenSSL EOL (in `_evaluate_container_package`) | False |
| Container quantum-vulnerable crypto library (no-version branch) | **True** |
| Container outdated cryptography (severe + medium) | False |
| Container outdated pyOpenSSL | False |
| Container outdated libgcrypt 1.8.x | False |
| Container generic crypto library inventory | False |
| Unknown open service | False |
| STARTTLS downgrade risk on SMTP | False |
| Weak cipher suite on email TLS endpoint | **True** |
| Non-PFS cipher suite on email TLS endpoint | **True** |
| Plaintext Kafka listener | False |
| Plaintext AMQP listener | False |
| Plaintext Redis listener | False |
| Weak cipher suite on broker TLS endpoint | **True** |

### Stale-terminology purge (line 447 hit)

- Old text at line 447: `"(ML-KEM / CRYSTALS-Kyber for key exchange, ML-DSA / Dilithium for signatures)."`
- Rewritten to: `"Plan migration to ML-KEM (FIPS 203) for key exchange and ML-DSA (FIPS 204) or SLH-DSA (FIPS 205) for signatures."`
- Container `_evaluate_container_package` "when NIST PQC standards are adopted upstream" was also rewritten to FIPS-only language.

After migration:
- `grep -i -cE 'kyber|dilithium|when standards are adopted' quirk/engine/risk_engine.py` → **0**
- `grep -c 'FIPS 203' quirk/engine/risk_engine.py` → **9**
- `grep -c 'FIPS 204' quirk/engine/risk_engine.py` → **5**
- `grep -c 'FIPS 205' quirk/engine/risk_engine.py` → **5**

### Dedup-key safety (T-48-03)

Inline NOTE added at the top of `_dedupe_findings` documenting the deterministic
suffix invariant. New regression test
`TestRichFindingContext.test_dedup_safety_for_quantum_findings` constructs two
identical RSA endpoints and asserts they collapse to a single deduped finding
post-suffix-append.

### Tests added

`tests/test_risk_engine.py`:

1. `TestBuildFinding` — 8 cases: validation rejects empty/whitespace `description`
   and `recommendation`; quantum-vulnerable append/no-append behavior; constant
   string equality; 6-key dict shape.
2. `TestRichFindingContext` — 5 cases over a 13-endpoint fixture:
   - every emitted finding has a non-empty description;
   - no `kyber` / `dilithium` / `when standards are adopted` substring in
     description+recommendation;
   - every quantum-vulnerable finding cites `NIST_IR_8547_DEPRECATION` and a
     `FIPS 203/204/205` designation;
   - non-quantum findings omit the deprecation phrase;
   - dedup-key safety for identical quantum endpoints.

## Files Modified

- `quirk/engine/risk_engine.py` — constant + helper + migration of all
  producer sites; dedup-key NOTE.
- `tests/test_risk_engine.py` — 13 new tests across `TestBuildFinding` and
  `TestRichFindingContext`.
- `.planning/phases/48-rich-finding-context/deferred-items.md` — pre-existing
  CBOM-schema test failures logged out-of-scope.

## Commits

| Task | Commit | Subject |
|---|---|---|
| 1 | `d4c7983` | `feat(48-01): add NIST_IR_8547_DEPRECATION constant and _build_finding helper` |
| 2 | `4cae4c3` | `feat(48-01): migrate all risk_engine producer sites to _build_finding` |

## Deviations from Plan

None of substance. Two minor in-scope adjustments worth flagging:

1. **ADVISORY coverage_gap recommendation default.** The plan listed the
   ADVISORY branch among the producer sites to migrate via `_build_finding`,
   but the original code populated `recommendation` from `getattr(e,
   "scan_error", "") or ""` — i.e. an empty string was legal. `_build_finding`
   forbids empty recommendations. To preserve the contract without dropping
   the finding, a sensible default was added: `"Install the missing optional
   extra (pip install 'quirk[<extra>]') and re-run the scan to obtain
   coverage for this protocol."` This is applied only when `scan_error` is
   empty. Tracked under decisions.

2. **EMAIL/BROKER quantum-vulnerable flagging.** The plan said "flag last two
   True" for email and "mixed" for broker. The semantics-driven flagging
   landed as: STARTTLS downgrade → False; Weak RSA-KEX (email) → True; Non-PFS
   ECDHE pre-1.3 (email) → True; Plaintext broker listeners (Kafka/AMQP/Redis)
   → False; Weak RSA-KEX broker → True. Rationale recorded under decisions.

## Quick-verify Commands

```bash
# Producer chokepoint enforced
grep -c '_build_finding(' quirk/engine/risk_engine.py    # 33
grep -c 'findings.append({' quirk/engine/risk_engine.py  # 0

# Stale terminology purged
grep -i -cE 'kyber|dilithium|when standards are adopted' quirk/engine/risk_engine.py  # 0

# FIPS designations present
grep -c 'FIPS 203' quirk/engine/risk_engine.py   # 9
grep -c 'FIPS 204' quirk/engine/risk_engine.py   # 5
grep -c 'FIPS 205' quirk/engine/risk_engine.py   # 5

# Constant exact-string check
python -c "from quirk.engine.risk_engine import NIST_IR_8547_DEPRECATION; assert NIST_IR_8547_DEPRECATION == 'Per NIST IR 8547, RSA and ECC are deprecated after 2030 and disallowed after 2035.'"

# Tests
python -m pytest tests/test_risk_engine.py -v        # 36 passed
python -m compileall quirk/engine/risk_engine.py     # exit 0
```

## Deferred Issues

19 pre-existing failures in `tests/test_cbom_schema_validation.py` (chaos lab
profile drift introduced by Phase 46 — `tls-cert-defects` profile not yet
wired into PROFILE_ENDPOINTS / synthesizers). Logged in `deferred-items.md`.
Not caused by 48-01 — verified by `git stash` baseline run.

## Self-Check: PASSED

- `quirk/engine/risk_engine.py` — FOUND
- `tests/test_risk_engine.py` — FOUND
- `.planning/phases/48-rich-finding-context/deferred-items.md` — FOUND
- Commit `d4c7983` — FOUND
- Commit `4cae4c3` — FOUND
