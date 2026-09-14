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
from sqlalchemy import func

from quirk.intelligence.key_reuse import compute_key_reuse_clusters
from quirk.models import CryptoEndpoint
from quirk.models_util import latest_successful_hardware_devices


def _device_label(host: str, vendor: str | None, model: str | None) -> str:
    """Return a human-readable device label for evidence strings.

    Falls back to *host* when neither vendor nor model is known — never
    fabricates a name (D-06 honest-absence convention shared with
    ``quirk/models.py``'s ``HardwareDevice`` "Unknown" vendor default).
    """
    parts = [p for p in (vendor, model) if p and p != "Unknown"]
    return " ".join(parts) if parts else host


def derive_key_reuse_edges(
    session: Any, scan_run_id: Any = None
) -> List[Dict[str, Any]]:
    """Derive key-reuse edges from ``compute_key_reuse_clusters`` VERBATIM.

    Each cluster contributes one edge per unique pair of members (all-pairs
    — the common cluster size is 2-3 members, per 195-RESEARCH.md Open
    Question 1's recommendation). Node ids are ``f"{host}:{port}"``.

    ``scan_run_id`` scopes the underlying cluster derivation to one scan. See
    ``compute_key_reuse_clusters``' docstring for why the default is unscoped.

    Two invariants are enforced on the way out, UNCONDITIONALLY — they hold
    even for an unscoped call, so a caller that legitimately wants cross-scan
    edges still cannot produce a self-loop or a repeated pair:

    1. **No self-edges.** An endpoint is never "key-reuse related" to itself.
       Before 2026-09-14 these were 32% of the rendered graph (390 of 1225 on
       the multihost estate): node ids are ``f"{host}:{port}"``, one endpoint
       yields one row per scan run, and all-pairs paired those rows against
       each other — every such pair collapsing to ``A -> A``.
    2. **No duplicate pairs.** Deduplicated on ``(source, target, edge_type)``
       treating the pair as unordered. 1169 of those 1225 edges (95%) were
       duplicate rows describing just 56 distinct pairs.

    Returns ``[]`` when there is no key reuse — never omitted, never
    fabricated.
    """
    result = compute_key_reuse_clusters(session, scan_run_id=scan_run_id)
    edges: List[Dict[str, Any]] = []
    seen_pairs: set[tuple[str, str, str]] = set()

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
                source = f"{a['host']}:{a['port']}"
                target = f"{b['host']}:{b['port']}"
                if source == target:
                    continue  # invariant 1
                pair_key = (*sorted((source, target)), "key_reuse")
                if pair_key in seen_pairs:
                    continue  # invariant 2
                seen_pairs.add(pair_key)
                edges.append(
                    {
                        "source": source,
                        "target": target,
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


def _ca_node_id(issuer: str) -> str:
    """Stable node id for a certificate-authority hub.

    Prefixed ``ca:`` so it can never collide with an endpoint id, which is
    always ``host:port``. The full issuer DN is kept in the id rather than a
    hash so the id stays human-readable in API output and test failures.
    """
    return f"ca:{issuer}"


def _ca_label(issuer: str) -> str:
    """Human label for a CA hub — the CN when there is one, else the full DN.

    Issuer DNs are long (``CN=ChaosLab-RootCA,OU=CA,O=ChaosLab,L=Lab,ST=NY,C=US``)
    and a graph node cannot show that legibly. The CN is the part an operator
    recognises. Falls back to the whole DN rather than truncating blindly, so a
    DN with no CN is never rendered as a misleading fragment.
    """
    for part in (issuer or "").split(","):
        part = part.strip()
        if part.upper().startswith("CN="):
            return part[3:].strip() or issuer
    return issuer


def derive_shared_ca_edges(
    session: Any, scan_run_id: Any = None
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Derive shared-certificate-authority HUB nodes and their edges.

    Two or more endpoints whose certificates were issued by the same CA share a
    single point of compromise: the CA's signing key. That key is the highest-
    value quantum target in an estate — breaking it lets an attacker FORGE a
    trusted certificate for every dependant, without touching the endpoints and
    without any victim seeing an invalid certificate. It is a strictly larger
    blast radius than key reuse, and on the reference estate a strictly larger
    cluster (10 endpoints vs 5).

    **Hub shape, not all-pairs.** One node per CA with one edge per dependant.
    All-pairs over the 10-member group would be 45 edges and would rebuild the
    edge explosion that ``derive_key_reuse_edges``' scoping fix removed the same
    day. A hub is linear in members, and it reads as what it is: one CA, many
    dependants.

    Returns ``([], [])`` when no issuer has two or more endpoints — never
    omitted, never fabricated. A CA with a single dependant is NOT a shared
    point of compromise and produces no node.
    """
    query = session.query(
        CryptoEndpoint.cert_issuer, CryptoEndpoint.host, CryptoEndpoint.port
    ).filter(
        CryptoEndpoint.protocol == "TLS",
        CryptoEndpoint.cert_issuer.isnot(None),
        CryptoEndpoint.cert_issuer != "",
    )
    if scan_run_id is not None:
        query = query.filter(CryptoEndpoint.scan_run_id == scan_run_id)

    # Dedupe members per issuer: one endpoint scanned twice within a scope must
    # not become two dependants (the same defect class as the key-reuse
    # self-edges).
    members_by_issuer: Dict[str, set] = {}
    for issuer, host, port in query.all():
        members_by_issuer.setdefault(issuer, set()).add(f"{host}:{port}")

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Largest blast radius first, issuer ascending as a deterministic
    # tiebreaker — mirrors compute_key_reuse_clusters' D-04 ordering.
    for issuer in sorted(
        members_by_issuer, key=lambda i: (-len(members_by_issuer[i]), i)
    ):
        members = sorted(members_by_issuer[issuer])
        if len(members) < 2:
            continue
        hub_id = _ca_node_id(issuer)
        nodes.append(
            {
                "id": hub_id,
                "label": _ca_label(issuer),
                "is_crown_jewel": False,
                "node_type": "ca",
            }
        )
        evidence = (
            f"Shared certificate authority: {len(members)} endpoints present "
            f"certificates issued by {issuer}. Compromise of this CA's signing "
            f"key allows forging a trusted certificate for every one of them."
        )
        for member in members:
            edges.append(
                {
                    "source": hub_id,
                    "target": member,
                    "edge_type": "shared_ca",
                    "evidence": evidence,
                }
            )

    return nodes, edges


def latest_scan_run_id(session: Any) -> Any:
    """The most recent ``scan_run_id`` present on any endpoint, or None.

    Resolved by ``MAX(scan_run_id)`` on the stored ISO-8601 key, NOT by the
    ``SESSION_BRACKET`` time-window used by
    ``quirk/dashboard/api/routes/scan.py::get_latest_scan``. That window
    deliberately spans multiple ``scan_run_id`` values to accommodate legacy
    NULL-keyed rows, and it is the mechanism by which two scans taken less than
    five minutes apart merge into one apparent result. The exposure map needs
    exactly one scan, so it must not inherit that behaviour.

    Returns None when no row carries a ``scan_run_id`` (an all-legacy
    database), which callers treat as "do not scope" rather than "scope to
    nothing" — scoping to nothing would render an empty map and read as
    verified zero exposure.
    """
    return (
        session.query(func.max(CryptoEndpoint.scan_run_id)).scalar()
    )


def derive_exposure_map(
    session: Any,
    scan_run_id: Any = None,
    crown_jewels: Any = None,
) -> Dict[str, Any]:
    """Derive the full v1 exposure map: nodes + verified-only edges.

    ``scan_run_id`` selects the scan to describe. When omitted, the LATEST
    scan is resolved and used — the map answers "the estate as this scan found
    it", so aggregating every scan in the database is not a neutral default.
    Before 2026-09-14 it did exactly that: on a 24-scan database the map
    rendered 1225 edges across 27 nodes, including a host with zero rows in the
    scan being displayed, where the scoped answer is 19 edges across 12 nodes.

    Pass a ``scan_run_id`` explicitly to pin the map to the same scan another
    surface is showing.

    Returns, with BOTH keys ALWAYS present (never sparse):
        {
            "nodes": [{"id": str, "label": str, "is_crown_jewel": bool}, ...],
            "edges": [{"source": str, "target": str, "edge_type": str,
                       "evidence": str}, ...],
        }

    ``crown_jewels`` is the operator's declaration of which systems matter —
    hosts / IPs / FQDNs, matched against the HOST portion of each endpoint node
    id, so declaring ``10.80.0.20`` marks ``10.80.0.20:443``. No probe can
    discover which system a client cares about, so this is declared and never
    inferred; an empty list marks nothing, which is honest absence rather than
    a guess at the "most important" host (195-RESEARCH.md Pitfall 3).

    CA hub nodes are never crown jewels — a crown jewel is a system the client
    owns and cares about, not an issuer identity.

    Read-only: this function persists nothing and performs no writes.
    """
    if scan_run_id is None:
        scan_run_id = latest_scan_run_id(session)

    key_reuse_edges = derive_key_reuse_edges(session, scan_run_id=scan_run_id)
    ca_nodes, shared_ca_edges = derive_shared_ca_edges(
        session, scan_run_id=scan_run_id
    )
    # derive_hardware_bridge_edges is deliberately NOT given scan_run_id: it
    # reads HardwareDevice rows through latest_successful_hardware_devices(),
    # which already resolves its own latest-per-host scope, and it already
    # carries a seen_pairs dedupe. Measured 2026-09-14, every one of the 1225
    # defective edges was key_reuse — this path contributed none of them.
    hardware_bridge_edges = derive_hardware_bridge_edges(session)
    edges = key_reuse_edges + shared_ca_edges + hardware_bridge_edges

    # Match on the HOST portion: a declaration names a system, not a port.
    # rsplit(":", 1) because IPv6 literals contain colons — only the final
    # separator is the port.
    declared = {h.strip() for h in (crown_jewels or []) if h and h.strip()}

    ca_node_ids = {n["id"] for n in ca_nodes}
    node_ids: List[str] = []
    seen_ids: set[str] = set(ca_node_ids)
    for edge in edges:
        for node_id in (edge["source"], edge["target"]):
            if node_id not in seen_ids:
                seen_ids.add(node_id)
                node_ids.append(node_id)

    endpoint_nodes = [
        {
            "id": node_id,
            "label": node_id,
            "is_crown_jewel": node_id.rsplit(":", 1)[0] in declared,
            "node_type": "endpoint",
        }
        for node_id in node_ids
    ]

    # CA hubs first so a renderer that draws in order puts the hubs down before
    # their dependants; both lists are otherwise independent.
    return {"nodes": ca_nodes + endpoint_nodes, "edges": edges}
