"""Hardening tests for network-exposed console deployments.

Covers the cloud-console hardening pass:

  serve() startup guardrail
    - loopback bind with no token starts normally
    - network-reachable bind with no token + no --insecure REFUSES (exit 2)
    - --insecure overrides the refusal
    - a configured QUIRK_API_TOKEN satisfies the guardrail
    - uvicorn is started with proxy_headers + forwarded_allow_ips so the real
      sensor IP survives a reverse proxy

  SecurityHeadersMiddleware
    - defensive headers present on responses
    - HSTS opt-in via QUIRK_HSTS

  Sensor IP allowlist (QUIRK_SENSOR_IP_ALLOWLIST)
    - helper parse/match semantics
    - push from an off-allowlist source is rejected 403 + audit row
"""
from __future__ import annotations

import sys
import unittest.mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, IntegrationDelivery


# ---------------------------------------------------------------------------
# serve() startup guardrail
# ---------------------------------------------------------------------------


def _mock_uvicorn():
    """Return a MagicMock standing in for the uvicorn module (run is a no-op)."""
    mock = unittest.mock.MagicMock()
    mock.run = unittest.mock.MagicMock()
    return mock


def _run_serve(monkeypatch, **kwargs):
    """Call serve() with uvicorn mocked; return the mock for assertions.

    QUIRK_CONFIG_PATH is pointed at a nonexistent file so the no-token branch is
    deterministic regardless of any config.yaml in the working tree.
    """
    from quirk.dashboard import server

    monkeypatch.setenv("QUIRK_CONFIG_PATH", "/nonexistent/quirk-test-config.yaml")
    mock = _mock_uvicorn()
    with unittest.mock.patch.dict(sys.modules, {"uvicorn": mock}):
        server.serve(no_open=True, **kwargs)
    return mock


def test_loopback_no_token_starts(monkeypatch):
    """Loopback bind with no token is always allowed (local dev default)."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    mock = _run_serve(monkeypatch, host="127.0.0.1")
    assert mock.run.called, "serve() should start on loopback without a token"


def test_network_bind_no_token_refuses(monkeypatch):
    """Network-reachable bind + no token + no --insecure → refuse with exit 2."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    from quirk.dashboard import server

    monkeypatch.setenv("QUIRK_CONFIG_PATH", "/nonexistent/quirk-test-config.yaml")
    mock = _mock_uvicorn()
    with unittest.mock.patch.dict(sys.modules, {"uvicorn": mock}):
        with pytest.raises(SystemExit) as exc:
            server.serve(host="0.0.0.0", no_open=True)
    assert exc.value.code == 2, f"Expected exit code 2, got {exc.value.code}"
    assert not mock.run.called, "uvicorn must NOT start on a refused bind"


def test_insecure_flag_overrides_refusal(monkeypatch):
    """--insecure lets a token-less network bind proceed (explicit opt-in)."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    mock = _run_serve(monkeypatch, host="0.0.0.0", insecure=True)
    assert mock.run.called, "--insecure should allow a token-less network bind"


def test_configured_token_satisfies_guardrail(monkeypatch):
    """A configured QUIRK_API_TOKEN allows a network bind without --insecure."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "s3cret-operator-token")
    mock = _run_serve(monkeypatch, host="0.0.0.0")
    assert mock.run.called, "A configured operator token should satisfy the guardrail"


def test_uvicorn_started_with_proxy_headers(monkeypatch):
    """uvicorn.run gets proxy_headers=True and forwarded_allow_ips from env."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.setenv("QUIRK_TRUST_PROXY", "10.0.0.5")
    mock = _run_serve(monkeypatch, host="127.0.0.1")
    assert mock.run.called
    kwargs = mock.run.call_args.kwargs
    assert kwargs.get("proxy_headers") is True, "proxy_headers must be enabled"
    assert kwargs.get("forwarded_allow_ips") == "10.0.0.5", (
        f"forwarded_allow_ips should honour QUIRK_TRUST_PROXY, got {kwargs.get('forwarded_allow_ips')!r}"
    )


def test_trust_proxy_defaults_to_loopback(monkeypatch):
    """With QUIRK_TRUST_PROXY unset, forwarded_allow_ips defaults to loopback."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("QUIRK_TRUST_PROXY", raising=False)
    mock = _run_serve(monkeypatch, host="127.0.0.1")
    assert mock.run.call_args.kwargs.get("forwarded_allow_ips") == "127.0.0.1"


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------


def _client():
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


def test_security_headers_present(monkeypatch):
    """Defensive headers are attached to responses."""
    monkeypatch.delenv("QUIRK_HSTS", raising=False)
    resp = _client().get("/api/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "no-referrer"
    # HSTS is opt-in — absent by default.
    assert "Strict-Transport-Security" not in resp.headers


def test_hsts_opt_in(monkeypatch):
    """QUIRK_HSTS=1 enables the Strict-Transport-Security header."""
    monkeypatch.setenv("QUIRK_HSTS", "1")
    resp = _client().get("/api/health")
    hsts = resp.headers.get("Strict-Transport-Security", "")
    assert "max-age=31536000" in hsts and "includeSubDomains" in hsts


# ---------------------------------------------------------------------------
# Sensor IP allowlist helpers
# ---------------------------------------------------------------------------


def test_ip_allowlist_parse_and_match(monkeypatch):
    from quirk.dashboard.api.middleware import sensor_auth

    monkeypatch.setenv("QUIRK_SENSOR_IP_ALLOWLIST", "203.0.113.4, 198.51.100.0/24")
    nets = sensor_auth._ip_allowlist()
    assert len(nets) == 2
    assert sensor_auth._ip_allowed("203.0.113.4", nets) is True
    assert sensor_auth._ip_allowed("198.51.100.77", nets) is True
    assert sensor_auth._ip_allowed("203.0.113.9", nets) is False
    assert sensor_auth._ip_allowed("10.0.0.1", nets) is False
    # Unparseable / missing source with an allowlist in force → denied.
    assert sensor_auth._ip_allowed("not-an-ip", nets) is False
    assert sensor_auth._ip_allowed(None, nets) is False


def test_ip_allowlist_empty_allows_all(monkeypatch):
    from quirk.dashboard.api.middleware import sensor_auth

    monkeypatch.delenv("QUIRK_SENSOR_IP_ALLOWLIST", raising=False)
    nets = sensor_auth._ip_allowlist()
    assert nets == []
    # Empty allowlist disables the control — everything passes.
    assert sensor_auth._ip_allowed("10.0.0.1", nets) is True
    assert sensor_auth._ip_allowed(None, nets) is True


def test_malformed_allowlist_entry_skipped(monkeypatch):
    from quirk.dashboard.api.middleware import sensor_auth

    monkeypatch.setenv("QUIRK_SENSOR_IP_ALLOWLIST", "bogus, 192.0.2.0/24")
    nets = sensor_auth._ip_allowlist()
    assert len(nets) == 1
    assert sensor_auth._ip_allowed("192.0.2.10", nets) is True


def test_push_from_off_allowlist_source_rejected(monkeypatch):
    """An allowlist that excludes the caller's source IP → 403 + audit row.

    The TestClient's pseudo source ("testclient"/loopback) is not inside the
    203.0.113.0/24 allowlist, so the push is rejected at the network layer
    before token handling.
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.setenv("QUIRK_SENSOR_IP_ALLOWLIST", "203.0.113.0/24")

    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
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
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        "/api/sensor/push",
        content=b"irrelevant-body",
        headers={"Authorization": "Bearer anything"},
    )
    assert resp.status_code == 403, f"Off-allowlist push must be 403, got {resp.status_code}: {resp.text}"

    db = TestingSession()
    try:
        rows = (
            db.query(IntegrationDelivery)
            .filter(IntegrationDelivery.error_summary == "sensor_ip_not_allowed")
            .all()
        )
        assert len(rows) >= 1, "Expected a sensor_ip_not_allowed audit row"
    finally:
        db.close()
