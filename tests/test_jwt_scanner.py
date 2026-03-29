"""Tests for JWT/JWKS scanner (SCAN-03).

Tests mock httpx responses to avoid network calls.
Scanner module: quirk/scanner/jwt_scanner.py
"""
import json
import pytest
from unittest.mock import patch, MagicMock

# Scanner module import — will fail until Plan 02 creates it
from quirk.scanner.jwt_scanner import scan_jwt_targets, scan_jwt_endpoint

SAMPLE_JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "alg": "RS256",
            "kid": "key-1",
            "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
            "e": "AQAB",
            "use": "sig"
        },
        {
            "kty": "EC",
            "alg": "ES256",
            "kid": "key-2",
            "crv": "P-256",
            "x": "f83OJ3D2xF1Bg8vub9tLe1gHMzV76e8Tus9uPHvRVEU",
            "y": "x_FEzRu9m36HLN_tue659LNpXW6pCyStikYjKIWI5a0",
            "use": "sig"
        },
        {
            "kty": "RSA",
            "alg": "RS256",
            "kid": "key-3",
            "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
            "e": "AQAB",
            "use": "sig"
        }
    ]
}


def test_multi_key_jwks():
    """JWKS endpoint with 3 keys must produce 3 CryptoEndpoint rows (per D-07)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_JWKS

    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = mock_response
        endpoints = scan_jwt_endpoint("https://api.example.com", timeout=5)
        assert len(endpoints) == 3
        for ep in endpoints:
            assert ep.protocol == "JWT"
            assert ep.cert_pubkey_alg is not None
            assert ep.jwt_scan_json is not None


def test_jwt_rsa_key_size():
    """RSA key size must be computed from modulus n parameter."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"keys": [SAMPLE_JWKS["keys"][0]]}

    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = mock_response
        endpoints = scan_jwt_endpoint("https://api.example.com", timeout=5)
        assert len(endpoints) == 1
        ep = endpoints[0]
        assert ep.cert_pubkey_alg == "RS256"
        assert ep.cert_pubkey_size is not None
        assert ep.cert_pubkey_size >= 2048


def test_jwt_ec_key_size():
    """EC key size must be derived from crv parameter."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"keys": [SAMPLE_JWKS["keys"][1]]}

    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = mock_response
        endpoints = scan_jwt_endpoint("https://api.example.com", timeout=5)
        assert len(endpoints) == 1
        ep = endpoints[0]
        assert ep.cert_pubkey_alg == "ES256"
        assert ep.cert_pubkey_size == 256


def test_jwt_endpoint_not_found():
    """404 from JWKS endpoint must return empty list, not raise."""
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = mock_response
        endpoints = scan_jwt_endpoint("https://api.example.com", timeout=5)
        assert endpoints == []


def test_jwt_httpx_unavailable():
    """If httpx is not importable, scan_jwt_targets must return empty list."""
    with patch("quirk.scanner.jwt_scanner.HTTPX_AVAILABLE", False):
        endpoints = scan_jwt_targets([], timeout=5)
        assert endpoints == []
