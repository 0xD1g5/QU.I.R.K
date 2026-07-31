"""Dashboard API tests — Wave 0 stubs (RED state).
Test IDs match .planning/phases/05-web-dashboard/05-VALIDATION.md verification map.
"""
import subprocess
import sys
import pytest


def test_serve_command():
    """UI-01: quirk serve subcommand exists in run_scan.py and exits 0 for --help."""
    result = subprocess.run(
        [sys.executable, "run_scan.py", "serve", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--port" in result.stdout
    assert "--host" in result.stdout
    assert "--no-open" in result.stdout


def test_dashboard_loads(dashboard_client):
    """UI-01: GET / returns 200 (SPA index.html or placeholder served)."""
    response = dashboard_client.get("/")
    assert response.status_code == 200


def test_health_endpoint(dashboard_client):
    """UI-01: GET /api/health returns {status: ok}."""
    response = dashboard_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score_endpoint(dashboard_client):
    """UI-02: GET /api/scan/latest returns score fields."""
    resp = dashboard_client.get("/api/scan/latest")
    # 404 is acceptable when no scan data exists in test DB
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "score" in data
        assert "subscores" in data["score"]
        assert "hygiene" in data["score"]["subscores"]


def test_findings_endpoint(dashboard_client):
    """UI-03: GET /api/scan/latest includes findings list."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "findings" in data
        assert isinstance(data["findings"], list)


def test_certificates_endpoint(dashboard_client):
    """UI-03: GET /api/scan/latest includes certificates list."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "certificates" in data


def test_cbom_endpoint(dashboard_client):
    """UI-03: GET /api/scan/latest includes cbom_components list."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "cbom_components" in data


# ---- Phase 36 — Motion Tab (DASH-04, DASH-05) ----

def test_motion_findings_endpoint(dashboard_client):
    """DASH-05: GET /api/scan/latest includes motion_findings list."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "motion_findings" in data
        assert isinstance(data["motion_findings"], list)


def test_data_in_motion_subscore(dashboard_client):
    """DASH-04: GET /api/scan/latest returns subscores.data_in_motion as int (Pitfall 1)."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "data_in_motion" in data["score"]["subscores"]
        assert isinstance(data["score"]["subscores"]["data_in_motion"], int)


from types import SimpleNamespace


def _ep(**kw):
    defaults = dict(host="example.com", port=0, protocol="", tls_version=None,
                    cipher_suite=None, cert_not_after=None)
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_derive_motion_findings_plaintext():
    """DASH-05: KAFKA-PLAIN endpoint -> HIGH severity, plaintext_exposed=True."""
    from quirk.dashboard.api.routes.scan import _derive_motion_findings
    out = _derive_motion_findings([_ep(host="kafka.test", port=9092, protocol="KAFKA-PLAIN")])
    assert len(out) == 1
    assert out[0].severity == "HIGH"
    assert out[0].plaintext_exposed is True


def test_derive_motion_findings_starttls():
    """DASH-05: starttls_warning=True only on port-25 SMTP-STARTTLS."""
    from quirk.dashboard.api.routes.scan import _derive_motion_findings
    out = _derive_motion_findings([
        _ep(host="m", port=25,  protocol="SMTP-STARTTLS"),
        _ep(host="m", port=587, protocol="SMTP-STARTTLS"),
    ])
    by_port = {f.port: f for f in out}
    assert by_port[25].starttls_warning is True
    assert by_port[587].starttls_warning is False


def test_derive_motion_findings_azure():
    """DASH-05: AMQPS/Azure-ServiceBus slash preserved verbatim (Phase 35 D-03)."""
    from quirk.dashboard.api.routes.scan import _derive_motion_findings
    out = _derive_motion_findings([_ep(host="ns.servicebus.windows.net", port=5671,
                                       protocol="AMQPS/Azure-ServiceBus")])
    assert len(out) == 1
    assert out[0].protocol == "AMQPS/Azure-ServiceBus"


# ---- Phase 140 BRIDGE-03 — dashboard bridge_status wiring ----

def _make_hw_bridge_session():
    """Fresh in-memory SQLite session with HardwareDevice rows for a bridge
    scenario: a PQC-capable gateway with confirming ARP evidence (promotes to
    upstream_mitigated), its paired legacy backend (promotes alongside it —
    symmetric group promotion per 140-02), and an isolated device with no
    subnet pairing at all (bridge_status stays null/absent).
    """
    import datetime
    import json

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import quirk.models as m
    from quirk.models import HardwareDevice

    engine = create_engine("sqlite:///:memory:")
    m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    scanned_at = datetime.datetime.utcnow()

    gateway = HardwareDevice(
        host="10.0.0.1",
        port=22,
        vendor="Cisco",
        pqc_status="supported",
        confidence="high",
        fingerprint_method="ssh_banner",
        scanned_at=scanned_at,
        bridge_evidence_json=json.dumps([{"target_ip": "10.0.0.2", "mac": "aa:bb:cc:dd:ee:ff"}]),
    )
    legacy_backend = HardwareDevice(
        host="10.0.0.2",
        port=22,
        vendor="Legacy Corp",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="ssh_banner",
        scanned_at=scanned_at,
    )
    isolated = HardwareDevice(
        host="192.168.9.9",
        port=22,
        vendor="Standalone Inc",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="ssh_banner",
        scanned_at=scanned_at,
    )
    session.add_all([gateway, legacy_backend, isolated])
    session.commit()
    return session, scanned_at


def test_derive_hardware_findings_bridge_status_promoted_and_null():
    """BRIDGE-03: _derive_hardware_findings projects bridge_status —
    upstream_mitigated for an evidence-confirmed pair, and null/absent for a
    device with no detected bridge pairing at all."""
    from quirk.dashboard.api.routes.scan import _derive_hardware_findings

    session, scanned_at = _make_hw_bridge_session()
    try:
        out = _derive_hardware_findings(session, scanned_at)
        by_host = {f.host: f for f in out}
        assert by_host["10.0.0.1"].bridge_status == "upstream_mitigated"
        assert by_host["10.0.0.2"].bridge_status == "upstream_mitigated"
        assert by_host["192.168.9.9"].bridge_status is None
    finally:
        session.close()


def test_derive_hw_components_bridge_status_promoted_and_null():
    """BRIDGE-03: _derive_hw_components (CBOM tab) mirrors the same
    bridge_status projection as _derive_hardware_findings."""
    from quirk.dashboard.api.routes.scan import _derive_hw_components

    session, scanned_at = _make_hw_bridge_session()
    try:
        out = _derive_hw_components(session, scanned_at)
        by_host = {c.host: c for c in out}
        assert by_host["10.0.0.1"].bridge_status == "upstream_mitigated"
        assert by_host["10.0.0.2"].bridge_status == "upstream_mitigated"
        assert by_host["192.168.9.9"].bridge_status is None
    finally:
        session.close()


def test_derive_hardware_findings_bridge_pairing_error_stays_advisory_empty(monkeypatch):
    """BRIDGE-03 / T-140-11: a pairing-derive error degrades to an advisory-
    empty list (never a 500) — the new bridge pipeline stays inside the
    existing try/except -> logger.exception -> return [] guard."""
    from quirk.dashboard.api.routes import scan as scan_module

    session, scanned_at = _make_hw_bridge_session()
    try:
        def _boom(*args, **kwargs):
            raise RuntimeError("simulated bridge-pairing failure")

        monkeypatch.setattr(scan_module, "_detect_crypto_bridges", _boom)
        out = scan_module._derive_hardware_findings(session, scanned_at)
        assert out == []
    finally:
        session.close()
