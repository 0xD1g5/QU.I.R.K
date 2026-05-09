"""Tests for Phase 57 / CR-01 / HARDEN-SCAN-01: JWT scanner TLS verification."""
from unittest.mock import MagicMock, patch
import pytest

from quirk.scanner.jwt_scanner import (
    scan_jwt_endpoint,
    scan_jwt_targets,
    ADVISORY_JWKS_VERIFY_DISABLED,
)


def _mock_jwks_response():
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"keys": [{"kty": "RSA", "n": "x", "e": "AQAB", "alg": "RS256"}]}
    m.text = '{"keys": [{"kty": "RSA"}]}'
    return m


def test_default_uses_verify_true():
    """Default scan_jwt_endpoint MUST call httpx.get with verify=True."""
    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = _mock_jwks_response()
        scan_jwt_endpoint("https://idp.example.com", timeout=5)
        # Inspect each httpx.get call — verify kwarg must be True (or absent => default httpx True)
        for call in mock_httpx.get.call_args_list:
            kwargs = call.kwargs
            assert kwargs.get("verify", True) is True, f"verify=False leaked: {call}"


def test_allow_insecure_jwks_uses_verify_false_and_emits_advisory():
    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = _mock_jwks_response()
        endpoints = scan_jwt_endpoint(
            "https://idp.example.com", timeout=5, allow_insecure_jwks=True
        )
        # At least one httpx.get call carries verify=False
        assert any(
            call.kwargs.get("verify") is False
            for call in mock_httpx.get.call_args_list
        ), "Expected at least one verify=False call when allow_insecure_jwks=True"
        # At least one advisory CryptoEndpoint with the right shape
        advisories = [e for e in endpoints if e.protocol == "ADVISORY"]
        assert len(advisories) >= 1
        adv = advisories[0]
        assert adv.service_detail == ADVISORY_JWKS_VERIFY_DISABLED
        assert adv.severity == "HIGH"
        assert adv.scan_error_category == "config"


def test_no_advisory_when_default():
    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = _mock_jwks_response()
        endpoints = scan_jwt_endpoint("https://idp.example.com", timeout=5)
        advisories = [e for e in endpoints if e.protocol == "ADVISORY"]
        assert advisories == []


def test_scan_jwt_targets_propagates_flag():
    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = _mock_jwks_response()
        scan_jwt_targets(["https://idp.example.com"], timeout=5, allow_insecure_jwks=True)
        assert any(
            call.kwargs.get("verify") is False
            for call in mock_httpx.get.call_args_list
        )
