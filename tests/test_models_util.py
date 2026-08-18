"""Phase 160 Plan 01 (HWLC-17) — unit tests for
``quirk.models_util.vendor_fleet_snapshot()``: the vendor-scoped,
distinct-device fleet window that backs the catalog-level PQC vendor trend
N-of-M confirmation gate.

Mirrors the tmp_path-free in-memory SQLite + create_engine + sessionmaker
pattern already used in tests/test_hardware_drift.py's reconcile_* section.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import quirk.models as _m
from quirk.models import HardwareDevice
from quirk.models_util import vendor_fleet_snapshot


def _memory_session():
    engine = create_engine("sqlite:///:memory:")
    _m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed(session, host, port, scanned_at, vendor, pqc_status="unsupported", probe_status="success"):
    device = HardwareDevice(
        host=host,
        port=port,
        vendor=vendor,
        model=None,
        pqc_status=pqc_status,
        confidence="high",
        fingerprint_method="ssh_banner",
        probe_status=probe_status,
        scanned_at=scanned_at,
        remediation_tier="Tier 1",
    )
    session.add(device)
    session.commit()
    return device


def test_vendor_fleet_snapshot_returns_at_most_limit_rows_newest_first() -> None:
    session = _memory_session()
    base = dt.datetime(2026, 8, 1)
    _seed(session, "10.0.0.1", 443, base, vendor="Cisco")
    _seed(session, "10.0.0.2", 443, base + dt.timedelta(days=1), vendor="Cisco")
    _seed(session, "10.0.0.3", 443, base + dt.timedelta(days=2), vendor="Cisco")
    _seed(session, "10.0.0.4", 443, base + dt.timedelta(days=3), vendor="Cisco")
    try:
        result = vendor_fleet_snapshot(session, "Cisco", limit=3)
        assert len(result) == 3
        hosts = [row.host for row in result]
        assert hosts == ["10.0.0.4", "10.0.0.3", "10.0.0.2"]
    finally:
        session.close()


def test_vendor_fleet_snapshot_dedupes_repeatedly_rescanned_host() -> None:
    """Pitfall 1 defence: a host rescanned 3 times contributes 1 row, not 3."""
    session = _memory_session()
    base = dt.datetime(2026, 8, 1)
    _seed(session, "10.0.0.1", 443, base, vendor="Cisco")
    _seed(session, "10.0.0.1", 443, base + dt.timedelta(days=1), vendor="Cisco")
    _seed(session, "10.0.0.1", 443, base + dt.timedelta(days=2), vendor="Cisco")
    _seed(session, "10.0.0.2", 443, base + dt.timedelta(days=1), vendor="Cisco")
    try:
        result = vendor_fleet_snapshot(session, "Cisco", limit=3)
        assert len(result) == 2
        hosts = {row.host for row in result}
        assert hosts == {"10.0.0.1", "10.0.0.2"}
    finally:
        session.close()


def test_vendor_fleet_snapshot_excludes_failed_probes() -> None:
    session = _memory_session()
    base = dt.datetime(2026, 8, 1)
    _seed(session, "10.0.0.1", 443, base, vendor="Cisco", probe_status="failed")
    try:
        result = vendor_fleet_snapshot(session, "Cisco", limit=3)
        assert result == []
    finally:
        session.close()


def test_vendor_fleet_snapshot_excludes_other_vendors() -> None:
    session = _memory_session()
    base = dt.datetime(2026, 8, 1)
    _seed(session, "10.0.0.1", 443, base, vendor="Cisco")
    _seed(session, "10.0.0.2", 443, base, vendor="Juniper")
    try:
        result = vendor_fleet_snapshot(session, "Cisco", limit=3)
        assert len(result) == 1
        assert result[0].vendor == "Cisco"
    finally:
        session.close()


def test_vendor_fleet_snapshot_scopes_on_literal_unknown_vendor() -> None:
    session = _memory_session()
    base = dt.datetime(2026, 8, 1)
    _seed(session, "10.0.0.1", 443, base, vendor="Unknown")
    _seed(session, "10.0.0.2", 443, base, vendor="Cisco")
    try:
        result = vendor_fleet_snapshot(session, "Unknown", limit=3)
        assert len(result) == 1
        assert result[0].vendor == "Unknown"
    finally:
        session.close()


def test_vendor_fleet_snapshot_returns_empty_for_no_successful_rows() -> None:
    session = _memory_session()
    try:
        result = vendor_fleet_snapshot(session, "Cisco", limit=3)
        assert result == []
    finally:
        session.close()


def test_vendor_fleet_snapshot_deterministic_tie_break_on_identical_scanned_at() -> None:
    session = _memory_session()
    same_ts = dt.datetime(2026, 8, 1, 12, 0, 0)
    d1 = _seed(session, "10.0.0.1", 443, same_ts, vendor="Cisco")
    d2 = _seed(session, "10.0.0.2", 443, same_ts, vendor="Cisco")
    try:
        result = vendor_fleet_snapshot(session, "Cisco", limit=3)
        assert len(result) == 2
        # newest-first ordering: higher id sorts first for identical scanned_at
        assert result[0].id == max(d1.id, d2.id)
    finally:
        session.close()
