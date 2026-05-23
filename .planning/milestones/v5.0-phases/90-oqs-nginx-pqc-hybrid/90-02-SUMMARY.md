---
phase: 90-oqs-nginx-pqc-hybrid
plan: "02"
subsystem: scanner/cbom/intelligence
tags: [pqc, probe, openssl, classifier, evidence, tdd]
dependency_graph:
  requires: [90-01]
  provides: [pqc_probe.py, x25519mlkem768-classifier-alias, pqc_hybrid_endpoint_count]
  affects: [quirk/cbom/classifier.py, quirk/intelligence/evidence.py, run_scan.py]
tech_stack:
  added: [quirk/scanner/pqc_probe.py]
  patterns: [subprocess-argv-list, capability-gate, advisory-fallback, tdd-red-green]
key_files:
  created:
    - quirk/scanner/pqc_probe.py
    - tests/test_pqc_probe.py
  modified:
    - quirk/cbom/classifier.py
    - quirk/intelligence/evidence.py
    - run_scan.py
decisions:
  - "D-01: PQC probe is a dedicated openssl subprocess phase outside sslyze/nassl"
  - "D-02: X25519MLKEM768 mapped via alias to existing mlkem768x25519-sha256 (KEM, NIST-L3)"
  - "D-05: pqc_hybrid_endpoint_count increments on both genuine and advisory paths"
  - "Sentinel string 'pqc-hybrid-detected' in service_detail drives the D-05 counter"
metrics:
  duration_seconds: 201
  completed_date: "2026-05-22"
  tasks_completed: 2
  files_changed: 5
---

# Phase 90 Plan 02: PQC Probe Module + Classifier Alias + Evidence Counter Summary

**One-liner:** Raw openssl s_client probe (argv-list, capability-gated) detects X25519MLKEM768 hybrid TLS outside the sslyze flow; classifier alias maps the group to KEM/NIST-L3; pqc_hybrid_endpoint_count primes Plan 03 scoring on both modern and old-OpenSSL hosts.

## What Was Built

### Task 1: PQC probe module + classifier alias (TDD — RED/GREEN)

**RED commit:** `12b61c2` — 19 failing tests covering argv-list safety, TimeoutExpired handling, host validation, negotiated-group parse, and classifier alias.

**GREEN commit:** `7b1c0be`

- `quirk/scanner/pqc_probe.py` (152 lines): capability gate (`host_supports_mlkem()` runs `openssl list -kem-algorithms` as argv list) + probe function (`probe_pqc_hybrid(host, port, timeout=8)`) running `openssl s_client -connect host:port -groups X25519MLKEM768 -tls1_3` as an argv list with `/dev/null` stdin, 8-second hard timeout, and host validation (empty + shell metachar rejection).
- `quirk/cbom/classifier.py`: added `"x25519mlkem768": (CryptoPrimitive.KEM, 3, 192)` alias adjacent to the existing `mlkem768x25519-sha256` entry — reuses the NIST-L3 slot, no table churn (D-02).
- All 19 tests pass with mocked subprocess; no live network required.

### Task 2: Evidence counter + run_scan PQC phase wiring

**Commit:** `1403254`

- `quirk/intelligence/evidence.py`: added `pqc_hybrid_endpoint_count` counter initialized to 0; increments for any endpoint whose `service_detail` contains the `"pqc-hybrid-detected"` sentinel; surfaces as `"pqc_hybrid_endpoint_count"` in the return dict of `build_evidence_summary`. Both genuine-component (TLS) and advisory-fallback (ADVISORY) paths carry the sentinel — D-05 satisfied.
- `run_scan.py`: dedicated `_run_pqc_phase` function wired via `_wrapped_phase(run_stats, "pqc_probe", ...)` between SSH and JWT phases — explicitly NOT inside `_run_tls_phase` (D-01). Genuine path emits `CryptoEndpoint(protocol="TLS", cipher_suite="X25519MLKEM768", service_detail="pqc-hybrid-detected|group=X25519MLKEM768")`; advisory path emits `CryptoEndpoint(protocol="ADVISORY", scan_error_category="coverage_gap", service_detail="pqc-hybrid-detected|advisory=openssl-too-old")`. `pqc_endpoints` included in the final `endpoints` list for DB persist/CBOM.

## Deviations from Plan

### Auto-fixed Issues

None.

### Design Note: D-05 implementation via sentinel

The plan specified that both the genuine-component and advisory paths must increment `pqc_hybrid_endpoint_count`. The chosen implementation uses a `"pqc-hybrid-detected"` substring in `service_detail` as the sentinel — both paths set it, `build_evidence_summary` checks for it in the endpoint loop. This is a minimal, forward-compatible pattern (any future PQC path that sets the sentinel is automatically counted) and avoids parsing endpoint protocol + additional fields.

## Verification Results

- `QUIRK_DB_PATH=:memory: python -m pytest tests/test_pqc_probe.py -x -q` — **19 passed**
- `classify_algorithm("X25519MLKEM768")` → `(CryptoPrimitive.KEM, 3, 192)` — **PASS**
- `build_evidence_summary([], [])` returns `pqc_hybrid_endpoint_count: 0` — **PASS**
- D-05 counter test (genuine + advisory endpoints): `pqc_hybrid_endpoint_count == 2` — **PASS**
- `python -m compileall quirk run_scan.py` — **clean**

## Known Stubs

None — the probe, classifier alias, counter, and run_scan wiring are all fully functional.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes. The PQC probe adds one subprocess invocation to the scan flow (openssl binary). This is within the threat model documented in the plan (T-90-03, T-90-04, T-90-05):
- T-90-03 mitigated: argv list, host validation, no shell=True, port coerced to int.
- T-90-04 mitigated: 8-second hard timeout + /dev/null stdin; TimeoutExpired caught.
- T-90-05 mitigated: advisory path clearly documents the OpenSSL >= 3.5 limitation.

## Self-Check: PASSED

- `quirk/scanner/pqc_probe.py` — FOUND
- `tests/test_pqc_probe.py` — FOUND
- `12b61c2` (test commit) — FOUND in git log
- `7b1c0be` (feat commit) — FOUND in git log
- `1403254` (evidence + wiring commit) — FOUND in git log
