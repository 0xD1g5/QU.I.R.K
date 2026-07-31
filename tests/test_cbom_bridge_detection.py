"""RED scaffold for HWCOMPAT-03 bridge detection invariants.

This file is intentionally RED and will fail with ImportError until
``quirk/cbom/bridge.py`` is created in Plan 129-01.  Do NOT attempt to fix
these failures at the scaffold stage — the ImportError is the correct outcome.

Phase 140 / BRIDGE-01/04/05 adds coverage for the console-side
``_confirm_upstream_mitigation()`` promotion sibling: evidence-gated
promotion, D-05 silent-stay on insufficient evidence, non-mutation,
zero-network-I/O, and the BRIDGE-05 SCORE_WEIGHTS isolation guard.
"""
from __future__ import annotations

import json
from unittest.mock import patch

from quirk.cbom.bridge import _detect_crypto_bridges, _confirm_upstream_mitigation  # RED: module does not exist yet


# ---------------------------------------------------------------------------
# Helper fixture
# ---------------------------------------------------------------------------


def _make_hw_dict(host: str, pqc_status: str) -> dict:
    return {
        "host": host,
        "port": 22,
        "vendor": "TestVendor",
        "model": "TestModel",
        "pqc_status": pqc_status,
        "remediation_tier": "Tier 1",
    }


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------


def test_both_directly_reachable_is_partial_only():
    """HWCOMPAT-03 / D-04: both directly scanned on same /24 → partial_only."""
    devices = [
        _make_hw_dict("192.168.1.1", "supported"),
        _make_hw_dict("192.168.1.2", "unsupported"),
    ]
    result = _detect_crypto_bridges(devices)
    assert result[0]["bridge_status"] == "partial_only"
    assert result[1]["bridge_status"] == "partial_only"


def test_upstream_mitigated_not_auto_assigned():
    """HWCOMPAT-03 / D-04: upstream_mitigated is never auto-assigned by
    _detect_crypto_bridges() alone; lone PQC device → None. A partial_only
    pair without evidence must also never be promoted by subnet co-presence
    alone (Phase 140 corrected invariant — see test_confirm_upstream_promotes_*
    below for the full evidence-gated behavior)."""
    devices = [_make_hw_dict("192.168.1.1", "supported")]
    result = _detect_crypto_bridges(devices)
    assert result[0]["bridge_status"] is None

    # Co-presence alone (no evidence) must never promote via _detect_crypto_bridges.
    paired = [
        _make_hw_dict("192.168.1.1", "supported"),
        _make_hw_dict("192.168.1.2", "unsupported"),
    ]
    paired_result = _detect_crypto_bridges(paired)
    assert paired_result[0]["bridge_status"] == "partial_only"
    assert paired_result[1]["bridge_status"] == "partial_only"
    assert "upstream_mitigated" not in {d["bridge_status"] for d in paired_result}


def test_cross_subnet_not_paired():
    """HWCOMPAT-03: devices on different /24 subnets must not be paired."""
    devices = [
        _make_hw_dict("192.168.1.1", "supported"),
        _make_hw_dict("10.0.0.1", "unsupported"),
    ]
    result = _detect_crypto_bridges(devices)
    assert result[0]["bridge_status"] is None
    assert result[1]["bridge_status"] is None


def test_pqc_status_case_insensitive():
    """HWCOMPAT-03 / Pitfall 4: pqc_status comparison must be case-insensitive."""
    devices = [
        _make_hw_dict("192.168.1.1", "partial"),
        _make_hw_dict("192.168.1.2", "VENDOR-SILENT"),
    ]
    result = _detect_crypto_bridges(devices)
    assert result[0]["bridge_status"] == "partial_only"
    assert result[1]["bridge_status"] == "partial_only"


def test_empty_devices_returns_empty():
    """HWCOMPAT-03: empty input returns empty output without error."""
    result = _detect_crypto_bridges([])
    assert result == []


def test_input_dicts_not_mutated():
    """HWCOMPAT-03 / D-02: input dicts must not be mutated; callers share them with HTML/PDF renderers."""
    device = _make_hw_dict("192.168.1.1", "supported")
    _detect_crypto_bridges([device])
    assert "bridge_status" not in device  # IN-01: check device itself, not a copy


# ---------------------------------------------------------------------------
# Phase 140 / BRIDGE-01/04/05: _confirm_upstream_mitigation() coverage
# ---------------------------------------------------------------------------


def _make_gateway_dict(host: str, pqc_status: str, evidence: list[dict] | None) -> dict:
    d = _make_hw_dict(host, pqc_status)
    d["bridge_evidence_json"] = json.dumps(evidence) if evidence is not None else None
    return d


def test_confirm_upstream_promotes_with_matching_ip_evidence():
    """Happy path (D-01/BRIDGE-01): gateway's ARP evidence lists the legacy
    backend's own IP as a target_ip -> promoted to upstream_mitigated."""
    gateway = _make_gateway_dict(
        "192.168.1.1", "supported", evidence=[{"target_ip": "192.168.1.2", "mac": "aa:bb:cc:dd:ee:ff"}]
    )
    legacy = _make_gateway_dict("192.168.1.2", "unsupported", evidence=None)
    devices = [gateway, legacy]

    paired = _detect_crypto_bridges(devices)
    result = _confirm_upstream_mitigation(paired)

    by_host = {d["host"]: d for d in result}
    assert by_host["192.168.1.1"]["bridge_status"] == "upstream_mitigated"
    assert by_host["192.168.1.2"]["bridge_status"] == "upstream_mitigated"


def test_confirm_upstream_stays_partial_only_without_evidence():
    """D-05: evidence-absent case (empty/missing bridge_evidence_json) must
    silently stay partial_only — no third rendered state."""
    gateway = _make_gateway_dict("192.168.1.1", "supported", evidence=None)
    legacy = _make_gateway_dict("192.168.1.2", "unsupported", evidence=None)
    devices = [gateway, legacy]

    paired = _detect_crypto_bridges(devices)
    result = _confirm_upstream_mitigation(paired)

    for d in result:
        assert d["bridge_status"] == "partial_only"


def test_confirm_upstream_stays_partial_only_when_evidence_lacks_ip():
    """Evidence present but does not list the legacy backend's IP -> stays
    partial_only (evidence must match the specific IP, not merely exist)."""
    gateway = _make_gateway_dict(
        "192.168.1.1", "supported", evidence=[{"target_ip": "192.168.1.99", "mac": "aa:bb:cc:dd:ee:ff"}]
    )
    legacy = _make_gateway_dict("192.168.1.2", "unsupported", evidence=None)
    devices = [gateway, legacy]

    paired = _detect_crypto_bridges(devices)
    result = _confirm_upstream_mitigation(paired)

    for d in result:
        assert d["bridge_status"] == "partial_only"


def test_confirm_upstream_mitigation_does_not_mutate_input():
    """Non-mutation contract: input dicts (post _detect_crypto_bridges) are
    never modified by _confirm_upstream_mitigation."""
    gateway = _make_gateway_dict(
        "192.168.1.1", "supported", evidence=[{"target_ip": "192.168.1.2", "mac": "aa:bb:cc:dd:ee:ff"}]
    )
    legacy = _make_gateway_dict("192.168.1.2", "unsupported", evidence=None)
    paired = _detect_crypto_bridges([gateway, legacy])
    snapshot = [dict(d) for d in paired]

    _confirm_upstream_mitigation(paired)

    assert paired == snapshot


def test_confirm_upstream_mitigation_zero_network_io():
    """BRIDGE-04 hard constraint: _confirm_upstream_mitigation makes ZERO
    network calls. Patch the SNMP scanner's probe/walk functions and assert
    none of them are ever invoked."""
    gateway = _make_gateway_dict(
        "192.168.1.1", "supported", evidence=[{"target_ip": "192.168.1.2", "mac": "aa:bb:cc:dd:ee:ff"}]
    )
    legacy = _make_gateway_dict("192.168.1.2", "unsupported", evidence=None)
    paired = _detect_crypto_bridges([gateway, legacy])

    with patch("quirk.scanner.snmp_scanner.walk_arp_table") as mock_walk, \
         patch("quirk.scanner.snmp_scanner._async_walk_arp_table") as mock_async_walk, \
         patch("quirk.scanner.snmp_scanner._async_probe") as mock_probe, \
         patch("quirk.scanner.snmp_scanner._async_probe_v3") as mock_probe_v3:
        result = _confirm_upstream_mitigation(paired)

    assert result[0]["bridge_status"] == "upstream_mitigated"
    mock_walk.assert_not_called()
    mock_async_walk.assert_not_called()
    mock_probe.assert_not_called()
    mock_probe_v3.assert_not_called()


def test_confirm_upstream_mitigation_never_enters_score_weights():
    """BRIDGE-05: no SCORE_WEIGHTS key names bridge/upstream/mitigat, and
    promotion does not alter any score input."""
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    for key in SCORE_WEIGHTS:
        lowered = key.lower()
        assert "bridge" not in lowered
        assert "upstream" not in lowered
        assert "mitigat" not in lowered

    # Promotion must not add/alter any of the existing SCORE_WEIGHTS keys.
    before = dict(SCORE_WEIGHTS)
    gateway = _make_gateway_dict(
        "192.168.1.1", "supported", evidence=[{"target_ip": "192.168.1.2", "mac": "aa:bb:cc:dd:ee:ff"}]
    )
    legacy = _make_gateway_dict("192.168.1.2", "unsupported", evidence=None)
    paired = _detect_crypto_bridges([gateway, legacy])
    _confirm_upstream_mitigation(paired)
    assert SCORE_WEIGHTS == before
