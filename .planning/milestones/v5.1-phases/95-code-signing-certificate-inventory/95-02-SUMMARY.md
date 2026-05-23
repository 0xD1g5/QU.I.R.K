---
phase: 95-code-signing-certificate-inventory
plan: "02"
subsystem: cbom,intelligence
tags: [codesign, cbom, dedup, fingerprint, scoring, csign-03, score-01]
dependency_graph:
  requires:
    - quirk.scanner.codesign_scanner (CODE_SIGNING protocol, fingerprint in service_detail)
  provides:
    - quirk.cbom.builder.build_cbom (CODE_SIGNING Pass-1 branch + Pass-2b dedup)
    - quirk.intelligence.evidence.build_evidence_summary (codesign_weak_algo_count + agility_codesign_weak_algo_ratio)
    - quirk.intelligence.scoring.SCORE_WEIGHTS (agility_codesign_weak_algo_ratio: 6.0)
  affects:
    - quirk/cbom/builder.py (Pass-1 branch, Pass-2 skip, Pass-3 skip, Pass-2b dedup)
    - quirk/intelligence/evidence.py (_PROTOCOL_KEYS + counter + return dict)
    - quirk/intelligence/scoring.py (SCORE_WEIGHTS +1 entry, agility_impacts +1 entry)
    - tests/test_score_weights_invariant.py (sum 293.0→299.0, count 39→40)
tech_stack:
  added: []
  patterns:
    - fingerprint-based same-source dedup (_extract_fp parses "fingerprint=<hex>" token)
    - surrogate-key cross-source dedup (cert_subject + cert_pubkey_alg + cert_not_after)
    - TLS-derived cert wins; CODE_SIGNING annotates via CycloneDX Property quirk:code-signing-eku
    - agility_signals counter + ratio pattern (mirrors Phase 94 BEARER_TOKEN/OPENAPI)
key_files:
  created:
    - tests/test_codesign_cbom.py
    - tests/test_evidence_codesign.py
  modified:
    - quirk/cbom/builder.py
    - quirk/intelligence/evidence.py
    - quirk/intelligence/scoring.py
    - tests/test_score_weights_invariant.py
decisions:
  - "Surrogate-key cross-source dedup uses TLS endpoint data (not cert_component properties) to build _tls_surrogate_index — simpler and avoids reverse-engineering bom_ref strings"
  - "CODE_SIGNING-emitted components NOT added to _tls_surrogate_index: fingerprint is authoritative for same-source CODE_SIGNING dedup; adding them would collapse distinct-fingerprint certs with same metadata"
  - "Pass-2b dedup pass is a separate loop after Pass-2 (not inline) to allow TLS-wins cross-source lookup against the fully-populated cert_components list"
metrics:
  duration: "~18 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  files_changed: 6
---

# Phase 95 Plan 02: CBOM CODE_SIGNING + Evidence/Scoring Wire-Up Summary

**One-liner:** CODE_SIGNING fingerprint dedup in CBOM builder with TLS-wins cross-source reconciliation, codesign weak-algo counter wired to agility_signals, and SCORE_WEIGHTS advancing 293.0→299.0 (count 39→40).

## What Was Built

### Task 1: CBOM CODE_SIGNING branch + fingerprint dedup (CSIGN-03)

**RED commit:** `1731390` — `tests/test_codesign_cbom.py` with 4 failing tests.

**GREEN commit:** `3353bda` — `quirk/cbom/builder.py` changes:

**New helpers:**
- `_extract_fp(service_detail)` — parses the `fingerprint=<hex>` pipe-delimited token from CODE_SIGNING `service_detail`. Returns `None` when absent. Safe: only splits on `|`, no eval. (T-95-05 mitigated.)
- `_codesign_surrogate_key(ep)` — returns `(cert_subject, cert_pubkey_alg, cert_not_after)` triple when all three are non-empty; otherwise `None`.
- `_tls_surrogate_key(ep)` — same structure for TLS endpoints.

**Pass-1 branch:** `elif ep.protocol == "CODE_SIGNING":` after the ADCS branch — calls `_register_algorithm(ep.cert_pubkey_alg, ...)` when `cert_pubkey_alg` is set.

**Pass-2 skip:** Added `"CODE_SIGNING"` to the skip tuple — cert dedup handled in Pass-2b, not here.

**Pass-2b (new):** Fingerprint + cross-source dedup pass between Pass-2 and Pass-3:
1. Builds `_tls_surrogate_index: dict[surrogate_key → cert_component]` from TLS endpoints.
2. For each CODE_SIGNING endpoint:
   - **Cross-source TLS-wins:** if surrogate key matches a TLS cert component, annotates it with `Property(name="quirk:code-signing-eku", value="true")` — no new cert component.
   - **Same-source fingerprint dedup:** first occurrence of a fingerprint hex wins; duplicates are skipped.
   - **New cert component:** built when fingerprint is unique and no TLS surrogate match — `bom_ref = f"crypto/certificate/codesign/{fp}"`.
3. CODE_SIGNING-emitted components are NOT added to `_tls_surrogate_index` (this prevents distinct-fingerprint same-metadata certs from being incorrectly collapsed).

**Pass-3 skip:** Added `"CODE_SIGNING"` to the skip tuple — no `ProtocolProperties` for a non-transport protocol.

Tests (all 4 GREEN):
- `test_codesign_pass1_registers_algorithm`
- `test_cbom_dedup_stable_count` — same fingerprint → stable count
- `test_codesign_distinct_fingerprints_not_deduped` — distinct fingerprints → 2 cert components
- `test_cbom_tls_plus_codesign_no_dup` — TLS + CODE_SIGNING same surrogate key → 1 cert component

### Task 2: Evidence counter + scoring weight + SCORE_WEIGHTS invariant (SCORE-01)

**RED commit:** `3081a0b` — `tests/test_evidence_codesign.py` with 3 failing tests (1 already passes).

**GREEN commit:** `ccdf6bb` — evidence.py, scoring.py, test_score_weights_invariant.py changes:

**`quirk/intelligence/evidence.py`:**
- Added `"CODE_SIGNING"` to `_PROTOCOL_KEYS` tuple (Phase 95 CSIGN-01 comment)
- Added `codesign_weak_algo_count = 0` counter declaration (alongside Phase 94 counters)
- Added `elif proto == "CODE_SIGNING":` branch that increments `codesign_weak_algo_count` when `"weak"` appears in `service_detail.lower()`
- Added to return dict: `codesign_weak_algo_count` and `agility_codesign_weak_algo_ratio` (rounds to 4dp, 0.0 when no endpoints)

**`quirk/intelligence/scoring.py`:**
- Added `"agility_codesign_weak_algo_ratio": 6.0` to `SCORE_WEIGHTS` after the Phase 94 pair
  - Sum: 293.0 → 299.0 (+6.0)
  - Count: 39 → 40 (+1)
- Added `agility_impacts.append(("Code-signing cert weak algorithm", -_ratio(...) * w["agility_codesign_weak_algo_ratio"]))` after Phase 94 block

**`tests/test_score_weights_invariant.py`:**
- Updated sum assertion: `293.0` → `299.0`
- Updated count assertion: `39` → `40`
- Updated docstring history: added Phase 95 SCORE-01 delta entry
- **Both assertions updated in the same edit** (Phase 94 lesson from plan context)

Tests (all 6 GREEN):
- `test_score_weights_sum_invariant` — sum == 299.0
- `test_score_weights_count_invariant` — count == 40
- `test_codesign_protocol_key_present`
- `test_codesign_weak_algo_count_increments`
- `test_codesign_weak_algo_count_no_increment_without_weak`
- `test_codesign_ratio_in_evidence_dict`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all counters are wired end-to-end from scanner service_detail through evidence dict into agility_impacts.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries beyond the plan's threat model.

- T-95-05 (Tampering — `_extract_fp` parsing): mitigated as designed — splits only on `|`, extracts only the `fingerprint=` fixed token, no eval/exec; non-matching detail yields `None`.
- T-95-06 (DoS — dedup pass): accepted; bounded by `paged_size=500` per LDAP page set upstream.
- T-95-07: no new packages installed this plan.

## Self-Check: PASSED

Files present:
- quirk/cbom/builder.py (modified): YES — `grep -c "CODE_SIGNING" = 18`
- quirk/intelligence/evidence.py (modified): YES — `"CODE_SIGNING" in _PROTOCOL_KEYS`
- quirk/intelligence/scoring.py (modified): YES — `"agility_codesign_weak_algo_ratio": 6.0`
- tests/test_codesign_cbom.py (created): YES
- tests/test_evidence_codesign.py (created): YES
- tests/test_score_weights_invariant.py (modified): YES — sum 299.0, count 40

Commits present:
- 1731390 (test RED CBOM): YES
- 3353bda (feat GREEN CBOM): YES
- 3081a0b (test RED evidence): YES
- ccdf6bb (feat GREEN evidence/scoring): YES

Tests: 10/10 passed (test_codesign_cbom.py × 4 + test_evidence_codesign.py × 4 + test_score_weights_invariant.py × 2)
