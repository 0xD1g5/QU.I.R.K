"""Dashboard wiring tests — Phase 11 fix verification.

Tests:
  - test_deps_default_db_path         : deps.py _default_db_path() returns './quirk.db' (GAP-INT-01)
  - test_deps_db_path_env_override    : QUIRK_DB_PATH env var override still works
  - test_server_sets_quirk_serve_port : server.py sets QUIRK_SERVE_PORT before uvicorn.run() (GAP-INT-02)
  - test_derive_cbom_ssh_algorithms   : _derive_cbom() parses ssh_audit_json (RED — Plan 02)
  - test_derive_cbom_ssh_only_scan    : _derive_cbom() returns non-empty for SSH-only scan (RED — Plan 02)
"""
from __future__ import annotations

import json
import os
import unittest.mock

import pytest

from quirk.dashboard.api.deps import _default_db_path
from quirk.dashboard.api.routes.scan import _derive_cbom
from quirk.models import CryptoEndpoint


# ---------------------------------------------------------------------------
# GAP-INT-01 — deps.py default db_path
# ---------------------------------------------------------------------------


def test_deps_default_db_path():
    """_default_db_path() returns './quirk.db' when QUIRK_DB_PATH env var is not set.

    Verifies GAP-INT-01: the dashboard fallback DB path matches config_template.yaml.
    """
    env_without_db_path = {k: v for k, v in os.environ.items() if k != "QUIRK_DB_PATH"}
    with unittest.mock.patch.dict(os.environ, env_without_db_path, clear=True):
        result = _default_db_path()
    assert result == "./quirk.db", (
        f"Expected './quirk.db' but got '{result}'. "
        "Fix: change the default in deps.py to match config_template.yaml."
    )


def test_deps_db_path_env_override():
    """_default_db_path() returns the custom path when QUIRK_DB_PATH is set."""
    with unittest.mock.patch.dict(os.environ, {"QUIRK_DB_PATH": "/tmp/custom.db"}):
        result = _default_db_path()
    assert result == "/tmp/custom.db"


# ---------------------------------------------------------------------------
# GAP-INT-02 — server.py QUIRK_SERVE_PORT propagation
# ---------------------------------------------------------------------------


def test_server_sets_quirk_serve_port():
    """serve() sets os.environ['QUIRK_SERVE_PORT'] to str(port) before uvicorn.run().

    Verifies GAP-INT-02: the PDF exporter can read the correct port from the env var.
    The test mocks uvicorn.run so the server never actually starts; it checks that
    the env var is already set at the moment uvicorn.run() would be called.
    """
    from quirk.dashboard.server import serve

    captured_port_in_env: list[str] = []

    def _check_env_and_stop(*args, **kwargs):
        # Read the env var value at the moment uvicorn.run() is called
        captured_port_in_env.append(os.environ.get("QUIRK_SERVE_PORT", "__NOT_SET__"))
        # Raise to prevent uvicorn from actually starting
        raise SystemExit(0)

    with unittest.mock.patch("uvicorn.run", side_effect=_check_env_and_stop):
        with pytest.raises(SystemExit):
            serve(port=9999, no_open=True)

    assert captured_port_in_env, "uvicorn.run mock was never called"
    assert captured_port_in_env[0] == "9999", (
        f"Expected QUIRK_SERVE_PORT='9999' at uvicorn.run() call, got '{captured_port_in_env[0]}'. "
        "Fix: add os.environ['QUIRK_SERVE_PORT'] = str(port) before uvicorn.run() in server.py."
    )


# ---------------------------------------------------------------------------
# SSH CBOM parsing — RED state (will go GREEN in Plan 02)
# ---------------------------------------------------------------------------


def _make_ssh_endpoint(ssh_audit_json: str) -> CryptoEndpoint:
    """Create a minimal CryptoEndpoint with SSH data for testing _derive_cbom()."""
    ep = unittest.mock.MagicMock(spec=CryptoEndpoint)
    ep.protocol = "SSH"
    ep.ssh_audit_json = ssh_audit_json
    ep.cert_pubkey_alg = None
    ep.cert_pubkey_size = None
    ep.tls_version = None
    ep.jwt_scan_json = None
    ep.cloud_scan_json = None
    ep.host = "10.0.0.1"
    ep.port = 22
    return ep


def test_derive_cbom_ssh_algorithms():
    """_derive_cbom() with ssh_audit_json returns CbomComponent entries for SSH algorithms.

    RED state — _derive_cbom() does not yet parse ssh_audit_json. This test will go GREEN
    in Plan 02 when SSH CBOM parsing is added.

    Expected: result contains entries for curve25519-sha256, rsa-sha2-512, aes256-ctr,
    and hmac-sha2-256.
    """
    ssh_data = {
        "kex": [{"algorithm": "curve25519-sha256"}],
        "key": [{"algorithm": "rsa-sha2-512", "keysize": 3072}],
        "enc": [{"algorithm": "aes256-ctr"}],
        "mac": [{"algorithm": "hmac-sha2-256"}],
    }
    ep = _make_ssh_endpoint(json.dumps(ssh_data))

    result = _derive_cbom([ep])
    alg_names = [c.algorithm for c in result]

    assert "curve25519-sha256" in alg_names, f"Expected 'curve25519-sha256' in CBOM, got: {alg_names}"
    assert "rsa-sha2-512" in alg_names, f"Expected 'rsa-sha2-512' in CBOM, got: {alg_names}"
    assert "aes256-ctr" in alg_names, f"Expected 'aes256-ctr' in CBOM, got: {alg_names}"
    assert "hmac-sha2-256" in alg_names, f"Expected 'hmac-sha2-256' in CBOM, got: {alg_names}"


def test_derive_cbom_ssh_only_scan():
    """_derive_cbom() with only SSH endpoints (no TLS) returns a non-empty list.

    RED state — will go GREEN in Plan 02 when SSH CBOM parsing is added.
    """
    ssh_data = {
        "kex": [{"algorithm": "curve25519-sha256"}],
        "key": [{"algorithm": "rsa-sha2-256"}],
        "enc": [{"algorithm": "aes128-ctr"}],
        "mac": [{"algorithm": "hmac-sha2-256"}],
    }
    ep = _make_ssh_endpoint(json.dumps(ssh_data))

    result = _derive_cbom([ep])
    assert len(result) > 0, (
        "Expected _derive_cbom() to return at least one component for an SSH-only scan, "
        "but got an empty list. Fix: add ssh_audit_json parsing in Plan 02."
    )
