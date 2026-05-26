---
phase: 110-cross-sensor-merge-scoring
plan: "01"
subsystem: cbom
tags: [merge, sensor, cbom, bom-ref, backward-compat, tdd]
dependency_graph:
  requires: [107-02, 108-01, 109-02]
  provides: [MERGE-03-sensor-aware-bom-ref]
  affects: [quirk/cbom/builder.py, tests/test_cbom_builder.py]
tech_stack:
  added: []
  patterns: [_sensor_prefix helper, f-string prefix insertion into bom_ref]
key_files:
  created: []
  modified:
    - quirk/cbom/builder.py
    - tests/test_cbom_builder.py
decisions:
  - "NULL sensor_id produces empty prefix so bom_refs are byte-identical to pre-110 format (backward-compat is non-negotiable per D-08)"
  - "CODE_SIGNING codesign/ fallback at L807/L811 intentionally excluded — no cross-segment code-sign scenario in v5.4 scope"
  - "_sensor_prefix uses getattr(ep, 'sensor_id', None) for safety against objects lacking the attribute"
metrics:
  duration: "~10 min"
  completed: "2026-05-25"
  tasks_completed: 2
  files_modified: 2
requirements: [MERGE-03]
---

# Phase 110 Plan 01: Sensor-Aware CBOM Identity (MERGE-03) Summary

**One-liner:** `_sensor_prefix(ep)` helper threaded through 4 host:port bom_ref sites so two sensors scanning the same RFC1918 IP produce distinct CBOM components while NULL sensor_id remains byte-identical to pre-110 output.

## What Was Built

### Task 1: MERGE-03 regression tests (RED)

Added two test functions to `tests/test_cbom_builder.py`:

- `test_two_sensors_same_ip_two_components`: builds a CBOM from two `_tls_endpoint` rows with `host="10.0.0.5"`, `port=443` but `sensor_id="sensor-a"` / `"sensor-b"` and distinct segments. Asserts that cert bom_refs are `crypto/certificate/sensor-a:10.0.0.5:443` and `crypto/certificate/sensor-b:10.0.0.5:443` (2 components, not collapsed), and that TLS protocol refs are similarly separated. Failed RED against the unmodified builder.
- `test_null_sensor_id_backward_compat`: asserts `sensor_id=None` produces `crypto/certificate/10.0.0.5:443` and `crypto/protocol/tls/10.0.0.5:443` — byte-identical to pre-110 format. Passed even before implementation (correct).

Commit: `fa4094d`

### Task 2: Thread _sensor_prefix through 4 bom_ref sites (GREEN)

Added `_sensor_prefix(ep) -> str` helper after `_emit_coverage_note` (~L441 in `quirk/cbom/builder.py`). Threaded into exactly 4 host:port-keyed derivation sites:

| Site | Line | Before | After |
|------|------|--------|-------|
| Pass 2 cert bom_ref | ~L711 | `crypto/certificate/{ep.host}:{ep.port}` | `crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}` |
| Pass 2b TLS surrogate lookup | ~L772 | `crypto/certificate/{ep.host}:{ep.port}` | `crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}` |
| Pass 3 SSH proto bom_ref | ~L858 | `crypto/protocol/ssh/{ep.host}:{ep.port}` | `crypto/protocol/ssh/{_sensor_prefix(ep)}{ep.host}:{ep.port}` |
| Pass 3 TLS proto bom_ref | ~L911 | `crypto/protocol/tls/{ep.host}:{ep.port}` | `crypto/protocol/tls/{_sensor_prefix(ep)}{ep.host}:{ep.port}` |

The CODE_SIGNING codesign/ fallback at ~L807/L811 was intentionally left unchanged.

All 34 `test_cbom_builder.py` tests pass (both new MERGE-03 tests green).

Commit: `c09f723`

## Verification

```
grep -n "_sensor_prefix" quirk/cbom/builder.py
441: def _sensor_prefix(ep) -> str:    ← 1 definition
711:     cert_bom_ref = f"crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}"
772:     bom_ref_val  = f"crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}"
858:     proto_bom_ref = f"crypto/protocol/ssh/{_sensor_prefix(ep)}{ep.host}:{ep.port}"
911:     proto_bom_ref = f"crypto/protocol/tls/{_sensor_prefix(ep)}{ep.host}:{ep.port}"

python -m compileall quirk/cbom/builder.py → 0
python -m pytest tests/test_cbom_builder.py -q → 34 passed
```

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The `sensor_id` value flows into an internal bom_ref string (JSON-internal CBOM), never rendered to HTML/SQL. T-110-02 (injection) disposition: accepted per plan threat model.

## Known Stubs

None.

## Lab Impact

No chaos lab profiles exercise multi-sensor merge scenarios yet — that is Phase 112 scope. No `labs/*/expected_results*.md` changes required for this plan.

## Self-Check: PASSED
