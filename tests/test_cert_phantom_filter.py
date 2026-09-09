"""Phase 194 Plan 01 (DASH-09 / D-11 / D-12): phantom-certificate filter.

Covers `_is_real_cert_endpoint()` (the single named predicate) plus an
end-to-end `/api/scan/latest` route regression proving both the filtered
`certificates` list and the new `excluded_cert_count` disclosure field, for
the exact scenario named in
`.planning/todos/pending/dashboard-cert-view-phantom-tls-rows.md`: 5 phantom
TLS rows and 0 real certificates should yield `certificates == []` and
`excluded_cert_count == 5`, not a silently-empty list with no explanation.
"""
from __future__ import annotations

import datetime
import uuid
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.routes.scan import _is_real_cert_endpoint
from quirk.models import Base, CryptoEndpoint


# ---------------------------------------------------------------------------
# Unit coverage: _is_real_cert_endpoint()
# ---------------------------------------------------------------------------


def _ep(**kwargs):
    defaults = dict(protocol="TLS", cert_subject=None, scan_error=None)
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_real_cert_endpoint_with_subject_and_no_error_is_kept():
    ep = _ep(cert_subject="CN=example.com", scan_error=None)
    assert _is_real_cert_endpoint(ep) is True


def test_endpoint_with_no_subject_and_no_error_is_excluded():
    ep = _ep(cert_subject=None, scan_error=None)
    assert _is_real_cert_endpoint(ep) is False


def test_endpoint_with_subject_and_scan_error_is_excluded():
    ep = _ep(cert_subject="CN=example.com", scan_error="handshake timeout")
    assert _is_real_cert_endpoint(ep) is False


def test_endpoint_with_no_subject_and_scan_error_is_excluded():
    ep = _ep(cert_subject=None, scan_error="connection reset")
    assert _is_real_cert_endpoint(ep) is False


# ---------------------------------------------------------------------------
# Route-level: end-to-end phantom filter + excluded_cert_count disclosure
# ---------------------------------------------------------------------------


def _make_session():
    db_name = f"test_cert_phantom_filter_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, TestingSession


def _client_and_session():
    from fastapi.testclient import TestClient

    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db

    engine, TestingSession = _make_session()

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app, headers={"X-Quirk-Request": "1"})
    return client, TestingSession, engine


def _seed_endpoint(
    TestingSession,
    scan_run_id: str,
    scanned_at: datetime.datetime,
    *,
    host: str,
    port: int,
    protocol: str = "TLS",
    cert_subject=None,
    scan_error=None,
):
    db = TestingSession()
    try:
        db.add(CryptoEndpoint(
            host=host,
            port=port,
            protocol=protocol,
            scanned_at=scanned_at,
            scan_run_id=scan_run_id,
            cert_subject=cert_subject,
            scan_error=scan_error,
        ))
        db.commit()
    finally:
        db.close()


def test_zero_real_certs_five_phantoms_yields_empty_list_and_count_five():
    """The exact regression scenario from
    dashboard-cert-view-phantom-tls-rows.md: 5 phantom TLS rows, 0 real
    certificates."""
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 9, 12, 0, 0)
        scan_run_id = scanned_at.isoformat()
        for i in range(5):
            _seed_endpoint(
                TestingSession,
                scan_run_id,
                scanned_at,
                host=f"10.0.0.{i}",
                port=443,
                cert_subject=None,
                scan_error="handshake timeout" if i % 2 == 0 else None,
            )

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["certificates"] == []
        assert data["excluded_cert_count"] == 5
    finally:
        client.close()
        engine.dispose()


def test_mixed_real_and_phantom_certs_filters_only_phantoms():
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 9, 13, 0, 0)
        scan_run_id = scanned_at.isoformat()
        # 1 real cert.
        _seed_endpoint(
            TestingSession, scan_run_id, scanned_at,
            host="10.0.0.1", port=443, cert_subject="CN=real.example.com", scan_error=None,
        )
        # 1 phantom: no subject.
        _seed_endpoint(
            TestingSession, scan_run_id, scanned_at,
            host="10.0.0.2", port=443, cert_subject=None, scan_error=None,
        )
        # 1 phantom: subject present but scan_error recorded.
        _seed_endpoint(
            TestingSession, scan_run_id, scanned_at,
            host="10.0.0.3", port=443, cert_subject="CN=stale.example.com", scan_error="reset",
        )
        # 1 non-TLS row — must not be counted at all.
        _seed_endpoint(
            TestingSession, scan_run_id, scanned_at,
            host="10.0.0.4", port=22, protocol="SSH", cert_subject=None, scan_error=None,
        )

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["certificates"]) == 1
        assert data["certificates"][0]["host"] == "10.0.0.1"
        assert data["excluded_cert_count"] == 2
    finally:
        client.close()
        engine.dispose()
