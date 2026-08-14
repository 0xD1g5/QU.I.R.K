"""Phase 141 Plan 05 (OTICS-06) — three-site projection parity tests.

Confirms that HardwareDevice modbus_*/bacnet_* fields (added in 141-01) flow
through all three projection sites — quirk/reports/writer.py,
quirk/merge/scan.py, and quirk/dashboard/api/routes/scan.py — plus the
dashboard Pydantic schemas (HardwareComponent/HardwareFinding), mirroring the
existing snmp_* / bridge_* precedent (v5.8 "B-01" lesson).

Phase 154 Plan 03 (HWLC-02) extends this file with a fourth site (dashboard
_derive_hw_components joins _derive_hardware_findings as the second dashboard
site) and a last-known-good parity test group: all four current-state
projections must select the latest probe_status="success" row PER
(host, port) — a device whose most recent probe FAILED still appears,
carrying its last-known-good row's data, never the failed row's data (D-13).
"""
from __future__ import annotations

import datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import quirk.models as m
from quirk.models import HardwareDevice


_OTICS_FIELDS = dict(
    modbus_vendor="Schneider Electric",
    modbus_model="M221",
    modbus_firmware="1.6",
    modbus_probe_state="matched",
    bacnet_vendor="Honeywell",
    bacnet_model="XL Web II",
    bacnet_firmware="2.0",
    bacnet_probe_state="matched",
)

_OTICS_KEYS = tuple(_OTICS_FIELDS.keys())


# ---------------------------------------------------------------------------
# Site 1 — quirk/reports/writer.py
# ---------------------------------------------------------------------------


def _make_writer_cfg(tmp_path, db_path):
    return SimpleNamespace(
        output=SimpleNamespace(directory=str(tmp_path), db_path=db_path),
        assessment=SimpleNamespace(
            name="Phase 141-05 OTICS Test Assessment",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


def test_writer_projection_carries_otics_keys(tmp_path, monkeypatch):
    """reports/writer.py's HardwareDevice projection dict must carry all eight
    modbus_*/bacnet_* keys for a device with OTICS fields set."""
    db_path = str(tmp_path / "quirk.db")
    from quirk.db import init_db

    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    scanned_at = datetime.datetime.utcnow()
    session.add(HardwareDevice(
        host="10.0.5.5",
        port=502,
        vendor="Schneider Electric",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="modbus_probe",
        scanned_at=scanned_at,
        probe_status="success",  # Phase 154 D-13: required for the row to be projected
        **_OTICS_FIELDS,
    ))
    session.commit()
    session.close()

    # Spy on _confirm_upstream_mitigation (the last stage before assignment to
    # exec_content.hardware_devices) — wraps the real function so downstream
    # rendering behavior is unchanged, but captures the projected dict.
    import quirk.cbom.bridge as bridge_mod

    real_confirm = bridge_mod._confirm_upstream_mitigation
    captured: dict = {}

    def _spy(devices):
        captured["devices"] = devices
        return real_confirm(devices)

    monkeypatch.setattr("quirk.reports.writer._confirm_upstream_mitigation", _spy)

    from quirk.reports.writer import write_reports

    cfg = _make_writer_cfg(tmp_path, db_path)
    write_reports(cfg, endpoints=[], findings=[])

    assert captured.get("devices"), "writer.py did not build any hardware_devices dicts"
    dev = captured["devices"][0]
    for key in _OTICS_KEYS:
        assert key in dev, f"writer.py projection dict missing key: {key}"
        assert dev[key] == _OTICS_FIELDS[key]


# ---------------------------------------------------------------------------
# Site 2 — quirk/merge/scan.py
# ---------------------------------------------------------------------------


def test_merge_projection_carries_otics_keys(tmp_path, monkeypatch):
    """merge/scan.py's hw_devices_for_cbom projection dict must carry all eight
    modbus_*/bacnet_* keys for a device with OTICS fields set."""
    db_path = str(tmp_path / "quirk_merge.db")
    from quirk.db import init_db, get_session

    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    scanned_at = datetime.datetime.utcnow()
    session.add(HardwareDevice(
        host="10.0.5.6",
        port=502,
        vendor="Schneider Electric",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="modbus_probe",
        scanned_at=scanned_at,
        probe_status="success",  # Phase 154 D-13: required for the row to be projected
        **_OTICS_FIELDS,
    ))
    # merge_scan() guards an empty union — seed one NULL-sensor CryptoEndpoint
    # so the union is non-empty and build_cbom() is reached.
    from quirk.models import CryptoEndpoint

    session.add(CryptoEndpoint(
        host="10.0.5.6",
        port=502,
        protocol="TLS",
        scanned_at=scanned_at,
    ))
    session.commit()
    session.close()

    import quirk.cbom.bridge as bridge_mod

    real_confirm = bridge_mod._confirm_upstream_mitigation
    captured: dict = {}

    def _spy(devices):
        captured["devices"] = devices
        return real_confirm(devices)

    monkeypatch.setattr("quirk.merge.scan._confirm_upstream_mitigation", _spy)

    from quirk.merge.scan import merge_scan

    with get_session(db_path) as db:
        merge_scan(db, stale_days=30, output_dir=str(tmp_path))

    assert captured.get("devices"), "merge/scan.py did not build any hw_devices_for_cbom dicts"
    dev = captured["devices"][0]
    for key in _OTICS_KEYS:
        assert key in dev, f"merge/scan.py projection dict missing key: {key}"
        assert dev[key] == _OTICS_FIELDS[key]


# ---------------------------------------------------------------------------
# Site 3 — quirk/dashboard/api/routes/scan.py + dashboard schemas
# ---------------------------------------------------------------------------


def _make_dashboard_session():
    engine = create_engine("sqlite:///:memory:")
    m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    scanned_at = datetime.datetime.utcnow()
    device = HardwareDevice(
        host="10.0.5.7",
        port=502,
        vendor="Schneider Electric",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="modbus_probe",
        scanned_at=scanned_at,
        probe_status="success",  # Phase 154 D-13: required for the row to be projected
        **_OTICS_FIELDS,
    )
    session.add(device)
    session.commit()
    return session, scanned_at


def test_dashboard_projection_carries_otics_keys():
    """dashboard/api/routes/scan.py's _derive_hardware_findings and
    _derive_hw_components must project the eight modbus_*/bacnet_* fields onto
    HardwareFinding/HardwareComponent."""
    from quirk.dashboard.api.routes.scan import (
        _derive_hardware_findings,
        _derive_hw_components,
    )

    session, scanned_at = _make_dashboard_session()
    try:
        findings = _derive_hardware_findings(session, scanned_at)
        components = _derive_hw_components(session, scanned_at)
    finally:
        session.close()

    assert findings, "no HardwareFinding rows derived"
    assert components, "no HardwareComponent rows derived"

    finding = findings[0]
    component = components[0]
    for key, value in _OTICS_FIELDS.items():
        assert getattr(finding, key, None) == value, f"HardwareFinding.{key} missing/incorrect"
        assert getattr(component, key, None) == value, f"HardwareComponent.{key} missing/incorrect"


def test_dashboard_schemas_expose_otics_fields():
    """HardwareFinding/HardwareComponent Pydantic schemas accept and round-trip
    the new modbus_*/bacnet_* Optional[str] fields."""
    from quirk.dashboard.api.schemas import HardwareComponent, HardwareFinding

    finding = HardwareFinding(
        host="10.0.5.8",
        port=502,
        severity="INFO",
        title="Test",
        vendor="Schneider Electric",
        pqc_status="unsupported",
        remediation_tier="Tier 1",
        confidence="high",
        fingerprint_method="modbus_probe",
        **_OTICS_FIELDS,
    )
    component = HardwareComponent(
        host="10.0.5.8",
        port=502,
        vendor="Schneider Electric",
        model="M221",
        pqc_status="unsupported",
        remediation_tier="Tier 1",
        **_OTICS_FIELDS,
    )
    for key, value in _OTICS_FIELDS.items():
        assert getattr(finding, key) == value
        assert getattr(component, key) == value


# ---------------------------------------------------------------------------
# Phase 154 Plan 03 (HWLC-02) — per-(host, port) last-known-good parity
# ---------------------------------------------------------------------------
#
# Confirms that all four current-state projection sites (writer, merge,
# dashboard findings, dashboard components) select the latest
# probe_status="success" row PER (host, port) rather than a single global
# MAX(scanned_at) window — a device whose most recent probe FAILED still
# appears, showing its last-known-good row's data (D-13), never a failed
# row's data (D-14).

_LKG_HOST = "10.0.9.9"
_LKG_PORT = 22
_LKG_UNKNOWN_HOST = "10.0.9.10"


def _seed_last_known_good_rows(session, unmapped_ok: bool = False) -> datetime.datetime:
    """Seed a two-row history for one device (older success, newer failed) plus
    a second, honest-unknown device (success + vendor="Unknown" only).

    Returns the newer (failed) row's scanned_at, which callers pass as the
    `latest_ts` argument some projection functions accept for signature parity
    (the functions themselves derive their own anchor from the DB).
    """
    older_success_ts = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
    newer_failed_ts = datetime.datetime.utcnow()

    session.add(HardwareDevice(
        host=_LKG_HOST,
        port=_LKG_PORT,
        vendor="Cisco Systems",
        pqc_status="unsupported",
        confidence="high",
        match_confidence="high",
        ssh_host_key_fingerprint="SHA256:abc123",
        fingerprint_method="ssh_banner",
        probe_status="success",
        scanned_at=older_success_ts,
    ))
    session.add(HardwareDevice(
        host=_LKG_HOST,
        port=_LKG_PORT,
        vendor="Unknown",
        pqc_status="unknown",
        confidence="unknown",
        fingerprint_method="ssh_banner",
        probe_status="failed",
        scanned_at=newer_failed_ts,
    ))
    session.add(HardwareDevice(
        host=_LKG_UNKNOWN_HOST,
        port=_LKG_PORT,
        vendor="Unknown",
        pqc_status="unknown",
        confidence="unknown",
        fingerprint_method="ssh_banner",
        probe_status="success",
        scanned_at=older_success_ts,
    ))
    session.commit()
    return newer_failed_ts


def test_writer_projection_shows_last_known_good_not_failed_row(tmp_path, monkeypatch):
    """writer.py: the device with a failed latest probe still appears exactly
    once, carrying the older success row's vendor — never the failed row's
    vendor="Unknown". The honest-unknown device (success + vendor=Unknown) is
    also present."""
    db_path = str(tmp_path / "quirk_lkg_writer.db")
    from quirk.db import init_db

    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    _seed_last_known_good_rows(session)
    session.close()

    import quirk.cbom.bridge as bridge_mod

    real_confirm = bridge_mod._confirm_upstream_mitigation
    captured: dict = {}

    def _spy(devices):
        captured["devices"] = devices
        return real_confirm(devices)

    monkeypatch.setattr("quirk.reports.writer._confirm_upstream_mitigation", _spy)

    from quirk.reports.writer import write_reports

    cfg = _make_writer_cfg(tmp_path, db_path)
    write_reports(cfg, endpoints=[], findings=[])

    devices = captured.get("devices") or []
    by_host = {}
    for d in devices:
        by_host.setdefault(d["host"], []).append(d)

    assert len(by_host.get(_LKG_HOST, [])) == 1, "device appeared more than once or vanished"
    assert by_host[_LKG_HOST][0]["vendor"] == "Cisco Systems"

    assert _LKG_UNKNOWN_HOST in by_host, "honest-unknown device (success + Unknown) must be present"


def test_merge_projection_shows_last_known_good_not_failed_row(tmp_path, monkeypatch):
    """merge/scan.py: same last-known-good guarantee for hw_devices_for_cbom."""
    db_path = str(tmp_path / "quirk_lkg_merge.db")
    from quirk.db import init_db, get_session

    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    _seed_last_known_good_rows(session)
    from quirk.models import CryptoEndpoint

    session.add(CryptoEndpoint(
        host=_LKG_HOST,
        port=_LKG_PORT,
        protocol="SSH",
        scanned_at=datetime.datetime.utcnow(),
    ))
    session.commit()
    session.close()

    import quirk.cbom.bridge as bridge_mod

    real_confirm = bridge_mod._confirm_upstream_mitigation
    captured: dict = {}

    def _spy(devices):
        captured["devices"] = devices
        return real_confirm(devices)

    monkeypatch.setattr("quirk.merge.scan._confirm_upstream_mitigation", _spy)

    from quirk.merge.scan import merge_scan

    with get_session(db_path) as db:
        merge_scan(db, stale_days=30, output_dir=str(tmp_path))

    devices = captured.get("devices") or []
    by_host = {}
    for d in devices:
        by_host.setdefault(d["host"], []).append(d)

    assert len(by_host.get(_LKG_HOST, [])) == 1, "device appeared more than once or vanished"
    assert by_host[_LKG_HOST][0]["vendor"] == "Cisco Systems"
    assert _LKG_UNKNOWN_HOST in by_host, "honest-unknown device (success + Unknown) must be present"


def test_dashboard_findings_shows_last_known_good_not_failed_row():
    """dashboard/api/routes/scan.py::_derive_hardware_findings: same guarantee."""
    from quirk.dashboard.api.routes.scan import _derive_hardware_findings

    engine = create_engine("sqlite:///:memory:")
    m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    scanned_at = _seed_last_known_good_rows(session)
    try:
        out = _derive_hardware_findings(session, scanned_at)
    finally:
        session.close()

    by_host: dict = {}
    for f in out:
        by_host.setdefault(f.host, []).append(f)

    assert len(by_host.get(_LKG_HOST, [])) == 1, "device appeared more than once or vanished"
    assert by_host[_LKG_HOST][0].vendor == "Cisco Systems"
    assert _LKG_UNKNOWN_HOST in by_host, "honest-unknown device (success + Unknown) must be present"


def test_dashboard_components_shows_last_known_good_not_failed_row():
    """dashboard/api/routes/scan.py::_derive_hw_components: same guarantee."""
    from quirk.dashboard.api.routes.scan import _derive_hw_components

    engine = create_engine("sqlite:///:memory:")
    m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    scanned_at = _seed_last_known_good_rows(session)
    try:
        out = _derive_hw_components(session, scanned_at)
    finally:
        session.close()

    by_host: dict = {}
    for c in out:
        by_host.setdefault(c.host, []).append(c)

    assert len(by_host.get(_LKG_HOST, [])) == 1, "device appeared more than once or vanished"
    assert by_host[_LKG_HOST][0].vendor == "Cisco Systems"
    assert _LKG_UNKNOWN_HOST in by_host, "honest-unknown device (success + Unknown) must be present"


def test_null_probe_status_excluded_from_dashboard_projection():
    """A row with probe_status=None (pre-Phase-154 legacy data) is excluded
    from the dashboard projection — pinning the documented
    invisible-until-rescanned behavior as intentional (D-13/RESEARCH)."""
    from quirk.dashboard.api.routes.scan import _derive_hardware_findings

    engine = create_engine("sqlite:///:memory:")
    m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    scanned_at = datetime.datetime.utcnow()
    session.add(HardwareDevice(
        host="10.0.9.20",
        port=22,
        vendor="Legacy Vendor",
        pqc_status="unknown",
        confidence="unknown",
        fingerprint_method="ssh_banner",
        probe_status=None,  # pre-Phase-154 row: never migrated/re-scanned
        scanned_at=scanned_at,
    ))
    session.commit()
    try:
        out = _derive_hardware_findings(session, scanned_at)
    finally:
        session.close()

    hosts = {f.host for f in out}
    assert "10.0.9.20" not in hosts, "NULL probe_status row must not surface in the projection"


def test_hardware_component_schema_has_no_match_confidence_or_probe_status_fields():
    """D-15 guard: HardwareComponent gets NO new fields this phase — pins the
    deferral to Phase 156 deliberately rather than letting it drift in
    unnoticed."""
    from quirk.dashboard.api.schemas import HardwareComponent

    field_names = set(HardwareComponent.model_fields.keys())
    assert "match_confidence" not in field_names
    assert "probe_status" not in field_names
