---
phase: 95-code-signing-certificate-inventory
verified: 2026-05-23T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run a live scan with --inventory-code-signing against the ldaps chaos profile"
    expected: "1 HIGH CODE_SIGNING finding for uid=codesign-weak with reasons weak-rsa-key + weak-signing-alg; stable CBOM component count (no duplicate from TLS source); agility_codesign_weak_algo_ratio present in score output"
    why_human: "Requires Docker (ldaps profile up, ldaps-codesign-seed sidecar ran), live LDAP bind, and visual confirmation of JSON findings + CBOM bom-ref — cannot be automated without running services"
---

# Phase 95: Code-Signing Certificate Inventory Verification Report

**Phase Goal:** Users can inventory code-signing certificates discovered from LDAP and from existing TLS cert captures, with weak-algorithm findings and fingerprint-based CBOM de-duplication.
**Verified:** 2026-05-23T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--inventory-code-signing` lists code-signing certs from BOTH LDAP userCertificate (CodeSigning EKU) AND EKU checks on TLS-captured certs | VERIFIED | `scan_codesign_from_ldap` + `scan_codesign_from_tls_endpoints` both called from `_run_codesign_phase`; `test_flag_on_invokes_scanner` + `test_tls_eku_path_invoked` pass; `_CODESIGN_ATTRS = ("userCertificate",)` hardcoded; EKU filter via `ExtendedKeyUsageOID.CODE_SIGNING` |
| 2 | RSA<2048, EC<256, or SHA-1 code-signing cert raises HIGH severity CODE-SIGN/weak-algorithm | VERIFIED | `_classify_codesign_severity`: SHA-1 via `is_weak_cipher`, RSA<2048 inline, EC<256 inline; `test_rsa1024_sha1_emits_high`, `test_ec192_emits_high` pass; `expected_results_v4.md` carries the oracle row |
| 3 | Running inventory against a target with TLS certs captured produces NO duplicate CBOM components (dedup by fingerprint/surrogate key) | VERIFIED | CR-01 fix (commit 56884ae) confirmed: scanner sets `cert_subject` + `cert_not_after` ORM columns on both LDAP and TLS-EKU CODE_SIGNING endpoints; `_codesign_surrogate_key` fires against real output; `test_cbom_tls_plus_codesign_real_scanner_shape_no_dup` uses production scanner path and asserts 1 cert component with `quirk:code-signing-eku=true` annotation |
| 4 | Code-signing signals contribute to agility_signals; SCORE_WEIGHTS sum 299.0 (count 40) | VERIFIED | `SCORE_WEIGHTS["agility_codesign_weak_algo_ratio"] = 6.0`; sum = 299.0, count = 40 confirmed by live import and both invariant tests passing; `"CODE_SIGNING"` in `evidence._PROTOCOL_KEYS`; `agility_codesign_weak_algo_ratio` in evidence return dict; `codesign_weak_algo_count` wired to `agility_impacts` in scoring.py |
| 5 | ldaps chaos profile gained code-signing cert fixture with expected_results + README updated (LAB-01 partial) | VERIFIED | `ldaps/ldif/codesign-users.ldif` exists (uid=codesign-weak, dc=chaos,dc=local); `ldaps/certs/codesign-weak.der` (667 bytes); `ldaps-codesign-seed` sidecar in docker-compose.yml; `expected_results_v4.md` contains "CODE-SIGN/weak-algorithm"; README updated; lab.sh intentionally not modified (no new profile, dynamic discovery unchanged) |

**Score:** 5/5 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/scanner/codesign_scanner.py` | Scanner module with LDAP + TLS-EKU sources | VERIFIED | CODE_SIGNING constant, EKU filter, LDAP anonymous bind, SHA-256 fingerprint, CR-01 ORM columns set, no impacket, safe_str routing |
| `tests/test_codesign_scanner.py` | 7 unit tests for CSIGN-01/02 | VERIFIED | 7/7 pass: EKU filter, RSA<2048, EC<256, SHA-1, fingerprint, protocol constant, TLS-EKU check |
| `tests/fixtures/codesign/*.der` | 4 DER fixtures | VERIFIED | rsa1024_sha1 (675B), ec192 (494B), rsa2048_sha256 (940B), rsa2048_sha256_noncoding (939B) |
| `quirk/config.py` | ConnectorsCfg codesign fields | VERIFIED | enable_codesign, codesign_targets, codesign_search_base, codesign_timeout present |
| `quirk/cbom/builder.py` | CODE_SIGNING Pass-1 branch, Pass-2b dedup, Pass-3 skip | VERIFIED | 18 occurrences of CODE_SIGNING; `_extract_fp`, `_codesign_surrogate_key`, `_tls_surrogate_key` helpers; WR-01 dead loop removed; WR-02 explicit `_TLS_CERT_SOURCE_PROTOCOLS = ("TLS",)` allow-list |
| `quirk/intelligence/evidence.py` | CODE_SIGNING in _PROTOCOL_KEYS, codesign_weak_algo_count | VERIFIED | _PROTOCOL_KEYS tuple includes "CODE_SIGNING"; counter declared; delimited `\|weak` token match (WR-03 fix) |
| `quirk/intelligence/scoring.py` | agility_codesign_weak_algo_ratio: 6.0; sum 299.0; count 40 | VERIFIED | Entry confirmed; live import verified sum=299.0, count=40; agility_impacts entry present |
| `tests/test_score_weights_invariant.py` | sum 299.0 / count 40 assertions | VERIFIED | Both assertions updated; both pass |
| `tests/test_codesign_cbom.py` | CBOM dedup tests including real-scanner-shape CR-01 regression | VERIFIED | 5 tests (4 original + `test_cbom_tls_plus_codesign_real_scanner_shape_no_dup`); all pass |
| `tests/test_evidence_codesign.py` | Evidence counter and ratio tests | VERIFIED | 4/4 pass |
| `run_scan.py` | --inventory-code-signing flag, _run_codesign_phase, CODE_SIGNING in _dar_protocols | VERIFIED | Flag present (dest=inventory_code_signing); _dar_protocols contains "CODE_SIGNING"; resume block; codesign_endpoints in assembly; lazy imports on flag-off path |
| `tests/test_run_scan_codesign_wiring.py` | Wiring tests | VERIFIED | 5/5 pass (includes dar_protocols AST test with correct path resolution) |
| `quantum-chaos-enterprise-lab/ldaps/ldif/codesign-users.ldif` | Code-signing fixture user | VERIFIED | dc=chaos,dc=local base DN (not dc=quirk,dc=lab); userCertificate;binary:: (RFC 4523) |
| `quantum-chaos-enterprise-lab/ldaps/certs/codesign-weak.der` | RSA-1024/SHA-1 DER cert | VERIFIED | 667 bytes; per SUMMARY verified RSA-1024, sha1WithRSAEncryption, CodeSigning EKU OID |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | ldaps-codesign-seed sidecar | VERIFIED | profiles: ["ldaps"], idempotent ldapadd -c, exit-68 swallow |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` | CODE-SIGN/weak-algorithm oracle row | VERIFIED | "CODE-SIGN/weak-algorithm" present |
| `quantum-chaos-enterprise-lab/README.md` | ldaps code-signing fixture documented | VERIFIED | grep -qi "code-signing" passes |
| `docs/configuration.md` | --inventory-code-signing + codesign connector docs | VERIFIED | grep passes |
| `docs/report-interpretation.md` | CODE-SIGN/weak-algorithm finding + 299.0 scoring | VERIFIED | grep passes |
| `docs/chaos-lab.md` | ldaps code-signing fixture | VERIFIED | grep passes |
| `docs/UAT-SERIES.md` | UAT-95-01/02 cases + 299.0 weight | VERIFIED | grep passes; committed as b7d2d35 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `codesign_scanner.py` | `quirk/util/weak_crypto.py` | `is_weak_cipher(sig_hash)` | VERIFIED | SHA-1 detection routed through is_weak_cipher; EC<256 inline (avoids AES-256 token collision) |
| `codesign_scanner.py` | `cryptography ExtendedKeyUsageOID.CODE_SIGNING` | `_has_codesigning_eku` | VERIFIED | OID 1.3.6.1.5.5.7.3.3 used in EKU extension check |
| `quirk/intelligence/scoring.py` | `quirk/intelligence/evidence.py` | `evidence.get("codesign_weak_algo_count")` | VERIFIED | `agility_impacts.append(("Code-signing cert weak algorithm", ... * w["agility_codesign_weak_algo_ratio"]))` |
| `quirk/cbom/builder.py` | `service_detail fingerprint token` | `_extract_fp` | VERIFIED | `_extract_fp` parses "fingerprint=<hex>" token; `_codesign_surrogate_key` reads cert_subject/cert_not_after ORM columns |
| `run_scan.py` | `quirk.scanner.codesign_scanner.scan_codesign_from_ldap` | `_run_codesign_phase` | VERIFIED | Lazy import inside _run_codesign_phase; called only when flag is set and codesign_targets non-empty |
| `docker-compose.yml` | `ldaps/ldif/codesign-users.ldif` | `ldaps-codesign-seed sidecar` | VERIFIED | `codesign-users.ldif` in volumes mount; sidecar runs ldapadd against the LDIF |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `codesign_scanner.py scan_codesign_from_ldap` | `results` list | LDAP `_bind_and_search_codesign` generator → `_parse_codesign_cert` → `_classify_codesign_severity` | Yes — parses real DER bytes from LDAP entries; CR-01 fix ensures cert_subject/cert_not_after ORM columns populated | FLOWING |
| `codesign_scanner.py scan_codesign_from_tls_endpoints` | `results` list | TLS `tls_capabilities_json["eku_oids"]` in-process check | Yes — reads already-populated CryptoEndpoint columns; CR-01 fix copies cert_subject/cert_not_after through | FLOWING |
| `builder.py Pass-2b` | `_tls_surrogate_index` | `cert_components` list + TLS endpoints | Yes — explicit `_TLS_CERT_SOURCE_PROTOCOLS = ("TLS",)` allow-list; WR-01 dead loop removed; surrogate dedup fires against real scanner output (verified by `test_cbom_tls_plus_codesign_real_scanner_shape_no_dup`) | FLOWING |
| `evidence.py codesign_weak_algo_count` | counter | CODE_SIGNING endpoints' `service_detail` | Yes — delimited `\|weak` token match (WR-03 fix); false-positive from DN/subject content closed | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| SCORE_WEIGHTS sum and count | `python3 -c "from quirk.intelligence.scoring import SCORE_WEIGHTS; print(sum(...), len(...))"` | sum=299.0, count=40 | PASS |
| All Phase 95 tests | `.venv/bin/python -m pytest tests/test_codesign_scanner.py tests/test_codesign_cbom.py tests/test_evidence_codesign.py tests/test_run_scan_codesign_wiring.py tests/test_score_weights_invariant.py` | 23/23 passed | PASS |
| CR-01 real-scanner-shape regression | `test_cbom_tls_plus_codesign_real_scanner_shape_no_dup` via pytest | PASSED — code_ep.cert_subject == "CN=signed.corp.com,O=Corp", code_ep.cert_not_after == datetime(2030,1,1), 1 cert component with quirk:code-signing-eku=true | PASS |
| WR-03 fix: delimited token match | Read `evidence.py:336-338` | `_cs_segments = ...split("|")` then `"weak" in _cs_segments` — delimited sentinel, not substring | PASS |
| WR-01 fix: no dead loop | Read `builder.py:740-757` | First loop replaced with `_TLS_CERT_SOURCE_PROTOCOLS = ("TLS",)` explicit allow-list; no dead code | PASS |

---

## Probe Execution

No probe scripts found for Phase 95. Step 7c: SKIPPED (no probe-*.sh in scripts/).

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CSIGN-01 | 95-01, 95-03 | Inventory from LDAP userCertificate + TLS EKU | SATISFIED | Both scanner functions implemented and wired; run_scan.py flag + _run_codesign_phase; 7 unit tests + 5 wiring tests pass |
| CSIGN-02 | 95-01 | Weak-algo HIGH finding (RSA<2048, EC<256, SHA-1) | SATISFIED | `_classify_codesign_severity` + severity HIGH on emitted endpoint; oracle row in expected_results_v4.md |
| CSIGN-03 | 95-02 | Fingerprint-based CBOM dedup (no duplicate components) | SATISFIED | Fingerprint same-source dedup + surrogate-key cross-source dedup; CR-01 fixed and verified by real-scanner-shape test |
| SCORE-01 (partial) | 95-02 | agility_signals +6.0 weight; SCORE_WEIGHTS 299.0/40 | SATISFIED (phase portion) | sum=299.0, count=40 live-verified; codesign_weak_algo_count wired through evidence to scoring |
| LAB-01 (partial) | 95-03 | ldaps profile code-signing fixture with triple update | SATISFIED (phase portion) | LDIF + DER + sidecar + expected_results + README all present; oracle row present |

**REQUIREMENTS.md tracking gap:** All CSIGN-01/02/03 rows and the SCORE-01 / LAB-01 rows remain `Pending` in `.planning/REQUIREMENTS.md`. This is a tracking artifact issue, not an implementation gap — the phase 95 portion of these requirements is demonstrably complete in the codebase. The orchestrator should flip these rows to `complete` (CSIGN-01/02/03) or `in-progress` (SCORE-01, LAB-01 which span into Phase 96).

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/scanner/codesign_scanner.py` | 349-358 | SAFE code-signing certs are not inventoried (severity==None → continue) | INFO (IN-01 from REVIEW) | Inventory-vs-risk framing gap: healthy certs leave no CBOM record; by design per current phase scope |
| `quirk/scanner/codesign_scanner.py` | 100-109, 138-167 | Ed25519/Ed448 classified UNKNOWN, not weak-flagged | INFO (IN-02 from REVIEW) | Quantum-vulnerable but silently unclassified; acceptable for v1 scope |
| `run_scan.py` | 1515 | `_dar_protocols` tuple mixes label conventions (AZURE-BLOB vs AZURE_BLOB in evidence) | INFO (IN-03 from REVIEW) | Pre-existing; CODE_SIGNING entry is correctly the exact uppercase literal — no regression |
| `quirk/scanner/codesign_scanner.py` | 186-190 (WR-04) | `expired` and `not_after_dt` computed but `cert_not_after` is propagated as a datetime to the ORM; expiry findings not yet reaching evidence `expired_count` counter | WARNING | Expiry of code-signing certs is invisible to the evidence layer; explicitly deferred in REVIEW.md |

No TBD/FIXME/XXX markers found in phase-modified files.

---

## Human Verification Required

### 1. Live Code-Signing Scan Against ldaps Chaos Profile

**Test:** Bring up the `ldaps` Docker Compose profile (`./lab.sh up ldaps`), wait for `ldaps-codesign-seed` sidecar to complete, then run a scan:
```bash
python run_scan.py --target ldap://127.0.0.1:389 \
  --inventory-code-signing \
  --codesign-search-base dc=chaos,dc=local \
  --allow-internal-targets \
  --output /tmp/cs-test.json
```
Inspect `/tmp/cs-test.json` findings and CBOM.

**Expected:**
- Exactly 1 HIGH CODE_SIGNING finding for `uid=codesign-weak,ou=people,dc=chaos,dc=local`
- Finding carries 2 reasons: `weak-rsa-key` and `weak-signing-alg` (RSA-1024 + SHA-1)
- CBOM contains exactly 1 certificate component with `bom-ref` starting `crypto/certificate/codesign/`
- `agility_codesign_weak_algo_ratio` appears in the score output with a non-zero value
- No duplicate cert component if TLS scan also captured the LDAP server's TLS cert

**Why human:** Requires Docker, live network bind to the ldaps container, and visual inspection of the JSON findings + CBOM output. Cannot be automated without running services.

---

## Gaps Summary

No automated gaps. All 5 success criteria are VERIFIED by code inspection and 23/23 passing tests including the CR-01 regression test that exercises the production scanner output shape end-to-end through the CBOM dedup logic.

The single outstanding item is the live-lab walkthrough (human verification above). All automated checks pass.

**REQUIREMENTS.md tracking note:** CSIGN-01, CSIGN-02, CSIGN-03 rows should be flipped to `complete`. SCORE-01 and LAB-01 rows should remain `in-progress` (both span into Phase 96).

---

_Verified: 2026-05-23T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
