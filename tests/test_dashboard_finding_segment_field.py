"""Tests that FindingItem and CbomComponent carry sensor_id and segment fields.

TDD RED phase — verifies the Phase 111 nullable field additions.
"""
from __future__ import annotations

from datetime import datetime, timezone
import itertools

import pytest

_db_counter = itertools.count(300)


def _make_isolated_client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base
    from fastapi.testclient import TestClient

    db_name = f"field_test_{next(_db_counter)}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, headers={"X-Quirk-Request": "1"})
    return client, TestingSession


def _seed_endpoint(db, *, host, port=443, segment=None, sensor_id=None,
                   scanned_at=None, protocol="HTTPS", tls_version="TLSv1.2",
                   cert_pubkey_alg="RSA", tls_weak_ciphers_present=True):
    from quirk.models import CryptoEndpoint
    if scanned_at is None:
        scanned_at = datetime.now(timezone.utc).replace(tzinfo=None)
    ep = CryptoEndpoint(
        host=host,
        port=port,
        segment=segment,
        sensor_id=sensor_id,
        scanned_at=scanned_at,
        protocol=protocol,
        tls_version=tls_version,
        cert_pubkey_alg=cert_pubkey_alg,
        tls_weak_ciphers_present=tls_weak_ciphers_present,
    )
    db.add(ep)
    db.commit()
    return ep


class TestFindingItemSegmentFields:
    """FindingItem response carries sensor_id and segment fields."""

    def test_finding_has_sensor_id_and_segment_keys(self):
        """FindingItem items include sensor_id and segment keys (may be null)."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_endpoint(db, host="10.0.1.1", segment="dmz", sensor_id="sensor-a",
                       scanned_at=now, tls_weak_ciphers_present=True)
        db.close()

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        assert len(findings) > 0, "Expected at least one finding"
        finding = findings[0]
        assert "sensor_id" in finding, "FindingItem missing sensor_id field"
        assert "segment" in finding, "FindingItem missing segment field"

    def test_finding_sensor_id_and_segment_values(self):
        """FindingItem items carry the correct sensor_id and segment from the endpoint."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_endpoint(db, host="10.0.1.1", segment="corp", sensor_id="sensor-xyz",
                       scanned_at=now, tls_weak_ciphers_present=True)
        db.close()

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        assert len(findings) > 0, "Expected at least one finding"
        # At least one finding should carry the segment/sensor_id
        # (identity findings cross-posted from _derive_identity_findings will have None)
        has_values = any(
            f.get("sensor_id") == "sensor-xyz" and f.get("segment") == "corp"
            for f in findings
        )
        assert has_values, "No finding carries sensor_id='sensor-xyz' and segment='corp'"

    def test_finding_null_sensor_id_and_segment_for_local_scan(self):
        """NULL-sensor local scan findings carry sensor_id=null and segment=null."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_endpoint(db, host="10.0.1.1", segment=None, sensor_id=None,
                       scanned_at=now, tls_weak_ciphers_present=True)
        db.close()

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        assert len(findings) > 0
        for f in findings:
            assert "sensor_id" in f
            assert "segment" in f
            # NULL-sensor endpoints → null values in finding
            # (identity findings cross-posted may have None too)
            if f.get("host") == "10.0.1.1":
                assert f["sensor_id"] is None
                assert f["segment"] is None


class TestCbomComponentSegmentFields:
    """CbomComponent response carries sensor_id and segment fields."""

    def test_cbom_component_has_sensor_id_and_segment_keys(self):
        """CbomComponent items include sensor_id and segment keys (may be null)."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_endpoint(db, host="10.0.1.1", segment="dmz", sensor_id="sensor-b",
                       scanned_at=now, cert_pubkey_alg="RSA",
                       tls_weak_ciphers_present=False)
        db.close()

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        components = resp.json()["cbom_components"]
        assert len(components) > 0, "Expected at least one CBOM component"
        comp = components[0]
        assert "sensor_id" in comp, "CbomComponent missing sensor_id field"
        assert "segment" in comp, "CbomComponent missing segment field"
