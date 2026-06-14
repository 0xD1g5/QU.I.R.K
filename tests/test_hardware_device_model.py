"""Phase 127 — HWCOMPAT-01 ORM contract tests for HardwareDevice model."""
from __future__ import annotations

import datetime


# ------------ column contract test ------------

def test_hardware_device_columns() -> None:
    from quirk.models import HardwareDevice

    assert HardwareDevice.__tablename__ == "hardware_devices"

    col_names = {c.name for c in HardwareDevice.__table__.columns}
    required_columns = {
        "id", "scan_id", "host", "port", "vendor", "model",
        "pqc_status", "eol_date", "confidence", "fingerprint_method",
        "raw_banner", "scanned_at",
    }
    assert required_columns.issubset(col_names), (
        f"HardwareDevice missing columns: {required_columns - col_names}"
    )

    cols_by_name = {c.name: c for c in HardwareDevice.__table__.columns}

    # host and vendor must be NOT NULL
    assert cols_by_name["host"].nullable is False
    assert cols_by_name["vendor"].nullable is False

    # pqc_status, confidence, fingerprint_method must be NOT NULL
    assert cols_by_name["pqc_status"].nullable is False
    assert cols_by_name["confidence"].nullable is False
    assert cols_by_name["fingerprint_method"].nullable is False


# ------------ in-memory SQLite creation test ------------

def test_hardware_device_create_in_sqlite() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import quirk.models as m
    from quirk.models import HardwareDevice

    engine = create_engine("sqlite:///:memory:")
    m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    device = HardwareDevice(
        host="10.0.0.1",
        port=22,
        vendor="Cisco",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="ssh_banner",
        scanned_at=datetime.datetime.utcnow(),
    )
    session.add(device)
    session.commit()

    result = session.query(HardwareDevice).filter_by(vendor="Cisco").one()
    assert result.vendor == "Cisco"
    session.close()
