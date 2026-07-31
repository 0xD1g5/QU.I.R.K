"""Bridge topology detection for QUIRK hardware scanner.

Detects PQC-capable gateways co-located with legacy backends on the same /24
subnet and annotates each device dict with a conservative bridge_status value.

Phase 129 / HWCOMPAT-03. Phase 140 / BRIDGE-01 extends this with the first-ever
reachable "upstream_mitigated" promotion, gated on real SNMP evidence.

bridge_status values produced by _detect_crypto_bridges():
  - "partial_only"        : PQC-capable gateway and legacy backend both present
                            on the same /24 subnet and both directly reachable.
  - "upstream_mitigated"  : NEVER assigned by _detect_crypto_bridges() itself —
                            only reachable via the separate, pure in-memory
                            _confirm_upstream_mitigation() sibling below, and
                            only when the paired gateway's stored SNMP ARP-table
                            evidence (bridge_evidence_json) shows the legacy
                            backend's own IP present as a target_ip in that
                            gateway's ipNetToMediaTable. NEVER promoted on
                            subnet co-presence alone.
  - None                  : device is not part of any detected bridge pair.
"""
from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PQC_CAPABLE: frozenset[str] = frozenset({"partial", "supported"})
_LEGACY_STATUS: frozenset[str] = frozenset({"unsupported", "vendor-silent", "unknown"})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _subnet_24(ip: str) -> str:
    """Return the /24 prefix of *ip*, or *ip* unchanged for non-IPv4 addresses.

    Examples::

        _subnet_24("192.168.1.42") -> "192.168.1"
        _subnet_24("::1")          -> "::1"
        _subnet_24("bad")          -> "bad"
    """
    parts = ip.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return ".".join(parts[:3])
    return ip


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


def _detect_crypto_bridges(hw_devices: list[dict]) -> list[dict]:
    """Annotate each hw_device dict with a transient ``bridge_status`` key.

    Uses a /24 subnet heuristic: if a PQC-capable device (pqc_status in
    ``_PQC_CAPABLE``) and a legacy device (pqc_status in ``_LEGACY_STATUS``)
    share the same /24 subnet prefix, both receive ``bridge_status="partial_only"``.

    bridge_status values:
      - ``"partial_only"``       : both gateway and backend are directly reachable
                                   on the same /24 (D-04 conservative invariant).
      - ``"upstream_mitigated"`` : reserved — NEVER auto-assigned in Phase 129.
      - ``None``                 : device is not part of any detected bridge pair.

    Non-mutation guarantee (D-02):
        Returns new dicts; the original input dicts are never modified. Input
        dicts are shared with HTML/PDF/DOCX renderers — mutation would inject
        unexpected ``bridge_status`` keys into those rendering contexts.

    Conservative invariant (D-04):
        If both a PQC-capable gateway and a legacy backend appear in
        ``hw_devices`` on the same /24, the gateway ALWAYS receives
        ``"partial_only"`` — NEVER ``"upstream_mitigated"``.

    Args:
        hw_devices: List of hw_device dicts. Each must contain at least
            ``"host"`` (str) and ``"pqc_status"`` (str) keys.

    Returns:
        A new list of new dicts, each containing all original keys plus
        ``bridge_status``.
    """
    # Step 1: build subnet index {prefix -> [device_index, ...]}
    subnet_to_devices: dict[str, list[int]] = {}
    for i, dev in enumerate(hw_devices):
        prefix = _subnet_24(dev.get("host", ""))
        subnet_to_devices.setdefault(prefix, []).append(i)

    # Step 2: build bridge_assignments {device_index -> bridge_status_str}
    bridge_assignments: dict[int, str] = {}

    for prefix, indices in subnet_to_devices.items():
        # Singleton subnets cannot form a bridge pair
        if len(indices) < 2:
            continue

        pqc_indices = [
            i for i in indices
            if hw_devices[i].get("pqc_status", "").lower() in _PQC_CAPABLE
        ]
        legacy_indices = [
            i for i in indices
            if hw_devices[i].get("pqc_status", "").lower() in _LEGACY_STATUS
        ]

        # Only assign when both sides are present — D-04: always "partial_only"
        if pqc_indices and legacy_indices:
            for i in pqc_indices + legacy_indices:
                bridge_assignments[i] = "partial_only"
        # NOTE: "upstream_mitigated" is NEVER assigned here (D-04 / HWCOMPAT-SNMP-DEFER)

    # Step 3: build result list with shallow-copied dicts (D-02 no-mutation guarantee)
    result: list[dict] = []
    for i, dev in enumerate(hw_devices):
        annotated = dict(dev)  # shallow copy — never mutates input
        annotated["bridge_status"] = bridge_assignments.get(i)  # None if not in pair
        result.append(annotated)

    return result


# ---------------------------------------------------------------------------
# Console-side promotion (Phase 140 / BRIDGE-01, BRIDGE-04)
# ---------------------------------------------------------------------------


def _has_sufficient_evidence(dev: dict, hw_devices: list[dict]) -> bool:
    """Return True when a paired PQC-capable gateway's stored ARP evidence
    proves the legacy backend *dev* is reachable through it (Pitfall-2
    approach a — IP presence in the gateway's ipNetToMediaTable is the
    evidence bar; no MAC-collection/correlation is required).

    Evidence interpretation (D-01 / Pitfall-2 approach a):
        A gateway's ``bridge_evidence_json`` column stores a JSON list of
        raw ARP-table facts collected by the sensor-side walk probe, each
        shaped like ``{"target_ip": "...", "mac": "..."}``. This helper
        parses every device in *hw_devices* that shares *dev*'s /24 subnet
        and is itself a PQC-capable gateway (bridge_status == "partial_only"),
        and returns True as soon as one such gateway's evidence list contains
        *dev*'s own host IP as a ``target_ip``. Subnet co-presence alone
        (i.e. both devices merely being paired by ``_detect_crypto_bridges``)
        is NEVER sufficient by itself — the IP must actually appear in the
        gateway's own collected ARP-table evidence.

    Zero network I/O: this function only reads already-collected dict data.

    Args:
        dev: The candidate device dict (already has bridge_status ==
            "partial_only" when this is called from _confirm_upstream_mitigation).
        hw_devices: The full annotated device list (post _detect_crypto_bridges),
            used to find dev's paired gateway(s) on the same /24 subnet.

    Returns:
        True if a paired gateway's stored ARP evidence lists dev's host IP.
    """
    host = dev.get("host", "")
    prefix = _subnet_24(host)

    for other in hw_devices:
        if other.get("host", "") == host:
            continue  # never self-match (identity is unreliable post-shallow-copy)
        if other.get("bridge_status") != "partial_only":
            continue
        if _subnet_24(other.get("host", "")) != prefix:
            continue
        if other.get("pqc_status", "").lower() not in _PQC_CAPABLE:
            continue  # only gateways (PQC-capable side) carry ARP evidence

        evidence_raw = other.get("bridge_evidence_json")
        if not evidence_raw:
            continue
        try:
            facts = json.loads(evidence_raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(facts, list):
            continue
        for fact in facts:
            if isinstance(fact, dict) and fact.get("target_ip") == host:
                return True

    return False


def _confirm_upstream_mitigation(hw_devices: list[dict]) -> list[dict]:
    """Promote bridge_status "partial_only" -> "upstream_mitigated" ONLY when
    evidence-backed (Phase 140 / BRIDGE-01).

    Must be called strictly AFTER _detect_crypto_bridges() — it only
    considers devices whose bridge_status is already "partial_only" and
    looks up the paired gateway's stored SNMP ARP-table evidence to decide
    whether promotion is warranted (see _has_sufficient_evidence's docstring
    for the exact IP-presence-in-ARP-table evidence interpretation).

    Insufficient-evidence handling (D-05):
        When the probe never ran, the gateway was unreachable, or the ARP
        table simply doesn't show the expected entry, the device silently
        stays "partial_only" — there is no third rendered state.

    Zero network I/O (D-02 / BRIDGE-04 hard constraint):
        This function is pure over already-collected dict data. It imports
        no SNMP/network module and makes no network calls.

    Non-mutation guarantee (matches _detect_crypto_bridges' contract):
        Returns new dicts; the original input dicts are never modified.

    Args:
        hw_devices: List of hw_device dicts, already annotated with
            bridge_status by _detect_crypto_bridges() (and optionally
            carrying "bridge_evidence_json" / "bridge_confirmed_at" keys
            sourced from HardwareDevice rows).

    Returns:
        A new list of new dicts; bridge_status is promoted to
        "upstream_mitigated" only where evidence-backed.
    """
    result: list[dict] = []
    for dev in hw_devices:
        annotated = dict(dev)  # shallow copy — never mutates input
        if annotated.get("bridge_status") == "partial_only" and _has_sufficient_evidence(
            annotated, hw_devices
        ):
            annotated["bridge_status"] = "upstream_mitigated"
        result.append(annotated)

    return result
