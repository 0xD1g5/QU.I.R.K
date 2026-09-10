---
phase: 195-quantum-exposure-map
plan: 03
subsystem: intelligence
tags: [exposure-map, score-firewall, evidence-required, test-guard, zero-fabrication]
requires:
  - 195-02 (quirk/intelligence/exposure_map.py: derive_exposure_map, derive_key_reuse_edges, derive_hardware_bridge_edges)
provides:
  - tests/test_exposure_map_score_guard.py (D-10 permanent score-firewall guard)
  - tests/test_exposure_map_edges.py (D-11/D-12 zero-inferred-edges + no-denormalized-table guard)
affects:
  - Any future edit to quirk/intelligence/exposure_map.py or quirk/intelligence/scoring.py (both guard files run in every full-suite CI pass)
tech-stack:
  added: []
  patterns:
    - "4-assertion score-firewall guard (SCORE_WEIGHTS key check + AST import-walk + negative control + structural-contract), copied near-verbatim from tests/test_key_reuse_score_guard.py per D-10/Pitfall 4"
    - "Dedicated NEW guard file per subsystem — never extend an existing guard file"
key-files:
  created:
    - tests/test_exposure_map_score_guard.py
    - tests/test_exposure_map_edges.py
  modified: []
decisions:
  - "Firewall test file is 100% new — no edit touched tests/test_cve_score_guard.py or tests/test_key_reuse_score_guard.py (verified via git diff --stat against both files across this plan's two commits: empty diff)"
  - "Forbidden SCORE_WEIGHTS substrings for D-10: exposure_map, reachability, crown_jewel (matched case-insensitively), per plan interface spec"
  - "Partial_only exclusion regression seeds the SAME (10.0.5.1 gateway, 10.0.5.2 legacy backend) pair twice in two independent isolated sessions: once with gateway_evidence_json=None (stays partial_only, asserts zero edges) and once with a JSON ARP-table fact naming the legacy backend's IP (promotes to upstream_mitigated, asserts exactly one edge) — proving the exclusion is the filter, not an accident of empty data (Pitfall 2, T-195-02)"
  - "D-12 structural check greps quirk/*.py at test-run time for __tablename__ values matching exposure.*(edge|map) and _ensure_columns calls referencing 'exposure' — a run-time scan rather than a hand-derived file list, matching this repo's established gotcha that hand-derived enumeration lists silently miss instances (CLAUDE.md TOOL-04/05 precedent)"
  - "test_exposure_map_score_guard.py's structural-contract assertion (assertion 4) duplicates a lightweight non-empty-evidence check as belt-and-suspenders alongside the dedicated, more thorough evidence-required guard in test_exposure_map_edges.py — intentional overlap, not redundant: the two files protect different failure surfaces (score leak vs. fabricated edge) even though one assertion touches both"
metrics:
  duration: "~25 min"
  completed: "2026-09-09"
---

# Phase 195 Plan 03: Exposure-Map Score-Firewall + Zero-Inferred-Edges Guards Summary

Two new, permanent pytest guard files that make MAP-03's zero-fabrication and score-neutrality
claims machine-enforced rather than aspirational: `tests/test_exposure_map_score_guard.py` proves
`quirk/intelligence/exposure_map.py` can never leak into `SCORE_WEIGHTS` or import
`quirk.intelligence.scoring` (D-10), and `tests/test_exposure_map_edges.py` proves every derived
edge carries cited evidence and that `partial_only` hardware co-location can never be rendered as
a confirmed edge (D-11/D-12, Pitfall 2).

## What Was Built

### Task 1: `tests/test_exposure_map_score_guard.py` (D-10 firewall, NEW file)

Copied the 4-assertion structure of `tests/test_key_reuse_score_guard.py` near-verbatim, adapted
for the exposure-map module:

1. `test_score_weights_has_no_exposure_map_key` — asserts no `SCORE_WEIGHTS` key contains
   `exposure_map`, `reachability`, or `crown_jewel` (case-insensitive substring match).
2. `test_exposure_map_module_never_imports_scoring` — AST-walks
   `quirk/intelligence/exposure_map.py`'s own source, asserting no `Import`/`ImportFrom` node
   resolves to `quirk.intelligence.scoring` or `scoring`.
3. `test_negative_control_ast_walk_detects_a_real_forbidden_import` — runs the identical checker
   against three fixture source strings (plain `import`, `from ... import`, and a clean
   comment-only decoy), proving the AST walk CAN detect a real violation and does NOT false-positive
   on prose mentioning the module name.
4. `test_derive_exposure_map_result_has_no_finding_shaped_keys` — seeds a real key-reuse cluster
   via `make_isolated_memory_engine()`, calls the real `derive_exposure_map`, and asserts the
   top-level result carries no `severity`/`host`/`port` key, plus a lightweight non-empty-evidence
   check on every edge.

### Task 2: `tests/test_exposure_map_edges.py` (D-11/D-12 evidence + partial_only exclusion, NEW file)

Four guards:

1. `test_every_exposure_map_edge_has_evidence` — seeds both a key-reuse cluster (two
   `CryptoEndpoint` rows sharing an SPKI fingerprint) and a confirmed hardware bridge pair
   (`upstream_mitigated`), calls `derive_exposure_map`, and asserts every edge in the mixed
   `key_reuse` + `hardware_bridge` result set has a non-empty string `evidence` field.
2. `test_partial_only_devices_produce_zero_edges` — the named regression test required by the
   plan. Seeds a PQC-capable gateway (`10.0.5.1`, `pqc_status="supported"`) and a legacy backend
   (`10.0.5.2`, `pqc_status="unsupported"`) on the same `/24` subnet, twice, in two independent
   `make_isolated_memory_engine()` sessions:
   - Branch 1: gateway has no `bridge_evidence_json` -> can only reach `bridge_status ==
     "partial_only"` -> `derive_hardware_bridge_edges` returns `[]`.
   - Branch 2: same pair, gateway's `bridge_evidence_json` is a JSON list naming
     `10.0.5.2` as a `target_ip` -> promotes to `"upstream_mitigated"` -> exactly one edge.
3. `test_no_denormalized_exposure_table` — greps every `.py` file under `quirk/` at test-run time
   for `__tablename__` values matching `exposure.*(edge|map)` and `_ensure_columns` calls
   referencing `exposure`, asserting the offending list is empty (D-12).
4. `test_empty_session_returns_present_empty_keys` — `derive_exposure_map` on an empty session
   returns `{"nodes": [], "edges": []}` with both keys present (D-08 honest-absence support).

## Verification

```
.venv/bin/python -m pytest -q tests/test_exposure_map_score_guard.py tests/test_exposure_map_edges.py tests/test_cve_score_guard.py tests/test_key_reuse_score_guard.py
36 passed, 2 warnings in 0.45s
```

`git diff --stat` across this plan's two commits confirms zero changes to
`tests/test_cve_score_guard.py` and `tests/test_key_reuse_score_guard.py` — both new files are
fully independent (Pitfall 4).

## Deviations from Plan

None — plan executed exactly as written. Both files matched the interface spec's forbidden
substrings, module paths, and fixture seeding shapes (`CryptoEndpoint` fields per
`test_key_reuse_score_guard.py:142-163`; `HardwareDevice` fields per
`tests/test_hardware_projection_sites.py`'s established `host, port, vendor, pqc_status,
confidence, fingerprint_method, scanned_at, probe_status="success"` pattern).

## Known Stubs

None.

## Threat Flags

None — this plan adds only test files; no new network endpoint, auth path, file access pattern,
or schema change.

## Self-Check: PASSED

- FOUND: tests/test_exposure_map_score_guard.py
- FOUND: tests/test_exposure_map_edges.py
- FOUND commit 018a3003 (test(195-03): add exposure-map score-firewall guard)
- FOUND commit a4d62e72 (test(195-03): add exposure-map zero-inferred-edges guard)
