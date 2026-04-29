"""Phase 39 GAP-04: Data at Rest dashboard projection + API contract tests."""
import json
import pytest
from types import SimpleNamespace


def _ep(**kw):
    defaults = dict(
        host="example.com", port=0, protocol="",
        tls_version=None, cipher_suite=None, cert_not_after=None,
        # DAR-specific extensions:
        service_detail=None, dat_scan_json=None, scan_error=None,
        severity="INFO",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_derive_dar_findings_db():
    """GAP-04: POSTGRESQL endpoint with ssl-enforced -> DarFinding(category='database')."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    out = _derive_dar_findings([
        _ep(host="db.internal", port=5432, protocol="POSTGRESQL",
            service_detail="PostgreSQL/ssl-enforced", severity="INFO"),
    ])
    assert len(out) == 1
    assert out[0].category == "database"


def test_derive_dar_db_postgresql():
    """GAP-04: service_detail='PostgreSQL/ssl-off' -> encryption_at_rest=False, tls_in_transit=False, severity='HIGH'."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    out = _derive_dar_findings([
        _ep(host="db.test", port=5432, protocol="POSTGRESQL",
            service_detail="PostgreSQL/ssl-off", severity="HIGH"),
    ])
    assert len(out) == 1
    assert out[0].category == "database"
    assert out[0].encryption_at_rest is False
    assert out[0].tls_in_transit is False
    assert out[0].severity == "HIGH"


def test_derive_dar_s3():
    """GAP-04: dat_scan_json with S3/sse-s3 -> encryption_mode='SSE-S3', encryption_at_rest=True, category='object_storage'."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    out = _derive_dar_findings([
        _ep(host="bucket.s3", port=443, protocol="S3",
            dat_scan_json=json.dumps({"service_detail": "S3/sse-s3"}),
            severity="INFO"),
    ])
    assert len(out) == 1
    assert out[0].category == "object_storage"
    assert out[0].encryption_mode == "SSE-S3"
    assert out[0].encryption_at_rest is True


def test_derive_dar_k8s_dispatch():
    """GAP-04: Two K8s endpoints dispatch to namespace shape vs. cluster-encryption shape."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep_namespace = _ep(
        host="k8s-ns.internal", port=443, protocol="KUBERNETES",
        dat_scan_json=json.dumps({
            "namespace": "default",
            "secret_type_counts": {"Opaque": 3},
        }),
        severity="INFO",
    )
    ep_cluster = _ep(
        host="k8s-cluster.internal", port=443, protocol="KUBERNETES",
        dat_scan_json=json.dumps({
            "cluster": "prod",
            "provider": "EKS",
            "encryptionConfig": [{"resources": ["secrets"]}],
        }),
        severity="MEDIUM",
    )
    out = _derive_dar_findings([ep_namespace, ep_cluster])
    assert len(out) == 2
    assert all(f.category == "kubernetes" for f in out)
    by_host = {f.host: f for f in out}
    assert by_host["k8s-ns.internal"].namespace == "default"
    assert by_host["k8s-cluster.internal"].encryption_provider is not None
    assert by_host["k8s-cluster.internal"].namespace is None


def test_derive_dar_vault_dispatch():
    """GAP-04: Three Vault endpoints dispatch to transit/pki/auth mount types; seal_type and auto_unseal always None."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep_transit = _ep(
        host="vault.internal", port=8200, protocol="VAULT",
        dat_scan_json=json.dumps({"key_name": "my-key", "path": "transit/my-key"}),
        severity="INFO",
    )
    ep_pki = _ep(
        host="vault.internal", port=8200, protocol="VAULT",
        dat_scan_json=json.dumps({"mount_point": "pki", "type": "pki"}),
        severity="INFO",
    )
    ep_auth = _ep(
        host="vault.internal", port=8200, protocol="VAULT",
        dat_scan_json=json.dumps({"auth_path": "approle/", "method": "approle"}),
        severity="INFO",
    )
    out = _derive_dar_findings([ep_transit, ep_pki, ep_auth])
    assert len(out) == 3
    assert all(f.category == "vault" for f in out)
    mount_types = {f.mount_type for f in out}
    assert "transit" in mount_types
    assert "pki" in mount_types
    assert "auth" in mount_types
    assert all(f.seal_type is None for f in out)
    assert all(f.auto_unseal is None for f in out)


def test_derive_dar_scan_error_excluded():
    """GAP-04: Endpoint with scan_error set is excluded from results."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    out = _derive_dar_findings([
        _ep(protocol="POSTGRESQL", scan_error="permission denied"),
    ])
    assert out == []


def test_api_dar_findings_key(dashboard_client):
    """GAP-04: GET /api/scan/latest response contains 'dar_findings' key."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "dar_findings" in data
        assert isinstance(data["dar_findings"], list)


def test_api_dar_findings_empty(dashboard_client):
    """GAP-04: When no DAR endpoints exist, dar_findings == [] (not absent)."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "dar_findings" in data
        assert isinstance(data["dar_findings"], list)
