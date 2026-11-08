"""STAB-04 regression tests: advisory sentinel rows must not enter the push/export envelope.

These tests verify that _read_scan_endpoints excludes CryptoEndpoint rows with
scan_error_category='missing_extra' (advisory sentinels written by
_emit_missing_extra_advisory when an optional scanner extra is absent), while
retaining normal finding rows whose scan_error_category is NULL.

Defect trace: run_scan._emit_missing_extra_advisory writes host='email_scanner',
port=0, scanned_at=None rows to the local scan DB.  _read_scan_endpoints previously
returned all rows without filtering, causing advisory rows to ride the push envelope
into the console DB (phantom endpoints in merged output).
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone


def test_read_scan_endpoints_excludes_advisory(tmp_path):
    """STAB-04: _read_scan_endpoints must not return rows with
    scan_error_category='missing_extra' (advisory sentinels), but must include
    rows whose scan_error_category is NULL (normal finding rows).
    """
    from sqlalchemy.orm import sessionmaker

    from quirk.db import init_db
    from quirk.models import CryptoEndpoint
    from quirk.cli.sensor_cmd import _read_scan_endpoints

    db_path = str(tmp_path / "scan.db")
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        # Advisory sentinel row (should be excluded)
        db.add(CryptoEndpoint(
            host="email_scanner",
            port=0,
            protocol="ADVISORY",
            scan_error_category="missing_extra",
            scanned_at=None,
        ))
        # Normal finding row with NULL scan_error_category (should be INCLUDED)
        db.add(CryptoEndpoint(
            host="10.0.0.1",
            port=443,
            protocol="tls",
            scan_error_category=None,
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
        db.commit()

    rows = _read_scan_endpoints(db_path)

    # Advisory row excluded
    advisory_rows = [r for r in rows if r.scan_error_category == "missing_extra"]
    assert advisory_rows == [], (
        f"Advisory rows must be excluded from push envelope; got: {advisory_rows}"
    )

    # Normal row with NULL scan_error_category included (SQL 3VL: != does NOT match NULL)
    real_rows = [r for r in rows if r.host == "10.0.0.1"]
    assert len(real_rows) == 1, (
        "Normal finding row with NULL scan_error_category must be INCLUDED (IS NULL clause required)"
    )


def test_no_phantom_rows_in_merged_output(tmp_path):
    """STAB-04 D-05 regression: after building a push envelope from a scan DB that
    contains advisory rows, the endpoint list returned by _read_scan_endpoints must
    contain zero entries with scanned_at=None or port=0.
    """
    from sqlalchemy.orm import sessionmaker

    from quirk.db import init_db
    from quirk.models import CryptoEndpoint
    from quirk.cli.sensor_cmd import _read_scan_endpoints

    db_path = str(tmp_path / "scan.db")
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        # Two advisory sentinels (email_scanner and broker_scanner pattern)
        for scanner_name in ("email_scanner", "broker_scanner"):
            db.add(CryptoEndpoint(
                host=scanner_name,
                port=0,
                protocol="ADVISORY",
                scan_error="optional extra [motion] not installed",
                scan_error_category="missing_extra",
                scanned_at=None,
            ))
        # One real endpoint
        db.add(CryptoEndpoint(
            host="192.168.1.100",
            port=22,
            protocol="ssh",
            scan_error_category=None,
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
        db.commit()

    endpoints = _read_scan_endpoints(db_path)

    # D-05: zero endpoints with scanned_at=None or port=0
    phantom_scanned_at = [e for e in endpoints if e.scanned_at is None]
    phantom_port_zero = [e for e in endpoints if e.port == 0]

    assert phantom_scanned_at == [], (
        f"Merged output must not contain scanned_at=None endpoints; got: "
        f"{[(e.host, e.port) for e in phantom_scanned_at]}"
    )
    assert phantom_port_zero == [], (
        f"Merged output must not contain port=0 endpoints; got: "
        f"{[(e.host, e.port) for e in phantom_port_zero]}"
    )


def test_read_scan_endpoints_excludes_missing_binary_advisory(tmp_path):
    """235.1 D-06: missing_binary advisory rows are filtered like missing_extra;
    real SOURCE rows and NULL-category rows stay."""
    from sqlalchemy.orm import sessionmaker

    from quirk.cli.sensor_cmd import _read_scan_endpoints
    from quirk.db import init_db
    from quirk.models import CryptoEndpoint

    db_path = str(tmp_path / "scan.db")
    engine = init_db(db_path)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with sessionmaker(bind=engine)() as db:
        db.add(CryptoEndpoint(
            host="source_scanner", port=0, protocol="ADVISORY",
            scan_error="semgrep is not installed (QRK-INSTALL-008)",
            scan_error_category="missing_binary", scanned_at=None,
        ))
        db.add(CryptoEndpoint(
            host="repo/app.py", port=0, protocol="SOURCE",
            scan_error_category=None, scanned_at=now,
        ))
        db.commit()

    hosts = {r.host for r in _read_scan_endpoints(db_path)}
    assert "source_scanner" not in hosts
    assert "repo/app.py" in hosts


@pytest.mark.parametrize("category", [
    "internal_target_refused", "auth_failed", "missing_credentials", "targets_unreachable",
])
def test_read_scan_endpoints_excludes_coverage_skip_advisory(tmp_path, category):
    """235.3 D-07: the four coverage-skip advisory rows never enter the push
    envelope; NULL-category rows stay (T-115-04 IS NULL clause)."""
    from sqlalchemy.orm import sessionmaker

    from quirk.cli.sensor_cmd import _read_scan_endpoints
    from quirk.db import init_db
    from quirk.models import CryptoEndpoint

    db_path = str(tmp_path / "scan.db")
    engine = init_db(db_path)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with sessionmaker(bind=engine)() as db:
        db.add(CryptoEndpoint(
            host="jwt_scanner", port=0, protocol="ADVISORY",
            scan_error="1 of 1 targets skipped",
            scan_error_category=category, scanned_at=None,
        ))
        db.add(CryptoEndpoint(
            host="repo/app.py", port=0, protocol="SOURCE",
            scan_error_category=None, scanned_at=now,
        ))
        db.commit()

    hosts = {r.host for r in _read_scan_endpoints(db_path)}
    assert "jwt_scanner" not in hosts
    assert "repo/app.py" in hosts
