---
phase: 195-quantum-exposure-map
plan: 02
subsystem: intelligence
tags: [exposure-map, key-reuse, hardware-bridge, score-firewall, read-only-derivation]
requires:
  - 195-01 (MAP-01 spike DECISION: DEFERRED — Tier A proceeds regardless per D-14)
provides:
  - quirk.intelligence.exposure_map.derive_exposure_map
  - quirk.intelligence.exposure_map.derive_key_reuse_edges
  - quirk.intelligence.exposure_map.derive_hardware_bridge_edges
  - quirk.cbom.bridge._find_matching_gateway (shared evidence-matching helper)
affects:
  - quirk/dashboard/api/routes/exposure_map.py (195-04, not yet built — will call derive_exposure_map)
  - tests/test_exposure_map_score_guard.py / tests/test_exposure_map_edges.py (195-03, not yet built)
tech-stack:
  added: []
  patterns:
    - "Read-time derivation, zero persisted table (mirrors quirk/intelligence/key_reuse.py)"
    - "Signature-preserving refactor: extract shared predicate helper, wrap for the existing boolean caller"
key-files:
  created:
    - quirk/intelligence/exposure_map.py
  modified:
    - quirk/cbom/bridge.py
decisions:
  - "_find_matching_gateway returns (gateway_dict, matched_ip) | None (not just a bool) so exposure_map can build both endpoint identities from the exact same matched evidence _has_sufficient_evidence already trusts"
  - "Hardware-bridge edge derivation calls _find_matching_gateway against the PRE-promotion ('partial_only') device list, matching _confirm_upstream_mitigation's own internal call shape — the shared helper's subnet-group lookup filters on bridge_status=='partial_only', so calling it post-promotion would silently break the group match for a device that was itself just promoted"
  - "Node id scheme: key-reuse nodes use f'{host}:{port}' (per plan interface spec, matches CryptoEndpoint granularity); hardware-bridge nodes use bare host (matches the established {host, pqc_status, bridge_evidence_json} projection shape, which carries no port)"
  - "device_name in hardware-bridge evidence strings falls back to host when vendor/model are unknown or 'Unknown' — never fabricates a label (D-06 honest-absence convention)"
metrics:
  duration: "~45 minutes"
  completed: 2026-09-09
---

# Phase 195 Plan 02: Read-Time Exposure-Map Derivation Summary

Built the read-time backend module that derives QU.I.R.K.'s Tier-A exposure-map edge set — key-reuse
cluster edges (verbatim reuse of `compute_key_reuse_clusters`) plus confirmed hardware crypto-bridge
edges (strictly `bridge_status == "upstream_mitigated"`, never the `partial_only` subnet heuristic) —
with zero persisted table and a machine-verified firewall against the quantum-readiness score.

## What Was Built

### Task 1: Shared matched-gateway helper in `quirk/cbom/bridge.py`

Extracted the inner ARP-evidence-matching loop out of `_has_sufficient_evidence` (Phase 140/BRIDGE-01)
into a new module-level helper, `_find_matching_gateway(dev, hw_devices) -> tuple[dict, str] | None`,
which returns the matched gateway dict plus the specific legacy-backend IP proven reachable through it
(instead of a bare bool). `_has_sufficient_evidence` now delegates to the helper (`is not None`) and
keeps its exact signature and `bool` return type — its single caller, `_confirm_upstream_mitigation`,
and every existing `tests/test_cbom_bridge_detection.py` test are unaffected. The matching predicate
itself (subnet /24 gating via the partial_only subnet-group, JSON parse guards, `target_ip` set
membership, gateway-vs-legacy direction) is byte-identical to the pre-refactor inline version — only
its location and return shape moved. Verified: `.venv/bin/python -m compileall -q quirk/cbom/bridge.py`
exit 0; `pytest -q tests/ -k bridge` → 47 passed, 1 xfailed, 1 xpassed (unchanged from baseline).

### Task 2: `quirk/intelligence/exposure_map.py` (NEW)

Three functions, mirroring `key_reuse.py`'s honest-absence/read-only/score-firewall docstring
conventions:

- **`derive_key_reuse_edges(session)`** — calls `compute_key_reuse_clusters(session)` verbatim; for
  each cluster, emits one edge per unique pair of members (all-pairs — the RESEARCH-recommended
  approach for the common size-2/3 clusters). Node id = `f"{host}:{port}"`. Evidence string:
  `"Key reuse: these endpoints share SPKI fingerprint {fingerprint[:12]}. Source: Phase 191 key-reuse
  derivation."`
- **`derive_hardware_bridge_edges(session)`** — projects `latest_successful_hardware_devices(session)`
  into the established `{host, pqc_status, bridge_evidence_json}` dict shape (mirroring
  `scan.py:819-826`), runs `_confirm_upstream_mitigation(_detect_crypto_bridges(...))`, then for every
  device that lands at `bridge_status == "upstream_mitigated"` (STRICT — `partial_only` is excluded by
  construction, never checked as a positive condition) calls the Task-1 shared helper against the
  PRE-promotion list to recover the gateway/matched-IP pair, dedupes by canonical `(a, b)` pair so a
  gateway-side and legacy-side iteration never double-emit the same edge, and emits one
  `hardware_bridge` edge with evidence `"Confirmed hardware crypto-bridge: {device_name} bridges
  {endpoint_a} to {endpoint_b}. Source: hardware inventory table."`
- **`derive_exposure_map(session)`** — composes both sources into `{"nodes": [...], "edges": [...]}`,
  both keys always present even when empty. Node dicts are `{"id", "label", "is_crown_jewel"}`, with
  `is_crown_jewel` always `False` (no live crown-jewel declaration data exists — Tier B was deferred by
  the 195-01 spike).

No table, migration, or persisted cache is introduced. The module never imports
`quirk.intelligence.scoring` — verified by both the plan's AST-walk check and manual inspection.

## Verification Performed

- `.venv/bin/python -m compileall -q quirk` → exit 0 (whole tree, not just the two changed files).
- `.venv/bin/python -m pytest -q tests/ -k "bridge or key_reuse"` → 75 passed, 1 xfailed, 1 xpassed,
  zero failures.
- AST firewall check (from the plan's own `<verify>` block) → `firewall ok`, confirming zero
  `import`/`from` of `quirk.intelligence.scoring` anywhere in the new module.
- `grep -n "partial_only" quirk/intelligence/exposure_map.py` → all 6 hits are in docstrings/comments
  or the exclusion `continue` guard — never an emitted-edge condition.
- `grep -n "CREATE TABLE\|_ensure_columns\|__tablename__" quirk/intelligence/exposure_map.py` → empty.
- Manual behavior verification against an isolated in-memory SQLite session (not a committed test file
  — `tests/test_exposure_map_edges.py` is 195-03's deliverable), covering all five `<behavior>`
  promises from the plan:
  1. Empty session → `{"nodes": [], "edges": []}`.
  2. A 2-member key-reuse cluster → 1 edge, `edge_type == "key_reuse"`, evidence contains the
     fingerprint prefix.
  3. A gateway + legacy backend with matching ARP evidence (`upstream_mitigated`) → 1
     `hardware_bridge` edge naming both endpoints and the vendor/model device label.
  4. The identical topology WITHOUT ARP evidence (stays `partial_only`) → **zero** hardware-bridge
     edges — the fabricated-chain gate holds.
  5. Every edge dict confirmed to have a non-empty `evidence` string and no `severity`/`score`/
     `host`/`port` top-level key.

## Deviations from Plan

None — plan executed exactly as written. The plan's own wording ("RETURNS the matched gateway dict
(and the matched IP)") was interpreted as a `(gateway, matched_ip)` tuple return rather than a bare
gateway dict, since `exposure_map.py`'s edge construction needs both the gateway identity and the
specific proven-reachable backend IP to build the evidence string and node-pair — this is a
same-scope implementation-detail choice, not a deviation from any stated constraint.

## Known Stubs

None. Both derivation functions are fully wired to live source-of-truth tables
(`CryptoEndpoint`/`HardwareDevice`); no hardcoded empty defaults or placeholder text reach the return
shape except the honest `is_crown_jewel: False` default, which is documented as intentional
honest-absence (Tier B crown-jewel data does not exist yet).

## Threat Flags

None. This plan's only new surface is the `T-195-02`/`T-195-04`/`T-195-05` mitigations the plan's own
threat model already named — no new endpoint, auth path, file access, or schema change was
introduced.

## Self-Check: PASSED

- FOUND: `quirk/intelligence/exposure_map.py`
- FOUND: `quirk/cbom/bridge.py` (modified, `_find_matching_gateway` present)
- FOUND commit `86cb4df2` (Task 1: bridge.py refactor)
- FOUND commit `8b2291da` (Task 2: exposure_map.py)
