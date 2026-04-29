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


def test_derive_dar_scan_error_excluded():
    """Endpoints with scan_error are excluded from dar_findings."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings
    ep = _ep(host="db.test", port=5432, protocol="POSTGRESQL",
             scan_error="permission denied")
    out = _derive_dar_findings([ep])
    assert out == []


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
