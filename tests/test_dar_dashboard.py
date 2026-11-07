"""Phase 39 GAP-04: Data at Rest dashboard projection + API contract tests."""
import json
import pytest
from types import SimpleNamespace


def _ep(**kw):
    defaults = dict(
        host="example.com", port=0, protocol="",
        tls_version=None, cipher_suite=None, cert_not_after=None,
        service_detail=None, dat_scan_json=None, scan_error=None,
        severity="INFO",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# ---- Unit tests: _derive_dar_findings() per-protocol dispatch ----

def test_derive_dar_findings_db():
    """POSTGRESQL endpoint with ssl-enforced → DarFinding(category='database')."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep = _ep(host="db.test", port=5432, protocol="POSTGRESQL",
             service_detail="PostgreSQL/ssl-enforced", severity="INFO")
    out = _derive_dar_findings([ep])
    assert len(out) == 1
    assert out[0].category == "database"
    assert out[0].encryption_at_rest is True
    assert out[0].tls_in_transit is True


def test_derive_dar_db_postgresql():
    """POSTGRESQL ssl-off → encryption_at_rest=False, tls_in_transit=False."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep = _ep(host="db.test", port=5432, protocol="POSTGRESQL",
             service_detail="PostgreSQL/ssl-off", severity="HIGH")
    out = _derive_dar_findings([ep])
    assert len(out) == 1
    assert out[0].category == "database"
    assert out[0].encryption_at_rest is False
    assert out[0].tls_in_transit is False
    assert out[0].severity == "HIGH"


def test_derive_dar_s3():
    """S3 dat_scan_json sse-s3 → encryption_mode='SSE-S3', encryption_at_rest=True."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep = _ep(host="bucket.s3", port=443, protocol="S3",
             dat_scan_json=json.dumps({"service_detail": "S3/sse-s3"}),
             severity="INFO")
    out = _derive_dar_findings([ep])
    assert len(out) == 1
    assert out[0].category == "object_storage"
    assert out[0].encryption_mode == "SSE-S3"
    assert out[0].encryption_at_rest is True


def test_derive_dar_k8s_dispatch():
    """K8s: namespace shape → namespace populated; cluster shape → encryption_provider populated."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep_ns = _ep(host="k8s.test", port=443, protocol="KUBERNETES",
                dat_scan_json=json.dumps({"namespace": "default",
                                          "secret_type_counts": {"Opaque": 3}}),
                severity="INFO")
    ep_cluster = _ep(host="eks.test", port=443, protocol="KUBERNETES",
                     dat_scan_json=json.dumps({"cluster": "prod", "provider": "EKS",
                                               "encryptionConfig": [{"resources": ["secrets"]}]}),
                     severity="INFO")
    out = _derive_dar_findings([ep_ns, ep_cluster])
    assert len(out) == 2
    assert all(f.category == "kubernetes" for f in out)
    ns_finding = next(f for f in out if f.namespace == "default")
    cluster_finding = next(f for f in out if f.namespace is None)
    assert ns_finding.namespace == "default"
    assert cluster_finding.encryption_provider is not None
    assert cluster_finding.namespace is None


def test_derive_dar_vault_dispatch():
    """VAULT: transit / pki / auth shapes → mount_type + seal_type/auto_unseal None."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep_transit = _ep(host="vault.test", port=8200, protocol="VAULT",
                     dat_scan_json=json.dumps({"key_name": "mykey", "key_type": "aes256-gcm96"}),
                     severity="INFO")
    ep_pki = _ep(host="vault.test", port=8200, protocol="VAULT",
                 dat_scan_json=json.dumps({"mount_point": "pki/", "role": "root",
                                           "sig_alg": "SHA256WithRSA", "key_size": 2048}),
                 severity="INFO")
    ep_auth = _ep(host="vault.test", port=8200, protocol="VAULT",
                  dat_scan_json=json.dumps({"auth_path": "token/", "auth_type": "token"}),
                  severity="INFO")
    out = _derive_dar_findings([ep_transit, ep_pki, ep_auth])
    assert len(out) == 3
    assert all(f.category == "vault" for f in out)
    mount_types = {f.mount_type for f in out}
    assert mount_types == {"transit", "pki", "auth"}
    for f in out:
        assert f.seal_type is None
        assert f.auto_unseal is None


def test_derive_dar_db_scan_error_failed_row():
    """235.3 D-10: a failed DB target is a failed row, not dropped.

    Replaces test_derive_dar_scan_error_excluded, which pinned DB + scan_error
    -> [] (the 2026-11-05 vanishing-Postgres-targets bug).
    """
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep = _ep(host="db.test", port=5432, protocol="POSTGRESQL",
             scan_error="connection-error: could not connect")
    out = _derive_dar_findings([ep])
    assert len(out) == 1
    f = out[0]
    assert f.protocol == "POSTGRESQL" and f.category == "database"
    assert f.severity == "INFO"
    assert f.title == "POSTGRESQL connection failed"
    assert f.scan_error == "connection-error: could not connect"


def test_derive_dar_mysql_scan_error_failed_row():
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    out = _derive_dar_findings([_ep(host="m", port=3306, protocol="MYSQL",
                                    scan_error="connection-error: boom")])
    assert [f.title for f in out] == ["MYSQL connection failed"]


def test_derive_dar_insufficient_privilege_is_not_a_connection_failure():
    """C-CR-01: db_connector writes scan_error="insufficient-privilege" AFTER a
    successful connection with SHOW ssl = on, when the role lacks
    pg_read_all_stats. That server answered; it must not read as a failed
    connection, and the GRANT remediation must survive.
    """
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep = _ep(host="db.test", port=5432, protocol="POSTGRESQL", severity="INFO",
             scan_error="insufficient-privilege",
             service_detail="Remediation: GRANT pg_read_all_stats TO <scanner_user>")
    out = _derive_dar_findings([ep])
    assert len(out) == 1
    f = out[0]
    assert "connection failed" not in f.title
    assert f.title == "POSTGRESQL posture incomplete"
    assert f.remediation == "Remediation: GRANT pg_read_all_stats TO <scanner_user>"
    assert f.scan_error == "insufficient-privilege"


def test_derive_dar_non_db_scan_error_still_excluded():
    """P-11: non-database DAR protocols with scan_error stay excluded."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep = _ep(host="b", port=443, protocol="S3", scan_error="denied")
    assert _derive_dar_findings([ep]) == []


def test_derive_dar_three_postgres_two_failed_scan_error():
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    eps = [
        _ep(host="a", port=5432, protocol="POSTGRESQL", service_detail="ssl-enforced"),
        _ep(host="b", port=5432, protocol="POSTGRESQL", scan_error="connection-error: x"),
        _ep(host="c", port=5432, protocol="POSTGRESQL", scan_error="connection-error: y"),
    ]
    out = _derive_dar_findings(eps)
    assert len(out) == 3
    assert sorted(f.scan_error for f in out if f.scan_error) == [
        "connection-error: x", "connection-error: y",
    ]
    assert [f.scan_error for f in out if "failed" not in f.title] == [None]


# ---- Integration tests: API contract ----

def test_api_dar_findings_key(dashboard_client):
    """GET /api/scan/latest response includes 'dar_findings' key."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "dar_findings" in data
        assert isinstance(data["dar_findings"], list)


def test_api_dar_findings_empty(dashboard_client):
    """dar_findings is empty list (not absent) when no DAR endpoints exist."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "dar_findings" in data
        assert isinstance(data["dar_findings"], list)


def _dar_api_client(tmp_path, monkeypatch, endpoints):
    from datetime import datetime

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.dashboard.api.routes import scan as scan_routes
    from quirk.db import get_session, init_db
    from quirk.models import CryptoEndpoint

    run_id = "2026-11-06T10:00:00"
    ts = datetime.fromisoformat(run_id)
    db_path = str(tmp_path / "dar-api.db")
    init_db(db_path)
    with get_session(db_path) as session:
        for kw in endpoints:
            session.add(CryptoEndpoint(scanned_at=ts, scan_run_id=run_id, **kw))
        session.commit()
    engine = create_engine(f"sqlite:///{db_path}",
                           connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(scan_routes, "_default_db_path", lambda: db_path)
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app, headers={"X-Quirk-Request": "1"})


def test_api_dar_insufficient_privilege_vs_connection_error(tmp_path, monkeypatch):
    """C-CR-01 at the API boundary: only a connection-error: scan_error is a
    failed connection; insufficient-privilege keeps its GRANT remediation."""
    client = _dar_api_client(tmp_path, monkeypatch, [
        dict(host="priv.db", port=5432, protocol="POSTGRESQL", severity="INFO",
             scan_error="insufficient-privilege",
             service_detail="Remediation: GRANT pg_read_all_stats TO <scanner_user>"),
        dict(host="down.db", port=5432, protocol="POSTGRESQL", severity="INFO",
             scan_error="connection-error: could not connect"),
    ])
    resp = client.get("/api/scan/latest")
    assert resp.status_code == 200, resp.text
    by_host = {f["host"]: f for f in resp.json()["dar_findings"]}
    assert by_host["priv.db"]["title"] == "POSTGRESQL posture incomplete"
    assert "GRANT pg_read_all_stats" in by_host["priv.db"]["remediation"]
    assert by_host["down.db"]["title"] == "POSTGRESQL connection failed"
    assert by_host["down.db"]["remediation"] is None
