"""Bridge topology detection for QUIRK hardware scanner.

Detects PQC-capable gateways co-located with legacy backends on the same /24
subnet and annotates each device dict with a conservative bridge_status value.

Phase 129 / HWCOMPAT-03.

bridge_status values produced by _detect_crypto_bridges():
  - "partial_only"        : PQC-capable gateway and legacy backend both present
                            on the same /24 subnet and both directly reachable.
  - "upstream_mitigated"  : reserved; NEVER auto-assigned in Phase 129 (requires
                            SNMP/routing data, deferred to v5.8).
  - None                  : device is not part of any detected bridge pair.
"""
from __future__ import annotations

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
    if len(parts) == 4:
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
