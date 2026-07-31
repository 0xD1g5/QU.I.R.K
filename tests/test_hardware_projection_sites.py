"""Phase 141 Plan 05 (OTICS-06) — three-site projection parity tests.

Confirms that HardwareDevice modbus_*/bacnet_* fields (added in 141-01) flow
through all three projection sites — quirk/reports/writer.py,
quirk/merge/scan.py, and quirk/dashboard/api/routes/scan.py — plus the
dashboard Pydantic schemas (HardwareComponent/HardwareFinding), mirroring the
existing snmp_* / bridge_* precedent (v5.8 "B-01" lesson).
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
