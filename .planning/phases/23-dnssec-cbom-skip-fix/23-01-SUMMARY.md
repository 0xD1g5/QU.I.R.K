---
phase: 23-dnssec-cbom-skip-fix
plan: "01"
subsystem: cbom
tags: [tdd, cbom, dnssec, bug-fix, regression-test]
requirements: [DNSSEC-04]

dependency_graph:
  requires: []
  provides: [DNSSEC-04]
  affects: [quirk/cbom/builder.py, tests/test_cbom_builder.py]

tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN cycle for regression test then one-line fix
    - Protocol skip list pattern (Pass 2 certificate filter)

key_files:
  created: []
  modified:
    - tests/test_cbom_builder.py
    - quirk/cbom/builder.py

decisions:
  - DNSSEC added to Pass 2 skip tuple only — Pass 1 and Pass 3 already handled DNSSEC correctly
  - Used real DNSKEY algorithm ECDSAP256SHA256 (not synthetic) to ensure test catches the actual bug path

metrics:
  duration: "< 5 minutes"
  completed: "2026-04-24"
  tasks_completed: 2
  files_modified: 2
---

# Phase 23 Plan 01: DNSSEC CBOM Pass 2 Certificate Skip List Fix Summary

**One-liner:** Added `"DNSSEC"` to the Pass 2 certificate skip tuple in `builder.py`, eliminating spurious hollow `CertificateProperties` CBOM components for DNSSEC endpoints that incorrectly represented DNSKEY algorithm records as X.509 certificates.

## What Was Built

### Task 1 — RED: DNSSEC fixture and three regression tests

Added to `tests/test_cbom_builder.py` (file now has 30 tests, up from 27):

- `_dnssec_endpoint(**overrides)` fixture factory — mirrors `_saml_endpoint` and `_kerberos_endpoint` pattern; uses `protocol="DNSSEC"`, `port=53`, `cert_pubkey_alg="ECDSAP256SHA256"`, `cert_pubkey_size=256`
- `test_dnssec_endpoint_algorithm_registered` — verifies Pass 1 registers `ecdsap256sha256` algorithm component (PASSED in RED state — Pass 1 was already correct)
- `test_dnssec_endpoint_no_tls_protocol` — verifies Pass 3 produces zero `crypto/protocol/tls/` components (PASSED in RED state — Pass 3 was already correct)
- `test_dnssec_endpoint_no_certificate` — verifies Pass 2 produces zero `crypto/certificate/` components (FAILED in RED state — confirmed the bug: spurious `crypto/certificate/example.com:53` component appeared)

**Commit:** `7435312` — `test(23-01): add failing DNSSEC CBOM regression tests`

### Task 2 — GREEN: One-line fix in builder.py

Changed line 389 of `quirk/cbom/builder.py` from:
```python
if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML"):
```
to:
```python
if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC"):
```

This is the only change. Pass 1 (line 351) and Pass 3 (line 468) already included `DNSSEC` and were untouched.

**Commit:** `de32d01` — `fix(23-01): add DNSSEC to Pass 2 cert skip list — closes DNSSEC-04`

## Verification Results

- `python -m pytest tests/test_cbom_builder.py -x -q` — **30 passed** (was 27 before phase)
- `python -m pytest tests/ -q --ignore=tests/test_dashboard_wiring.py --ignore=tests/test_v41_gap_closure.py` — **349 passed, 3 skipped** (zero new regressions)
- Smoke test: `build_cbom([DNSSEC endpoint])` → `Certificate components: 0` — VERIFIED
- `grep -n "DNSSEC" quirk/cbom/builder.py` confirms DNSSEC in Pass 1 (line 351), Pass 2 (line 389), Pass 3 (line 468)

**Note:** `test_v41_gap_closure.py::test_package_manifest_version_is_4_1_0` fails due to a stale `pip install` in the worktree environment (`importlib.metadata.version('quirk')` returns `4.0.0`). This is pre-existing, unrelated to this change, and confirmed by the test checking an installed package version rather than source files.

## Deviations from Plan

None — plan executed exactly as written. The one-line fix matched the plan specification precisely. TDD RED/GREEN gate sequence followed correctly.

## TDD Gate Compliance

- RED gate commit: `7435312` — `test(23-01): add failing DNSSEC CBOM regression tests`
- GREEN gate commit: `de32d01` — `fix(23-01): add DNSSEC to Pass 2 cert skip list — closes DNSSEC-04`
- REFACTOR: not needed (single-line fix, no cleanup required)

Both gates present and in correct order.

## Known Stubs

None.

## Threat Flags

None — this change is an internal data transform filter with no external input processing.

## Self-Check: PASSED

- `tests/test_cbom_builder.py` — FOUND (modified, 30 tests)
- `quirk/cbom/builder.py` — FOUND (modified, "DNSSEC" in Pass 2 skip tuple)
- Commit `7435312` — FOUND (RED test commit)
- Commit `de32d01` — FOUND (GREEN fix commit)
- 30 tests pass, 0 regressions
