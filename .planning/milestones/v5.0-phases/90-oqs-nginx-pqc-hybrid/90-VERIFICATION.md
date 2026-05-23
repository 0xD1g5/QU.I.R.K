---
phase: 90-oqs-nginx-pqc-hybrid
verified: 2026-05-22T12:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/9
  gaps_closed:
    - "On modern-OpenSSL hosts (genuine path), the scanner produces a genuine quantum-safe CBOM algorithm component (KEM, NIST L3)"
    - "REQUIREMENTS.md traceability table reflects PQC-01/02/03 as completed (not pending)"
  gaps_remaining: []
  regressions: []
---

# Phase 90: OQS-nginx PQC-Hybrid Verification Report

**Phase Goal:** The quantum-readiness scoring model has a concrete demoable post-quantum ceiling anchor — a digest-pinned OQS-nginx chaos lab profile serving an X25519MLKEM768 hybrid endpoint is up, the scanner observes and classifies it (as a real quantum-safe component or a clearly-scoped advisory), and the scoring model rewards PQC-hybrid posture with an agility bonus.
**Verified:** 2026-05-22
**Status:** PASSED
**Re-verification:** Yes — after gap closure (commits f861dc6 + ee0e192)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `docker compose --profile oqs-nginx up` starts a digest-pinned OQS-nginx container | VERIFIED | `docker-compose.yml` L1232: `openquantumsafe/nginx@sha256:6ca18ac692f347ea9d4c3fdab4231189f2146570cd03c4d8fb486bba208ef870`; profiles: ["oqs-nginx"]; port 127.0.0.1:39444:443 |
| 2 | The container serves a TLS 1.3 endpoint pinning X25519MLKEM768 | VERIFIED | `oqs-nginx/nginx.conf`: `ssl_ecdh_curve X25519MLKEM768`, `ssl_protocols TLSv1.3`; human-verified live via `openssl s_client` (Negotiated TLS1.3 group: X25519MLKEM768, mldsa65 cert) |
| 3 | lab.sh profiles auto-derives oqs-nginx with no ALL_PROFILES edit | VERIFIED | `./lab.sh profiles` output includes `oqs-nginx`; lab.sh has no hardcoded `ALL_PROFILES` list — auto-derives from `docker-compose.yml` profiles |
| 4 | README profile table and expected_results_v4.md document the profile | VERIFIED | README L50: oqs-nginx row with port 39444; `expected_results_v4.md` has `## Profile: oqs-nginx` section at L723 with full oracle |
| 5 | The PQC probe is outside the sslyze flow, wired via `_wrapped_phase` | VERIFIED | `run_scan.py` L1111-1169: `_run_pqc_phase` defined as a standalone function, wired via `_wrapped_phase(run_stats, "pqc_probe", "pqc_probe", ...)` — not inside `_run_tls_phase` |
| 6 | `pqc_hybrid_endpoint_count` surfaces in `build_evidence_summary` and increments on both paths | VERIFIED | `evidence.py` L117/138/444: counter initialized to 0, increments when `service_detail` contains `"pqc-hybrid-detected"` (both genuine TLS path and advisory ADVISORY path use this sentinel), returned in dict |
| 7 | SCORE_WEIGHTS gains `agility_pqc_hybrid_bonus: 8.0` and invariant test updated to 283.0/37 | VERIFIED | `scoring.py` L58; `test_score_weights_invariant.py` asserts `sum == 283.0` and `len == 37`; all PQC tests pass |
| 8 | On modern-OpenSSL hosts, the scanner produces a genuine quantum-safe CBOM algorithm component (KEM, NIST L3) | VERIFIED | commit f861dc6 added `"X25519MLKEM768": "X25519MLKEM768"` to `_KEX_MAP` in `builder.py` L153. `_decompose_cipher_suite("X25519MLKEM768")` now returns `["X25519MLKEM768"]`. `build_cbom([pqc_ep])` yields 2 components: `ALGORITHM X25519MLKEM768, primitive=KEM, nist_level=3, fips140-3-status=approved` + `PROTOCOL protocol:tls:pqc.example.com:39444`. 11-test regression suite in `tests/test_pqc_cbom_component.py` — all 11 pass. No side effects on classical or TLS 1.3 suite decomposition (confirmed by test and live spot-check). |
| 9 | REQUIREMENTS.md traceability table reflects PQC-01/02/03 as completed (not pending) | VERIFIED | commit ee0e192 updated L89-91: `PQC-01 \| 90 \| 90-01 \| done (6491f35, e5c61da)`, `PQC-02 \| 90 \| 90-02 \| done (7b1c0be, 1403254)`, `PQC-03 \| 90 \| 90-03 \| done (00e24f5, 41e172d)`. Pattern matches all prior completed requirements. |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quantum-chaos-enterprise-lab/docker-compose.yml` | oqs-nginx service, digest-pinned, profile oqs-nginx, port 39444:443 | VERIFIED | Service at L1231, exact digest, profiles: ["oqs-nginx"], `127.0.0.1:39444:443` |
| `quantum-chaos-enterprise-lab/oqs-nginx/nginx.conf` | `ssl_ecdh_curve X25519MLKEM768` deterministic config | VERIFIED | File exists, pins `ssl_ecdh_curve X25519MLKEM768` and `ssl_protocols TLSv1.3` |
| `quantum-chaos-enterprise-lab/README.md` | oqs-nginx row in Profile Summary table | VERIFIED | Row at L50 with port 39444 and correct description |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` | Finalized oqs-nginx oracle with X25519MLKEM768 | VERIFIED | Section exists at L723 with correct CBOM component claim (KEM/NIST-L3 now accurate as of gap closure) |
| `quirk/scanner/pqc_probe.py` | Capability gate + raw openssl probe, argv-list, no shell=True, timeout | VERIFIED | 166-line file; no `shell=True` found; argv list construction at L116-122; 8s timeout at L131; TimeoutExpired caught at L136; host validation at L102-103 |
| `quirk/cbom/classifier.py` | `x25519mlkem768` alias → (KEM, 3, 192) | VERIFIED | L69: `"x25519mlkem768": (CryptoPrimitive.KEM, 3, 192)`; `classify_algorithm("X25519MLKEM768")` returns `(KEM, 3, 192)` — now reachable from builder's TLS path via fixed `_decompose_cipher_suite` |
| `quirk/cbom/builder.py` | `_KEX_MAP` includes `"X25519MLKEM768"` entry | VERIFIED | L153: `"X25519MLKEM768": "X25519MLKEM768"` with comment documenting Phase 90 gap-closure rationale |
| `quirk/intelligence/evidence.py` | `pqc_hybrid_endpoint_count` in evidence summary dict | VERIFIED | L117/138/444 |
| `quirk/intelligence/scoring.py` | agility PQC-hybrid bonus weight + impacts entry reading `pqc_hybrid_endpoint_count` | VERIFIED | L58: `"agility_pqc_hybrid_bonus": 8.0`; L210-221: reads counter, appends to agility_impacts when count > 0 |
| `tests/test_score_weights_invariant.py` | Updated sum (283.0) and count (37) | VERIFIED | L22: asserts `sum == 283.0`; L36: asserts `len == 37`; Phase 90 note documented |
| `tests/test_pqc_cbom_component.py` | 11-test regression suite for gap-closure | VERIFIED | 142-line file, 11 tests: 4 unit tests for `_decompose_cipher_suite` (non-empty, token present, no classical side effect, no TLS1.3 side effect) + 7 integration tests for `build_cbom` (algorithm component present, name correct, KEM primitive, NIST level 3, approved fips status, protocol component still present, exactly 2 total components) |
| `tests/test_pqc_probe.py` | Probe tests with mocked subprocess | VERIFIED | 182 lines; 19 tests covering argv-list safety, timeout, host validation, classifier alias, parse |
| `tests/test_pqc_agility_bonus.py` | PQC-hybrid > classical agility + /25 clamp + orthogonality | VERIFIED | 117 lines; covers uplift, clamp, orthogonality, presence |
| `tests/test_pqc_discriminator.py` | False-positive-free discriminator regression | VERIFIED | 204 lines; negative arm (classical mocked) always runs; positive arm skips when lab down |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` | `quirk/scanner/pqc_probe.py` | import + `_wrapped_phase` (not sslyze) | VERIFIED | L1118: `from quirk.scanner.pqc_probe import probe_pqc_hybrid, host_supports_mlkem`; L1167-1169: `_wrapped_phase(run_stats, "pqc_probe", "pqc_probe", _run_pqc_phase, ...)` |
| `quirk/cbom/classifier.py` | `quirk/cbom/builder.py` | `classify_algorithm` lookup via fixed `_decompose_cipher_suite` | VERIFIED | `builder.py` L153: `_KEX_MAP["X25519MLKEM768"] = "X25519MLKEM768"`. `_decompose_cipher_suite("X25519MLKEM768")` returns `["X25519MLKEM768"]`. `_register_algorithm("X25519MLKEM768", ...)` is called. `classify_algorithm("X25519MLKEM768")` returns `(KEM, 3, 192)`. KEM ALGORITHM component emitted. Full chain now connected. |
| `quirk/intelligence/scoring.py` | `quirk/intelligence/evidence.py` | `evidence.get("pqc_hybrid_endpoint_count")` | VERIFIED | `scoring.py` L210: `pqc_hybrid_count = max(0, _as_int(evidence.get("pqc_hybrid_endpoint_count", 0)))` |
| `docker-compose.yml` | `oqs-nginx/nginx.conf` | volume mount | VERIFIED | L1238: `./oqs-nginx/nginx.conf:/opt/nginx/nginx-conf/nginx.conf:ro` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `quirk/intelligence/scoring.py` agility bonus | `pqc_hybrid_count` | `evidence.get("pqc_hybrid_endpoint_count", 0)` → `build_evidence_summary` sentinel check | Yes — counter increments when endpoint has `pqc-hybrid-detected` in `service_detail` | FLOWING |
| `quirk/cbom/builder.py` KEM component | `_decompose_cipher_suite(ep.cipher_suite)` for `cipher_suite="X25519MLKEM768"` | `_KEX_MAP["X25519MLKEM768"] = "X25519MLKEM768"` → returns `["X25519MLKEM768"]` → `_register_algorithm` called → `classify_algorithm("X25519MLKEM768")` → `(KEM, 3, 192)` | Yes — live spot-check: 2 components emitted (ALGORITHM KEM NIST-L3 + PROTOCOL) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All PQC + CBOM regression tests pass | `QUIRK_DB_PATH=:memory: python -m pytest tests/test_pqc_cbom_component.py tests/test_pqc_probe.py tests/test_pqc_agility_bonus.py tests/test_score_weights_invariant.py tests/test_pqc_discriminator.py -q` | 51 passed in 0.28s | PASS |
| `_decompose_cipher_suite("X25519MLKEM768")` → non-empty | `python -c "from quirk.cbom.builder import _decompose_cipher_suite; print(_decompose_cipher_suite('X25519MLKEM768'))"` | `['X25519MLKEM768']` | PASS |
| `build_cbom([pqc_ep])` produces KEM + PROTOCOL components | live Python invocation with `CryptoEndpoint(cipher_suite="X25519MLKEM768", ...)` | 2 components: `ALGORITHM X25519MLKEM768 primitive=KEM nist_level=3 fips140-3-status=approved` + `PROTOCOL protocol:tls:...` | PASS |
| Classical suite decomposition unaffected | `_decompose_cipher_suite("TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384")` | `['X25519', 'RSA', 'AES-256-GCM', 'SHA-384']` | PASS |
| TLS 1.3 suite decomposition unaffected | `_decompose_cipher_suite("TLS_AES_256_GCM_SHA384")` | `['AES-256-GCM', 'SHA-384']` | PASS |
| `pqc_hybrid_endpoint_count` in evidence summary | `build_evidence_summary([],[])['pqc_hybrid_endpoint_count']` | `0` (correct default on empty input) | PASS |
| compileall clean | `python -m compileall quirk run_scan.py` | No errors | PASS |

---

### Probe Execution

Step 7c: No `scripts/*/tests/probe-*.sh` files apply to this phase. SKIPPED (conventional probe pattern not used for this phase type).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| PQC-01 | 90-01 | oqs-nginx chaos-lab profile, digest-pinned, X25519MLKEM768 endpoint | SATISFIED | docker-compose.yml, nginx.conf, README, expected_results all consistent; lab.sh auto-derives |
| PQC-02 | 90-02 | Scanner observes and classifies PQC-hybrid endpoint (genuine quantum-safe CBOM component or clearly-scoped advisory) | SATISFIED | Genuine path: `build_cbom([pqc_ep])` emits `ALGORITHM X25519MLKEM768 KEM NIST-L3`. Advisory path: `scan_error_category="coverage_gap"` on old-OpenSSL hosts. Both OR conditions satisfied. REQUIREMENTS.md traceability row updated: `done (7b1c0be, 1403254)` |
| PQC-03 | 90-03 | pqc_hybrid_endpoint_count evidence counter + agility bonus in SCORE_WEIGHTS; invariant test updated | SATISFIED | `agility_pqc_hybrid_bonus: 8.0` in SCORE_WEIGHTS; invariant 283.0/37 asserted; agility uplift regression tests pass; REQUIREMENTS.md traceability row updated: `done (00e24f5, 41e172d)` |

---

### Anti-Patterns Found

No `TBD`, `FIXME`, or `XXX` debt markers found in any phase-90-modified source files. No `shell=True` in `pqc_probe.py`. The previously-flagged inaccuracy in `expected_results_v4.md` (CBOM component claim) is now accurate — the KEM component is genuinely emitted after the gap closure. No residual anti-patterns.

---

### Human Verification Required

None. All must-haves are verified programmatically. The live before/after agility demo (PQC agility 25 vs classical 17) was human-verified by the user during phase execution with the OQS-nginx container running (host OpenSSL 3.6.2).

---

## Summary

Phase 90 goal is fully achieved. Both gaps from the initial verification are closed:

**Gap 1 (was BLOCKER — now CLOSED):** commit f861dc6 added `"X25519MLKEM768": "X25519MLKEM768"` to `_KEX_MAP` in `quirk/cbom/builder.py` L153. `_decompose_cipher_suite("X25519MLKEM768")` now returns `["X25519MLKEM768"]` (was `[]`). `build_cbom([pqc_ep])` now yields 2 components: a genuine `ALGORITHM` component classified `KEM / NIST-L3 / approved` plus the `PROTOCOL` service component. The classifier alias `x25519mlkem768` → `(KEM, 3, 192)` in `classifier.py` is now reachable from the builder's TLS path. 11-test regression suite (`tests/test_pqc_cbom_component.py`) all pass. No side effects on classical or TLS 1.3 cipher suite decomposition confirmed.

**Gap 2 (was WARNING — now CLOSED):** commit ee0e192 updated REQUIREMENTS.md traceability table L89-91 from `pending` to `done` with commit hashes for PQC-01/02/03, matching the pattern of all prior completed requirements.

Full test suite result: **51 passed in 0.28s** (tests/test_pqc_cbom_component.py + tests/test_pqc_probe.py + tests/test_pqc_agility_bonus.py + tests/test_score_weights_invariant.py + tests/test_pqc_discriminator.py).

---

*Verified: 2026-05-22*
*Verifier: Claude (gsd-verifier)*
