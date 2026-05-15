"""
Phase 46 TLS-FIND-06 sentinel tests for chain_verified plumbing.

Covers:
- Task 1 (Tests 1-4): Schema column, default value, migration shim, idempotency.
- Task 2 (Tests 5-11): sslyze success/failure assignment, fallback CERT_REQUIRED
  pre-pass (True/False/None), and scan_one D-01 validation gate merge.
"""
from __future__ import annotations

import os
import sqlite3
import ssl
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import inspect as sa_inspect

from quirk.db import init_db, _ensure_columns, _PHASE46_COLUMNS
from quirk.models import CryptoEndpoint


# ---------------------------------------------------------------------------
# Task 1: schema + migration shim
# ---------------------------------------------------------------------------

def _tmp_db_path(name: str = "phase46.db") -> str:
    d = tempfile.mkdtemp(prefix="quirk_phase46_")
    return os.path.join(d, name)


def test_chain_verified_column_present_after_init_db():
    """Test 1: init_db() exposes chain_verified column on crypto_endpoints."""
    db_path = _tmp_db_path()
    engine = init_db(db_path)
    cols = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    assert "chain_verified" in cols


def test_crypto_endpoint_default_chain_verified_is_none():
    """Test 2: A freshly-constructed CryptoEndpoint has chain_verified=None."""
    ep = CryptoEndpoint(host="x", port=1)
    assert ep.chain_verified is None


def test_migration_shim_adds_column_to_legacy_db():
    """Test 3: Legacy SQLite DB without chain_verified gains it via init_db()."""
    db_path = _tmp_db_path("legacy.db")
    # Hand-create a minimal legacy crypto_endpoints table with no chain_verified.
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE crypto_endpoints ("
            "id INTEGER PRIMARY KEY, host VARCHAR(255), port INTEGER)"
        )
        conn.execute("INSERT INTO crypto_endpoints (host, port) VALUES ('legacy.example', 443)")
        conn.commit()
    finally:
        conn.close()

    engine = init_db(db_path)
    cols = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    assert "chain_verified" in cols

    # Existing legacy rows have NULL for the new column.
    with engine.connect() as c:
        from sqlalchemy import text as _t
        rows = list(c.execute(_t("SELECT host, chain_verified FROM crypto_endpoints")))
    assert rows == [("legacy.example", None)]


def test_migration_shim_idempotent():
    """Test 4: init_db() is safe to call twice — column not duplicated, no error."""
    db_path = _tmp_db_path("idem.db")
    engine = init_db(db_path)
    # Call again on the already-migrated DB — must not raise.
    engine = init_db(db_path)
    # And explicitly hammer the shim itself (Phase 77 D-21: now via generic helper).
    _ensure_columns(engine, "crypto_endpoints", _PHASE46_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _PHASE46_COLUMNS)
    cols = [c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")]
    assert cols.count("chain_verified") == 1


# ---------------------------------------------------------------------------
# Task 2: scanner plumbing (sslyze + fallback) + scan_one D-01 gate
# ---------------------------------------------------------------------------

# These tests import the scanner lazily so Task 1 can run independently.
from quirk.scanner import tls_scanner as _tls  # noqa: E402


def _stub_scan_result_with_chain(verified: bool):
    """Build a minimal sslyze server_result whose certificate_info attempt
    completes and whose deployment.verified_certificate_chain is either a list
    (verified=True) or None (verified=False)."""
    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa_module

    # Build a leaf cert mock matching _make_mock_cert in test_sslyze_integration.py.
    leaf = MagicMock()
    leaf.subject.rfc4514_string.return_value = "CN=example.com"
    leaf.issuer.rfc4514_string.return_value = "CN=Test CA"
    sig = MagicMock(); sig.name = "sha256"
    leaf.signature_hash_algorithm = sig
    pubkey = MagicMock(spec=_rsa_module.RSAPublicKey)
    pubkey.key_size = 2048
    leaf.public_key.return_value = pubkey
    leaf.not_valid_before_utc = datetime(2026, 1, 1)
    leaf.not_valid_after_utc = datetime(2027, 1, 1)
    ext = MagicMock(); ext.value.get_values_for_type.return_value = []
    leaf.extensions.get_extension_for_class.return_value = ext

    deployment = MagicMock()
    deployment.received_certificate_chain = [leaf]
    deployment.verified_certificate_chain = [leaf] if verified else None

    cert_attempt = MagicMock()
    cert_attempt.status = _tls.ScanCommandAttemptStatusEnum.COMPLETED if _tls.SSLYZE_AVAILABLE else None
    cert_attempt.result.certificate_deployments = [deployment]

    scan = MagicMock()
    scan.certificate_info = cert_attempt
    # No cipher protocols accepted, no elliptic curves.
    for attr, _, _ in _tls._PROTO_MAP:
        a = MagicMock()
        a.status = None  # not COMPLETED, so skipped
        setattr(scan, attr, a)
    ec_attempt = MagicMock()
    ec_attempt.status = None
    scan.elliptic_curves = ec_attempt

    server_result = MagicMock()
    server_result.scan_status = _tls.ServerScanStatusEnum.COMPLETED if _tls.SSLYZE_AVAILABLE else None
    server_result.scan_result = scan
    return server_result


@pytest.mark.skipif(not _tls.SSLYZE_AVAILABLE, reason="sslyze not installed")
def test_sslyze_success_chain_verified_true():
    """Test 5: sslyze success path with verified_certificate_chain set → True."""
    server_result = _stub_scan_result_with_chain(verified=True)
    fake_scanner = MagicMock()
    fake_scanner.get_results.return_value = iter([server_result])
    with patch.object(_tls, "SslyzeScanner", return_value=fake_scanner):
        ep = _tls._scan_one_sslyze("example.com", 443, 5, True, logger=None)
    assert ep is not None
    assert ep.chain_verified is True


@pytest.mark.skipif(not _tls.SSLYZE_AVAILABLE, reason="sslyze not installed")
def test_sslyze_success_chain_verified_false():
    """Test 6: sslyze deployment.verified_certificate_chain=None → False."""
    server_result = _stub_scan_result_with_chain(verified=False)
    fake_scanner = MagicMock()
    fake_scanner.get_results.return_value = iter([server_result])
    with patch.object(_tls, "SslyzeScanner", return_value=fake_scanner):
        ep = _tls._scan_one_sslyze("example.com", 443, 5, True, logger=None)
    assert ep is not None
    assert ep.chain_verified is False


# ---- Fallback path tests --------------------------------------------------
#
# We patch `socket.create_connection` and `ssl.create_default_context` from
# inside quirk.scanner.tls_scanner so the fallback's CERT_REQUIRED pre-pass
# can be steered without touching the network.


class _FakeSocketCM:
    """Fake context manager returning itself as the socket."""
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


class _FakeSSLSocketCM:
    """Fake wrap_socket() context-manager. Optionally raises on entry."""
    def __init__(self, raise_exc=None, der=b"", version="TLSv1.2", cipher=("AES",)):
        self._raise = raise_exc
        self._der = der
        self._version = version
        self._cipher = cipher
    def __enter__(self):
        if self._raise is not None:
            raise self._raise
        return self
    def __exit__(self, *a):
        return False
    def version(self):
        return self._version
    def cipher(self):
        return self._cipher
    def getpeercert(self, binary_form=False):
        return self._der


class _FakeCtx:
    """Fake SSLContext whose wrap_socket() returns a configurable CM."""
    def __init__(self, on_wrap):
        self.check_hostname = False
        self.verify_mode = None
        self._on_wrap = on_wrap
    def wrap_socket(self, sock, server_hostname=None):
        return self._on_wrap()


def _patch_fallback_paths(verify_outcome, second_pass_outcome=None):
    """
    verify_outcome: 'success' | SSLCertVerificationError instance | other Exception
    second_pass_outcome: callable returning a wrap_socket CM (default: success with empty cert)
                         If 'success' isn't desired we still need pass 2 to attempt
                         metadata extraction; we keep it lightweight by always raising
                         a benign Exception which the existing CERT_NONE block catches.
    """
    call_count = {"n": 0}

    def _ctx_factory():
        call_count["n"] += 1
        n = call_count["n"]
        if n == 1:
            # Pass 1 = CERT_REQUIRED verification pre-pass
            if verify_outcome == "success":
                return _FakeCtx(lambda: _FakeSSLSocketCM())
            return _FakeCtx(lambda: _FakeSSLSocketCM(raise_exc=verify_outcome))
        # Pass 2 = CERT_NONE metadata extraction. We make it raise a benign
        # exception so we don't have to fabricate a parseable DER cert. The
        # outer try/except in _scan_one_fallback catches and records as
        # scan_error — that's fine for chain_verified-focused tests.
        if second_pass_outcome is not None:
            return _FakeCtx(second_pass_outcome)
        return _FakeCtx(lambda: _FakeSSLSocketCM(raise_exc=RuntimeError("metadata-noop")))

    sock_patch = patch.object(_tls.socket, "create_connection", return_value=_FakeSocketCM())
    ctx_patch = patch.object(_tls.ssl, "create_default_context", side_effect=_ctx_factory)
    return sock_patch, ctx_patch


def test_fallback_chain_verified_true_on_cert_required_success():
    """Test 7: CERT_REQUIRED handshake succeeds → chain_verified=True."""
    sock_p, ctx_p = _patch_fallback_paths("success")
    with sock_p, ctx_p:
        ep = _tls._scan_one_fallback("example.com", 443, 5, True, logger=None)
    assert ep.chain_verified is True


def test_fallback_chain_verified_false_on_ssl_cert_verification_error():
    """Test 8: CERT_REQUIRED raises SSLCertVerificationError → chain_verified=False."""
    err = ssl.SSLCertVerificationError("self signed certificate")
    sock_p, ctx_p = _patch_fallback_paths(err)
    with sock_p, ctx_p:
        ep = _tls._scan_one_fallback("example.com", 443, 5, True, logger=None)
    assert ep.chain_verified is False


def test_fallback_chain_verified_none_on_network_error():
    """Test 9: CERT_REQUIRED raises ConnectionRefusedError → chain_verified=None
    (per Pitfall 1: network errors must not produce false untrusted-CA findings)."""
    err = ConnectionRefusedError("connection refused")
    sock_p, ctx_p = _patch_fallback_paths(err)
    with sock_p, ctx_p:
        ep = _tls._scan_one_fallback("example.com", 443, 5, True, logger=None)
    assert ep.chain_verified is None


# ---- scan_one D-01 validation gate ---------------------------------------

def test_scan_one_d01_gate_merges_when_sslyze_half_populated():
    """Test 10: sslyze returns ep with cert_not_after=None and empty cert_subject
    → fallback runs and merges cert_not_after, cert_subject, chain_verified."""
    half = CryptoEndpoint(host="x", port=443, protocol="TLS")
    half.cert_not_after = None
    half.cert_subject = ""
    half.cert_issuer = ""
    half.cert_pubkey_size = None
    half.cert_pubkey_alg = None
    half.chain_verified = None

    fb = CryptoEndpoint(host="x", port=443, protocol="TLS")
    fb.cert_not_after = datetime(2027, 1, 1)
    fb.cert_subject = "CN=fallback.example.com"
    fb.cert_issuer = "CN=Fallback CA"
    fb.cert_pubkey_size = 2048
    fb.cert_pubkey_alg = "RSA"
    fb.chain_verified = False

    with patch.object(_tls, "SSLYZE_AVAILABLE", True), \
         patch.object(_tls, "_scan_one_sslyze", return_value=half) as m_sslyze, \
         patch.object(_tls, "_scan_one_fallback", return_value=fb) as m_fb:
        ep = _tls.scan_one("x", 443, 5, True, logger=None)

    m_sslyze.assert_called_once()
    m_fb.assert_called_once()
    assert ep.cert_not_after == datetime(2027, 1, 1)
    assert ep.cert_subject == "CN=fallback.example.com"
    assert ep.cert_issuer == "CN=Fallback CA"
    assert ep.cert_pubkey_size == 2048
    assert ep.cert_pubkey_alg == "RSA"
    assert ep.chain_verified is False


def test_scan_one_d01_gate_skips_when_sslyze_healthy():
    """Test 11: sslyze returns fully-populated ep → fallback NOT invoked."""
    healthy = CryptoEndpoint(host="x", port=443, protocol="TLS")
    healthy.cert_not_after = datetime(2027, 1, 1)
    healthy.cert_subject = "CN=healthy.example.com"
    healthy.cert_issuer = "CN=Real CA"
    healthy.cert_pubkey_size = 2048
    healthy.cert_pubkey_alg = "RSA"
    healthy.chain_verified = True

    with patch.object(_tls, "SSLYZE_AVAILABLE", True), \
         patch.object(_tls, "_scan_one_sslyze", return_value=healthy), \
         patch.object(_tls, "_scan_one_fallback") as m_fb:
        ep = _tls.scan_one("x", 443, 5, True, logger=None)

    m_fb.assert_not_called()
    assert ep is healthy
    assert ep.chain_verified is True
