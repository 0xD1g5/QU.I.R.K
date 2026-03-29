"""
Tests for sslyze integration in tls_scanner.py.

Tests cover:
- sslyze primary path (mocked): CryptoEndpoint fields populated from sslyze data
- sslyze not installed (ImportError): fallback to existing scan_one runs
- sslyze scan error (ERROR_NO_CONNECTIVITY): fallback runs
- Certificate field mapping from sslyze data
- tls_capabilities_json structure
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from types import ModuleType
from typing import Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from qcscan.models import CryptoEndpoint


# ---------------------------------------------------------------------------
# Helpers to build mock sslyze result objects
# ---------------------------------------------------------------------------

def _make_mock_cert(subject="CN=example.com", issuer="CN=CA", sig_alg="sha256", pubkey_alg="RSA", pubkey_size=2048):
    """Build a mock cryptography x509.Certificate."""
    cert = MagicMock()

    # subject / issuer
    subject_mock = MagicMock()
    subject_mock.rfc4514_string.return_value = subject
    cert.subject = subject_mock

    issuer_mock = MagicMock()
    issuer_mock.rfc4514_string.return_value = issuer
    cert.issuer = issuer_mock

    # signature algorithm
    sig_hash = MagicMock()
    sig_hash.name = sig_alg
    cert.signature_hash_algorithm = sig_hash

    # public key — RSA by default
    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa_module
    pubkey = MagicMock(spec=_rsa_module.RSAPublicKey)
    pubkey.key_size = pubkey_size
    cert.public_key.return_value = pubkey

    # validity dates (use newer API if available)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    expiry = datetime(2027, 1, 1, tzinfo=timezone.utc)
    cert.not_valid_before_utc = now
    cert.not_valid_after_utc = expiry

    # SANs extension — empty for simplicity
    from cryptography import x509 as crypto_x509
    ext = MagicMock()
    ext.value.get_values_for_type.return_value = []
    cert.extensions.get_extension_for_class.return_value = ext

    return cert


def _make_mock_cipher_suite(name: str):
    cs = MagicMock()
    cs.cipher_suite.name = name
    return cs


def _make_sslyze_mock_modules():
    """
    Build a fake sslyze module tree so we can patch sys.modules before import.
    Returns (sslyze_mod, ScanCommandAttemptStatusEnum_mock, ServerScanStatusEnum_mock).
    """
    import enum

    class _ScanCommandAttemptStatusEnum(enum.Enum):
        COMPLETED = "COMPLETED"
        ERROR = "ERROR"
        NOT_SCHEDULED = "NOT_SCHEDULED"

    class _ServerScanStatusEnum(enum.Enum):
        COMPLETED = "COMPLETED"
        ERROR_NO_CONNECTIVITY = "ERROR_NO_CONNECTIVITY"

    # Build mock cipher suite attempts
    def _make_cipher_attempt(accepted_names, status=_ScanCommandAttemptStatusEnum.COMPLETED):
        attempt = MagicMock()
        attempt.status = status
        if status == _ScanCommandAttemptStatusEnum.COMPLETED:
            attempt.result.accepted_cipher_suites = [_make_mock_cipher_suite(n) for n in accepted_names]
            attempt.result.tls_version_used = MagicMock()  # not used by scanner directly
        return attempt

    # Fake sslyze module
    sslyze_mod = ModuleType("sslyze")
    sslyze_mod.__version__ = "6.3.1"
    sslyze_mod.ScanCommandAttemptStatusEnum = _ScanCommandAttemptStatusEnum
    sslyze_mod.ServerScanStatusEnum = _ServerScanStatusEnum

    # ScanCommand enum
    class _ScanCommand(enum.Enum):
        CERTIFICATE_INFO = "CERTIFICATE_INFO"
        SSL_2_0_CIPHER_SUITES = "SSL_2_0_CIPHER_SUITES"
        SSL_3_0_CIPHER_SUITES = "SSL_3_0_CIPHER_SUITES"
        TLS_1_0_CIPHER_SUITES = "TLS_1_0_CIPHER_SUITES"
        TLS_1_1_CIPHER_SUITES = "TLS_1_1_CIPHER_SUITES"
        TLS_1_2_CIPHER_SUITES = "TLS_1_2_CIPHER_SUITES"
        TLS_1_3_CIPHER_SUITES = "TLS_1_3_CIPHER_SUITES"
        ELLIPTIC_CURVES = "ELLIPTIC_CURVES"

    sslyze_mod.ScanCommand = _ScanCommand

    # ServerNetworkLocation / ServerNetworkConfiguration / ServerScanRequest — just pass-through mocks
    sslyze_mod.ServerNetworkLocation = MagicMock()
    sslyze_mod.ServerNetworkConfiguration = MagicMock()
    sslyze_mod.ServerScanRequest = MagicMock()

    # Scanner class
    sslyze_mod.Scanner = MagicMock

    return sslyze_mod, _ScanCommandAttemptStatusEnum, _ServerScanStatusEnum


# ---------------------------------------------------------------------------
# Test 1: sslyze available — happy path
# ---------------------------------------------------------------------------

class TestSslyzeAvailableSuccess:
    """When sslyze is installed and returns COMPLETED, CryptoEndpoint fields are populated."""

    def _make_completed_server_result(self, sslyze_mod, ScanCommandAttemptStatusEnum, ServerScanStatusEnum):
        """Build a fully-completed sslyze ServerScanResult mock."""
        cert = _make_mock_cert()

        # Certificate info attempt
        cert_attempt = MagicMock()
        cert_attempt.status = ScanCommandAttemptStatusEnum.COMPLETED
        deployment = MagicMock()
        deployment.received_certificate_chain = [cert]
        deployment.verified_certificate_chain = [cert]  # non-None means trusted
        cert_attempt.result.certificate_deployments = [deployment]

        # Cipher suite attempts — TLS 1.2 and 1.3 have suites; others empty
        def _make_cipher_attempt(names, status=ScanCommandAttemptStatusEnum.COMPLETED):
            a = MagicMock()
            a.status = status
            if status == ScanCommandAttemptStatusEnum.COMPLETED:
                a.result.accepted_cipher_suites = [_make_mock_cipher_suite(n) for n in names]
            return a

        scan_result = MagicMock()
        scan_result.certificate_info = cert_attempt
        scan_result.ssl_2_0_cipher_suites = _make_cipher_attempt([])
        scan_result.ssl_3_0_cipher_suites = _make_cipher_attempt([])
        scan_result.tls_1_0_cipher_suites = _make_cipher_attempt([])
        scan_result.tls_1_1_cipher_suites = _make_cipher_attempt([])
        scan_result.tls_1_2_cipher_suites = _make_cipher_attempt(
            ["ECDHE-RSA-AES256-GCM-SHA384", "AES256-SHA"]
        )
        scan_result.tls_1_3_cipher_suites = _make_cipher_attempt(
            ["TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256"]
        )

        # Elliptic curves
        ec_attempt = MagicMock()
        ec_attempt.status = ScanCommandAttemptStatusEnum.COMPLETED
        curve1, curve2 = MagicMock(), MagicMock()
        curve1.name, curve2.name = "x25519", "secp256r1"
        ec_attempt.result.supported_curves = [curve1, curve2]
        scan_result.elliptic_curves = ec_attempt

        server_result = MagicMock()
        server_result.scan_status = ServerScanStatusEnum.COMPLETED
        server_result.scan_result = scan_result

        return server_result

    def test_sslyze_available_success(self):
        """sslyze returns COMPLETED result → CryptoEndpoint populated, no fallback."""
        sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus = _make_sslyze_mock_modules()
        server_result = self._make_completed_server_result(sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus)

        scanner_instance = MagicMock()
        scanner_instance.get_results.return_value = [server_result]
        sslyze_mod.Scanner.return_value = scanner_instance

        import importlib
        # Inject mock sslyze before importing tls_scanner
        with patch.dict(sys.modules, {"sslyze": sslyze_mod}):
            import qcscan.scanner.tls_scanner as tls_mod
            importlib.reload(tls_mod)
            # Force SSLYZE_AVAILABLE=True
            tls_mod.SSLYZE_AVAILABLE = True

            ep = tls_mod._scan_one_sslyze("example.com", 443, 10, True, None)

        assert ep is not None, "_scan_one_sslyze should return CryptoEndpoint on success"
        assert ep.tls_version is not None, "tls_version should be populated"
        assert ep.tls_enum_mode == "sslyze"
        assert ep.tls_capabilities_json is not None, "tls_capabilities_json must be populated"

        caps = json.loads(ep.tls_capabilities_json)
        assert caps["source"] == "sslyze"
        assert "accepted_by_version" in caps

    def test_tls_version_set_to_highest_available(self):
        """Highest available TLS version is set as ep.tls_version."""
        sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus = _make_sslyze_mock_modules()
        server_result = self._make_completed_server_result(sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus)
        scanner_instance = MagicMock()
        scanner_instance.get_results.return_value = [server_result]
        sslyze_mod.Scanner.return_value = scanner_instance

        import importlib
        with patch.dict(sys.modules, {"sslyze": sslyze_mod}):
            import qcscan.scanner.tls_scanner as tls_mod
            importlib.reload(tls_mod)
            tls_mod.SSLYZE_AVAILABLE = True
            ep = tls_mod._scan_one_sslyze("example.com", 443, 10, True, None)

        # TLS 1.3 has suites, so tls_version should be TLSv1.3
        assert ep.tls_version == "TLSv1.3"


# ---------------------------------------------------------------------------
# Test 2: sslyze not installed (ImportError)
# ---------------------------------------------------------------------------

class TestSslyzeNotInstalled:
    """When sslyze is not installed, scan_one falls back to _scan_one_fallback."""

    def test_sslyze_not_installed_uses_fallback(self):
        """SSLYZE_AVAILABLE=False → scan_one calls _scan_one_fallback, not sslyze."""
        import importlib
        # Remove sslyze from sys.modules to simulate it not being installed
        with patch.dict(sys.modules, {"sslyze": None}):
            import qcscan.scanner.tls_scanner as tls_mod
            importlib.reload(tls_mod)

        # After reload with sslyze=None, SSLYZE_AVAILABLE should be False
        assert tls_mod.SSLYZE_AVAILABLE is False, "SSLYZE_AVAILABLE must be False when sslyze not installed"

    def test_scan_one_calls_fallback_when_sslyze_unavailable(self):
        """scan_one routes to _scan_one_fallback when SSLYZE_AVAILABLE=False."""
        import importlib
        import qcscan.scanner.tls_scanner as tls_mod
        importlib.reload(tls_mod)
        tls_mod.SSLYZE_AVAILABLE = False

        fallback_ep = CryptoEndpoint(host="example.com", port=443, protocol="TLS")
        with patch.object(tls_mod, "_scan_one_fallback", return_value=fallback_ep) as mock_fallback:
            result = tls_mod.scan_one("example.com", 443, 10, True, None)

        mock_fallback.assert_called_once()
        assert result is fallback_ep


# ---------------------------------------------------------------------------
# Test 3: sslyze scan error triggers fallback
# ---------------------------------------------------------------------------

class TestSslyzeErrorFallback:
    """When sslyze returns ERROR_NO_CONNECTIVITY, scan_one falls back."""

    def test_sslyze_scan_error_falls_back(self):
        """scan status ERROR_NO_CONNECTIVITY → _scan_one_sslyze returns None → fallback runs."""
        sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus = _make_sslyze_mock_modules()

        # Server result with error status
        error_result = MagicMock()
        error_result.scan_status = ServerScanStatus.ERROR_NO_CONNECTIVITY

        scanner_instance = MagicMock()
        scanner_instance.get_results.return_value = [error_result]
        sslyze_mod.Scanner.return_value = scanner_instance

        import importlib
        with patch.dict(sys.modules, {"sslyze": sslyze_mod}):
            import qcscan.scanner.tls_scanner as tls_mod
            importlib.reload(tls_mod)
            tls_mod.SSLYZE_AVAILABLE = True
            ep = tls_mod._scan_one_sslyze("example.com", 443, 10, True, None)

        assert ep is None, "_scan_one_sslyze must return None when sslyze reports connectivity error"

    def test_scan_one_calls_fallback_after_sslyze_error(self):
        """scan_one uses fallback when _scan_one_sslyze returns None."""
        import importlib
        import qcscan.scanner.tls_scanner as tls_mod
        importlib.reload(tls_mod)
        tls_mod.SSLYZE_AVAILABLE = True

        fallback_ep = CryptoEndpoint(host="example.com", port=443, protocol="TLS")
        with patch.object(tls_mod, "_scan_one_sslyze", return_value=None):
            with patch.object(tls_mod, "_scan_one_fallback", return_value=fallback_ep) as mock_fallback:
                result = tls_mod.scan_one("example.com", 443, 10, True, None)

        mock_fallback.assert_called_once()
        assert result is fallback_ep


# ---------------------------------------------------------------------------
# Test 4: Certificate field mapping
# ---------------------------------------------------------------------------

class TestSslyzeMapsCertFields:
    """Verify cert_* fields are populated from sslyze certificate info."""

    def _build_result(self, sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus):
        cert = _make_mock_cert(
            subject="CN=test.example.com",
            issuer="CN=Test CA",
            sig_alg="sha256",
            pubkey_alg="RSA",
            pubkey_size=4096,
        )

        cert_attempt = MagicMock()
        cert_attempt.status = ScanCmdAttemptStatus.COMPLETED
        deployment = MagicMock()
        deployment.received_certificate_chain = [cert]
        deployment.verified_certificate_chain = None  # untrusted / self-signed
        cert_attempt.result.certificate_deployments = [deployment]

        def _empty_cipher_attempt():
            a = MagicMock()
            a.status = ScanCmdAttemptStatus.COMPLETED
            a.result.accepted_cipher_suites = []
            return a

        scan_result = MagicMock()
        scan_result.certificate_info = cert_attempt
        scan_result.ssl_2_0_cipher_suites = _empty_cipher_attempt()
        scan_result.ssl_3_0_cipher_suites = _empty_cipher_attempt()
        scan_result.tls_1_0_cipher_suites = _empty_cipher_attempt()
        scan_result.tls_1_1_cipher_suites = _empty_cipher_attempt()
        scan_result.tls_1_2_cipher_suites = _empty_cipher_attempt()
        scan_result.tls_1_3_cipher_suites = _empty_cipher_attempt()

        ec_attempt = MagicMock()
        ec_attempt.status = ScanCmdAttemptStatus.COMPLETED
        ec_attempt.result.supported_curves = []
        scan_result.elliptic_curves = ec_attempt

        server_result = MagicMock()
        server_result.scan_status = ServerScanStatus.COMPLETED
        server_result.scan_result = scan_result
        return server_result

    def test_sslyze_maps_cert_fields(self):
        sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus = _make_sslyze_mock_modules()
        server_result = self._build_result(sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus)

        scanner_instance = MagicMock()
        scanner_instance.get_results.return_value = [server_result]
        sslyze_mod.Scanner.return_value = scanner_instance

        import importlib
        with patch.dict(sys.modules, {"sslyze": sslyze_mod}):
            import qcscan.scanner.tls_scanner as tls_mod
            importlib.reload(tls_mod)
            tls_mod.SSLYZE_AVAILABLE = True
            ep = tls_mod._scan_one_sslyze("test.example.com", 443, 10, True, None)

        assert ep is not None
        assert ep.cert_subject == "CN=test.example.com"
        assert ep.cert_issuer == "CN=Test CA"
        assert ep.cert_sig_alg == "sha256"
        assert ep.cert_pubkey_alg == "RSA"
        assert ep.cert_pubkey_size == 4096
        assert ep.cert_not_before is not None
        assert ep.cert_not_after is not None

    def test_chain_depth_in_capabilities_json(self):
        sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus = _make_sslyze_mock_modules()
        server_result = self._build_result(sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus)

        scanner_instance = MagicMock()
        scanner_instance.get_results.return_value = [server_result]
        sslyze_mod.Scanner.return_value = scanner_instance

        import importlib
        with patch.dict(sys.modules, {"sslyze": sslyze_mod}):
            import qcscan.scanner.tls_scanner as tls_mod
            importlib.reload(tls_mod)
            tls_mod.SSLYZE_AVAILABLE = True
            ep = tls_mod._scan_one_sslyze("test.example.com", 443, 10, True, None)

        caps = json.loads(ep.tls_capabilities_json)
        assert caps["chain_depth"] == 1  # one cert in received chain
        assert caps["chain_verified"] is False  # verified_certificate_chain is None


# ---------------------------------------------------------------------------
# Test 5: tls_capabilities_json structure
# ---------------------------------------------------------------------------

class TestTlsCapabilitiesJsonStructure:
    """Verify tls_capabilities_json contains required keys."""

    def test_tls_capabilities_json_structure(self):
        sslyze_mod, ScanCmdAttemptStatus, ServerScanStatus = _make_sslyze_mock_modules()

        cert = _make_mock_cert()
        cert_attempt = MagicMock()
        cert_attempt.status = ScanCmdAttemptStatus.COMPLETED
        deployment = MagicMock()
        deployment.received_certificate_chain = [cert]
        deployment.verified_certificate_chain = [cert]
        cert_attempt.result.certificate_deployments = [deployment]

        def _make_ca(names):
            a = MagicMock()
            a.status = ScanCmdAttemptStatus.COMPLETED
            a.result.accepted_cipher_suites = [_make_mock_cipher_suite(n) for n in names]
            return a

        scan_result = MagicMock()
        scan_result.certificate_info = cert_attempt
        scan_result.ssl_2_0_cipher_suites = _make_ca([])
        scan_result.ssl_3_0_cipher_suites = _make_ca([])
        scan_result.tls_1_0_cipher_suites = _make_ca([])
        scan_result.tls_1_1_cipher_suites = _make_ca([])
        scan_result.tls_1_2_cipher_suites = _make_ca(["ECDHE-RSA-AES128-GCM-SHA256"])
        scan_result.tls_1_3_cipher_suites = _make_ca(["TLS_AES_128_GCM_SHA256"])

        curve = MagicMock()
        curve.name = "x25519"
        ec_attempt = MagicMock()
        ec_attempt.status = ScanCmdAttemptStatus.COMPLETED
        ec_attempt.result.supported_curves = [curve]
        scan_result.elliptic_curves = ec_attempt

        server_result = MagicMock()
        server_result.scan_status = ServerScanStatus.COMPLETED
        server_result.scan_result = scan_result

        scanner_instance = MagicMock()
        scanner_instance.get_results.return_value = [server_result]
        sslyze_mod.Scanner.return_value = scanner_instance

        import importlib
        with patch.dict(sys.modules, {"sslyze": sslyze_mod}):
            import qcscan.scanner.tls_scanner as tls_mod
            importlib.reload(tls_mod)
            tls_mod.SSLYZE_AVAILABLE = True
            ep = tls_mod._scan_one_sslyze("example.com", 443, 10, True, None)

        assert ep is not None
        assert ep.tls_capabilities_json is not None

        caps = json.loads(ep.tls_capabilities_json)
        assert "accepted_by_version" in caps, "accepted_by_version key required"
        assert "chain_depth" in caps, "chain_depth key required"
        assert "elliptic_curves" in caps, "elliptic_curves key required"
        assert caps["source"] == "sslyze"
        assert caps["sslyze_version"] == "6.3.1"
        assert "x25519" in caps["elliptic_curves"]
        assert "TLSv1.2" in caps["accepted_by_version"]
        assert "ECDHE-RSA-AES128-GCM-SHA256" in caps["accepted_by_version"]["TLSv1.2"]


# ---------------------------------------------------------------------------
# Test 6: _scan_one_fallback exists (old scan_one renamed)
# ---------------------------------------------------------------------------

class TestFallbackFunctionExists:
    """Verify _scan_one_fallback is defined and callable."""

    def test_fallback_function_exists(self):
        import importlib
        import qcscan.scanner.tls_scanner as tls_mod
        importlib.reload(tls_mod)
        assert hasattr(tls_mod, "_scan_one_fallback"), "_scan_one_fallback must be defined"
        assert callable(tls_mod._scan_one_fallback)

    def test_sslyze_function_exists(self):
        import importlib
        import qcscan.scanner.tls_scanner as tls_mod
        importlib.reload(tls_mod)
        assert hasattr(tls_mod, "_scan_one_sslyze"), "_scan_one_sslyze must be defined"
        assert callable(tls_mod._scan_one_sslyze)

    def test_sslyze_available_flag_exists(self):
        import importlib
        import qcscan.scanner.tls_scanner as tls_mod
        importlib.reload(tls_mod)
        assert hasattr(tls_mod, "SSLYZE_AVAILABLE"), "SSLYZE_AVAILABLE must be defined"
        assert isinstance(tls_mod.SSLYZE_AVAILABLE, bool)
