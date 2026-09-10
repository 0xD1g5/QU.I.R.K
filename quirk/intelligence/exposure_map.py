"""Phase 195 (MAP-02): read-time quantum-exposure-map derivation.

The exposure map's defensibility rests entirely on every edge being a
VERIFIED relationship with cited evidence and zero inference (D-03). This
module is the single source of that guarantee for Tier A (the always-shipped
subset — key-reuse cluster edges + confirmed hardware crypto-bridge edges).
Tier B (operator-declared reachability) is spike-gated and NOT implemented
here (195-SPIKE-DECISION.md).

Mirroring ``quirk/intelligence/key_reuse.py``'s conventions:

- The two top-level return keys (``nodes``, ``edges``) are ALWAYS present,
  never sparse, even when there are zero edges (D-08 honest-absence
  support) — a caller can distinguish "no verified relationships exist" from
  "this data was never computed".
- This module is READ-ONLY: it never writes, never commits, and has no
  scan-pipeline call site — it derives its edge set fresh, on every call,
  from source-of-truth tables (``CryptoEndpoint`` fingerprints via
  ``compute_key_reuse_clusters``, ``HardwareDevice`` rows via
  ``latest_successful_hardware_devices``). There is no persisted exposure-map
  table and no denormalized cache anywhere in this codebase (D-12).
- This module never imports ``quirk.intelligence.scoring`` and the data it
  returns never reaches the quantum-readiness score (D-10) — enforced
  permanently by ``tests/test_exposure_map_score_guard.py`` (195-03). The
  edge dict shape deliberately carries no top-level ``severity``, ``score``,
  ``host``, or ``port`` key (D-11) — only ``edge_type`` + a mandatory
  non-empty ``evidence`` citation string.
- Hardware-bridge edges are emitted ONLY for devices with
  ``bridge_status == "upstream_mitigated"`` — NEVER ``"partial_only"``
  (the subnet-heuristic co-location signal). Rendering a ``partial_only``
  pair as a confirmed edge is the fabricated-chain anti-feature this whole
  phase exists to prevent (D-03, Pitfall 2, T-195-02).
"""
from __future__ import annotations

from typing import Any, Dict, List

from quirk.cbom.bridge import (
    _confirm_upstream_mitigation,
    _detect_crypto_bridges,
    _find_matching_gateway,
)
from quirk.intelligence.key_reuse import compute_key_reuse_clusters
from quirk.models_util import latest_successful_hardware_devices


def _device_label(host: str, vendor: str | None, model: str | None) -> str:
    """Return a human-readable device label for evidence strings.

    Falls back to *host* when neither vendor nor model is known — never
    fabricates a name (D-06 honest-absence convention shared with
    ``quirk/models.py``'s ``HardwareDevice`` "Unknown" vendor default).
    """
    parts = [p for p in (vendor, model) if p and p != "Unknown"]
    return " ".join(parts) if parts else host


def derive_key_reuse_edges(session: Any) -> List[Dict[str, Any]]:
    """Derive key-reuse edges from ``compute_key_reuse_clusters`` VERBATIM.

    Each cluster contributes one edge per unique pair of members (all-pairs
    — the common cluster size is 2-3 members, per 195-RESEARCH.md Open
    Question 1's recommendation). Node ids are ``f"{host}:{port}"``.

    Returns ``[]`` when there is no key reuse — never omitted, never
    fabricated.
    """
    result = compute_key_reuse_clusters(session)
    edges: List[Dict[str, Any]] = []

    for cluster in result["clusters"]:
        fingerprint = cluster["fingerprint"]
        members = cluster["members"]
        evidence = (
            f"Key reuse: these endpoints share SPKI fingerprint "
            f"{fingerprint[:12]}. Source: Phase 191 key-reuse derivation."
        )
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a = members[i]
                b = members[j]
                edges.append(
                    {
                        "source": f"{a['host']}:{a['port']}",
                        "target": f"{b['host']}:{b['port']}",
                        "edge_type": "key_reuse",
                        "evidence": evidence,
                    }
                )

    return edges


def derive_hardware_bridge_edges(session: Any) -> List[Dict[str, Any]]:
    """Derive hardware crypto-bridge edges — STRICTLY ``upstream_mitigated``.

    ``partial_only`` (subnet co-location heuristic) NEVER produces an edge —
    that is the rejected fabricated-chain anti-feature this phase exists to
    prevent (D-03, Pitfall 2, T-195-02).

    Returns ``[]`` when there is no confirmed hardware bridge — never
    omitted, never fabricated.
    """
    devices = latest_successful_hardware_devices(session)
    if not devices:
        return []

    label_by_host: Dict[str, str] = {
        getattr(d, "host", "") or "": _device_label(
            getattr(d, "host", "") or "",
            getattr(d, "vendor", None),
            getattr(d, "model", None),
        )
        for d in devices
    }

    bridge_dicts = [
        {
            "host": getattr(d, "host", "") or "",
            "pqc_status": getattr(d, "pqc_status", "unknown") or "unknown",
            "bridge_evidence_json": getattr(d, "bridge_evidence_json", None),
        }
        for d in devices
    ]

    # NOTE: _find_matching_gateway must be called against the PRE-promotion
    # ("partial_only") list — the shared helper's subnet-group lookup filters
    # on bridge_status == "partial_only", matching the exact call shape
    # _confirm_upstream_mitigation itself uses internally.
    detected = _detect_crypto_bridges(bridge_dicts)
    confirmed = _confirm_upstream_mitigation(detected)
    detected_by_host = {d["host"]: d for d in detected}

    edges: List[Dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for dev in confirmed:
        # STRICT filter — the ONLY qualifying status string (D-03/Pitfall 2).
        # "partial_only" is deliberately excluded here, never emitted as an edge.
        if dev.get("bridge_status") != "upstream_mitigated":
            continue

        pre_dev = detected_by_host.get(dev["host"])
        if pre_dev is None:
            continue

        match = _find_matching_gateway(pre_dev, detected)
        if match is None:
            continue
        gateway, matched_ip = match

        gateway_host = gateway.get("host", "")
        if dev["host"] == gateway_host:
            # dev IS the matched gateway — matched_ip is the proven legacy backend.
            endpoint_a, endpoint_b = gateway_host, matched_ip
        else:
            # dev is the legacy backend — gateway_host is the matched gateway.
            endpoint_a, endpoint_b = gateway_host, dev["host"]

        pair_key = tuple(sorted((endpoint_a, endpoint_b)))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        device_name = label_by_host.get(gateway_host, gateway_host)
        evidence = (
            f"Confirmed hardware crypto-bridge: {device_name} bridges "
            f"{endpoint_a} to {endpoint_b}. Source: hardware inventory table."
        )
        edges.append(
            {
                "source": endpoint_a,
                "target": endpoint_b,
                "edge_type": "hardware_bridge",
                "evidence": evidence,
            }
        )

    return edges


def derive_exposure_map(session: Any) -> Dict[str, Any]:
    """Derive the full v1 exposure map: nodes + verified-only edges.

    Returns, with BOTH keys ALWAYS present (never sparse):
        {
            "nodes": [{"id": str, "label": str, "is_crown_jewel": bool}, ...],
            "edges": [{"source": str, "target": str, "edge_type": str,
                       "evidence": str}, ...],
        }

    ``is_crown_jewel`` always defaults ``False`` here — no live crown-jewel
    declaration data exists until Tier B ships (honest absence, not a
    fabricated default; 195-RESEARCH.md Pitfall 3).

    Read-only: this function persists nothing and performs no writes.
    """
    key_reuse_edges = derive_key_reuse_edges(session)
    hardware_bridge_edges = derive_hardware_bridge_edges(session)
    edges = key_reuse_edges + hardware_bridge_edges

    node_ids: List[str] = []
    seen_ids: set[str] = set()
    for edge in edges:
        for node_id in (edge["source"], edge["target"]):
            if node_id not in seen_ids:
                seen_ids.add(node_id)
                node_ids.append(node_id)

    nodes = [
        {"id": node_id, "label": node_id, "is_crown_jewel": False}
        for node_id in node_ids
    ]

    return {"nodes": nodes, "edges": edges}
