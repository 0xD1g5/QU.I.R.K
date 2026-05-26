"""Tests for ?segment= filter on GET /api/scan/latest.

TDD RED phase — defines expected NULL-safe filtering behaviour.

Critical invariant (Trap T4):
- ?segment=dmz → only dmz findings
- Omitting ?segment= → ALL findings, including NULL-segment rows
"""
from __future__ import annotations

from datetime import datetime, timezone
import itertools

import pytest

_db_counter = itertools.count(200)


def _make_isolated_client():
    """Return a (TestClient, TestingSession) pair using a unique in-memory SQLite DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base
    from fastapi.testclient import TestClient

    db_name = f"seg_test_{next(_db_counter)}"
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
                   scanned_at=None, protocol="HTTPS", tls_version=None,
                   cert_pubkey_alg=None, tls_weak_ciphers_present=False):
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


class TestSegmentFilterNullSafe:
    """The NULL-safe guard: omitting segment returns ALL endpoints including NULL-segment ones."""

    def test_omitting_segment_returns_all_including_null_segment(self):
        """Omitting ?segment= returns endpoints with both set and NULL segment (Trap T4 regression)."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        # One endpoint with segment, one with NULL segment
        _seed_endpoint(db, host="10.0.1.1", segment="dmz", sensor_id="s1",
                       scanned_at=now, tls_version="TLSv1.2",
                       tls_weak_ciphers_present=True)   # will generate a finding
        _seed_endpoint(db, host="10.0.1.2", segment=None, sensor_id=None,
                       scanned_at=now, tls_version="TLSv1.2",
                       tls_weak_ciphers_present=True)   # will generate a finding
        db.close()

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        hosts_in_findings = {f["host"] for f in data["findings"]}
        # BOTH hosts must appear when no segment filter is applied
        assert "10.0.1.1" in hosts_in_findings, "dmz-segment host missing from unfiltered results"
        assert "10.0.1.2" in hosts_in_findings, "NULL-segment host missing from unfiltered results (Trap T4)"

    def test_segment_filter_excludes_other_segments(self):
        """?segment=dmz returns only dmz findings, excluding corp and NULL-segment."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_endpoint(db, host="10.0.1.1", segment="dmz", sensor_id="s1",
                       scanned_at=now, tls_version="TLSv1.2",
                       tls_weak_ciphers_present=True)
        _seed_endpoint(db, host="192.168.1.1", segment="corp", sensor_id="s2",
                       scanned_at=now, tls_version="TLSv1.2",
                       tls_weak_ciphers_present=True)
        _seed_endpoint(db, host="10.0.1.2", segment=None, sensor_id=None,
                       scanned_at=now, tls_version="TLSv1.2",
                       tls_weak_ciphers_present=True)
        db.close()

        resp = client.get("/api/scan/latest?segment=dmz")
        assert resp.status_code == 200
        data = resp.json()
        hosts = {f["host"] for f in data["findings"]}
        assert "10.0.1.1" in hosts, "dmz host should be in filtered results"
        assert "192.168.1.1" not in hosts, "corp host should be excluded by segment=dmz filter"
        assert "10.0.1.2" not in hosts, "NULL-segment host should be excluded by segment=dmz filter"

    def test_segment_filter_unknown_segment_returns_empty_or_404(self):
        """?segment=nosuchseg with no matching endpoints returns 404 (no endpoints after filter)."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_endpoint(db, host="10.0.1.1", segment="dmz", sensor_id="s1",
                       scanned_at=now, tls_version="TLSv1.2",
                       tls_weak_ciphers_present=True)
        db.close()

        resp = client.get("/api/scan/latest?segment=nosuchseg")
        # After filtering, no endpoints remain → 404
        assert resp.status_code == 404

    def test_segment_filter_all_cbom_components_inherit_filter(self):
        """When ?segment=dmz, cbom_components are also from dmz endpoints only."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_endpoint(db, host="10.0.1.1", segment="dmz", sensor_id="s1",
                       scanned_at=now, cert_pubkey_alg="RSA-2048")
        _seed_endpoint(db, host="192.168.1.1", segment="corp", sensor_id="s2",
                       scanned_at=now, cert_pubkey_alg="EC-256")
        db.close()

        resp = client.get("/api/scan/latest?segment=dmz")
        assert resp.status_code == 200
        data = resp.json()
        # source_systems in CBOM should only reference dmz host
        for comp in data.get("cbom_components", []):
            for src in comp.get("source_systems", []):
                assert "192.168.1.1" not in src, f"corp host leaked into dmz-filtered CBOM: {src}"
