"""Phase 195 Plan 03 (MAP-03 / D-11 / D-12) — permanent regression guard: every
exposure-map edge must carry cited evidence, and hardware devices reaching
only "partial_only" bridge status must NEVER produce an edge.

NEW dedicated file, never extends any existing guard file.

Four guards, each protecting against a distinct fabrication path:

1. ``test_every_exposure_map_edge_has_evidence``: seeds both a key-reuse
   cluster and a confirmed (``upstream_mitigated``) hardware bridge pair,
   calls ``derive_exposure_map``, and asserts EVERY edge dict's ``evidence``
   field is a non-empty string. This is the machine enforcement of "zero
   inferred edges" (D-11) — an edge with no evidence cannot exist.
2. ``test_partial_only_devices_produce_zero_edges``: THE single most
   important zero-fabrication gate in this phase (Pitfall 2, T-195-02).
   Seeds a PQC-capable gateway + legacy backend co-located on the same /24
   subnet with NO SNMP ARP-table evidence — they can only ever reach
   ``bridge_status == "partial_only"`` — and asserts
   ``derive_hardware_bridge_edges`` returns ``[]``. It then seeds the SAME
   pair again, this time with the gateway's ``bridge_evidence_json``
   proving the legacy backend's IP is in its ARP table (the
   ``upstream_mitigated`` promotion path), and asserts exactly one edge is
   produced. Both branches together prove the exclusion is the filter, not
   an accident of empty data.
3. ``test_no_denormalized_exposure_table``: structural check asserting no
   new table/migration named like ``*exposure*edge*`` / ``*exposure*map*``
   exists anywhere in ``quirk/`` — D-12's read-time-only enforcement.
4. ``test_empty_session_returns_present_empty_keys``: ``derive_exposure_map``
   called against an empty session returns ``{"nodes": [], "edges": []}``
   with BOTH keys present — D-08 honest-absence support at the data layer.
"""
from __future__ import annotations

import json
import pathlib
import re

from sqlalchemy.orm import sessionmaker

from quirk.intelligence.exposure_map import (
    derive_exposure_map,
    derive_hardware_bridge_edges,
)
from quirk.models import CryptoEndpoint, HardwareDevice

from tests.conftest import make_isolated_memory_engine

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_QUIRK_DIR = _REPO_ROOT / "quirk"

_EXPOSURE_TABLE_NAME_RE = re.compile(r"exposure.*(edge|map)", re.IGNORECASE)


def _make_session():
    engine = make_isolated_memory_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session(), engine


def _seed_hardware_pair(session, *, gateway_evidence_json: str | None) -> None:
    """Seed one PQC-capable gateway + one legacy backend on the same /24.

    When *gateway_evidence_json* is None, the pair can only ever be detected
    as "partial_only" (no SNMP ARP-table proof). When it is a JSON list
    naming the legacy backend's IP as a target_ip, the pair is eligible for
    "upstream_mitigated" promotion.
    """
    scanned_at = __import__("datetime").datetime(2026, 1, 1)
    session.add_all(
        [
            HardwareDevice(
                host="10.0.5.1",
                port=502,
                vendor="Schneider Electric",
                model="Gateway-X",
                pqc_status="supported",
                confidence="high",
                fingerprint_method="modbus_probe",
                scanned_at=scanned_at,
                probe_status="success",
                bridge_evidence_json=gateway_evidence_json,
            ),
            HardwareDevice(
                host="10.0.5.2",
                port=502,
                vendor="Legacy Corp",
                model="Backend-Y",
                pqc_status="unsupported",
                confidence="high",
                fingerprint_method="modbus_probe",
                scanned_at=scanned_at,
                probe_status="success",
            ),
        ]
    )
    session.commit()


def test_every_exposure_map_edge_has_evidence() -> None:
    session, engine = _make_session()
    try:
        fp = "f" * 64
        session.add_all(
            [
                CryptoEndpoint(
                    host="a.example.com",
                    port=443,
                    protocol="TLS",
                    cert_spki_fingerprint=fp,
                    cert_subject="CN=example.com",
                    cert_pubkey_alg="RSA",
                    cert_pubkey_size=2048,
                ),
                CryptoEndpoint(
                    host="b.example.com",
                    port=443,
                    protocol="TLS",
                    cert_spki_fingerprint=fp,
                    cert_subject="CN=example.com",
                    cert_pubkey_alg="RSA",
                    cert_pubkey_size=2048,
                ),
            ]
        )
        _seed_hardware_pair(
            session,
            gateway_evidence_json=json.dumps([{"target_ip": "10.0.5.2", "mac": "aa:bb:cc:dd:ee:ff"}]),
        )

        result = derive_exposure_map(session)

        assert result["edges"], "expected both a key-reuse and a hardware-bridge edge"
        edge_types = {e["edge_type"] for e in result["edges"]}
        assert edge_types == {"key_reuse", "hardware_bridge"}, (
            f"expected mixed edge types, got {edge_types}"
        )
        for edge in result["edges"]:
            evidence = edge.get("evidence")
            assert isinstance(evidence, str) and evidence.strip(), (
                f"every exposure-map edge must carry non-empty evidence (D-11): {edge}"
            )
    finally:
        session.close()
        engine.dispose()


def test_partial_only_devices_produce_zero_edges() -> None:
    """The single most important zero-fabrication gate (Pitfall 2, T-195-02):
    partial_only co-location must NEVER be rendered as a confirmed edge, and
    the same pair WITH evidence must produce exactly one.
    """
    # Branch 1: no ARP evidence -> stays "partial_only" -> zero edges.
    session, engine = _make_session()
    try:
        _seed_hardware_pair(session, gateway_evidence_json=None)
        edges = derive_hardware_bridge_edges(session)
        assert edges == [], (
            f"partial_only hardware devices must never produce an edge (D-03/Pitfall 2): {edges}"
        )
    finally:
        session.close()
        engine.dispose()

    # Branch 2: SAME pair, now with the gateway's ARP-table evidence naming
    # the legacy backend's IP -> promoted to "upstream_mitigated" -> exactly one edge.
    session, engine = _make_session()
    try:
        _seed_hardware_pair(
            session,
            gateway_evidence_json=json.dumps([{"target_ip": "10.0.5.2", "mac": "aa:bb:cc:dd:ee:ff"}]),
        )
        edges = derive_hardware_bridge_edges(session)
        assert len(edges) == 1, (
            f"expected exactly one upstream_mitigated edge, got {len(edges)}: {edges}"
        )
        assert edges[0]["edge_type"] == "hardware_bridge"
        assert edges[0].get("evidence"), "upstream_mitigated edge must carry evidence"
    finally:
        session.close()
        engine.dispose()


def test_no_denormalized_exposure_table() -> None:
    """D-12: no persisted exposure-map/edge table or migration exists — the
    map is derived fresh, read-time-only, on every call.
    """
    offending: list[str] = []
    for path in _QUIRK_DIR.rglob("*.py"):
        text = path.read_text(errors="ignore")
        for match in re.finditer(r'__tablename__\s*=\s*["\']([^"\']+)["\']', text):
            if _EXPOSURE_TABLE_NAME_RE.search(match.group(1)):
                offending.append(f"{path}: __tablename__={match.group(1)!r}")
        for match in re.finditer(r'_ensure_columns\([^)]*["\']([^"\']*exposure[^"\']*)["\']', text, re.IGNORECASE):
            offending.append(f"{path}: _ensure_columns references {match.group(1)!r}")

    assert offending == [], (
        f"D-12 violated — found denormalized exposure-edge table/migration artifacts: {offending}"
    )


def test_empty_session_returns_present_empty_keys() -> None:
    session, engine = _make_session()
    try:
        result = derive_exposure_map(session)
        assert result == {"nodes": [], "edges": []}
        assert "nodes" in result and "edges" in result
    finally:
        session.close()
        engine.dispose()
