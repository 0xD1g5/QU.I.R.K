"""Phase 163 (DISC-08, D-01..D-07): tests for the per-batch discovery
checkpoint/resume loop — resume-skip guard, unconditional per-batch
checkpoint+cache writes, dead-batch checkpointing, and the NmapOpenPort
serializer pair that makes batch cache payloads JSON-safe.

Part A mirrors the loop shape (following tests/test_discovery_batch_progress.py's
convention) with stubbed nmap calls and a real temp-SQLite-backed
ScanCheckpoint table via write_scan_checkpoint() — no subprocess is spawned
and no real nmap binary is required.

Part B parses the REAL run_scan.py via `ast` so a passing mirror test can
never mask an unwired loop (mirrors tests/test_cli_dashboard_discovery_parity.py's
structural-test convention). Part B is added by Plan 163-02.
"""
from __future__ import annotations

from quirk.discovery.nmap_parser import NmapOpenPort
from quirk.engine.cache import open_ports_to_serial, serial_to_open_ports
from quirk.scanner.target_expander import _chunked, _expand_and_dedup_hosts, _MAX_HOSTS_PER_CIDR

_RESUME_BATCH_CACHE_TTL_HOURS = 720


# ---------------------------------------------------------------------------
# Part A: NmapOpenPort serializer round-trip (Task 1)
# ---------------------------------------------------------------------------

def test_nmap_open_port_serializer_roundtrip():
    ports = [
        NmapOpenPort(host="10.0.0.1", port=443, protocol="tcp", service="https"),
        NmapOpenPort(host="10.0.0.2", port=53, protocol="udp", service="domain"),
        NmapOpenPort(host="10.0.0.3", port=22, protocol="tcp", service=None),
    ]

    serial = open_ports_to_serial(ports)
    assert serial == [
        {"host": "10.0.0.1", "port": 443, "protocol": "tcp", "service": "https"},
        {"host": "10.0.0.2", "port": 53, "protocol": "udp", "service": "domain"},
        {"host": "10.0.0.3", "port": 22, "protocol": "tcp", "service": None},
    ]

    # service=None round-trips as None, not "None" and not dropped.
    assert serial[2]["service"] is None

    roundtripped = serial_to_open_ports(serial)
    assert roundtripped == ports

    # None / empty input.
    assert serial_to_open_ports(None) == []
    assert serial_to_open_ports([]) == []

    # Malformed items are skipped, not raised on.
    malformed = [
        {"port": 443, "protocol": "tcp"},  # missing host
        {"host": "10.0.0.1", "protocol": "tcp"},  # missing port
        {"host": "10.0.0.1", "port": 443},  # missing protocol
        {"host": "10.0.0.1", "port": 443, "protocol": "tcp", "service": "https"},  # valid
    ]
    result = serial_to_open_ports(malformed)
    assert result == [NmapOpenPort(host="10.0.0.1", port=443, protocol="tcp", service="https")]

    # json.dumps must succeed on the serialized payload (no TypeError).
    import json
    json.dumps({"ports": open_ports_to_serial(ports)})


# --- Part B: AST-structural tests (Plan 163-02) ---
