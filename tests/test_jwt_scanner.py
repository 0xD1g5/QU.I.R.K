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


# ---------------------------------------------------------------------------
# Phase 93 / AUTH-01: CredentialContext wiring tests
# ---------------------------------------------------------------------------

def test_jwt_query_param_cred_ctx_appends_key_to_url() -> None:
    """AUTH-01 / D-03: a query-param CredentialContext causes the JWKS fetch URL
    to carry the API key as a query parameter (observed via mocked httpx.Client).

    The test builds a real CredentialContext in api_key_query scheme (seeded with
    a known secret without hitting getpass), mocks httpx.Client to capture the
    request URL, and asserts the key appears in the URL query string.
    """
    from quirk.auth.credentials import CredentialContext

    # Build a real CredentialContext seeded via environment variable (no getpass)
    import os
    os.environ["_TEST_QUIRK_JWT_KEY"] = "test-api-key-value"
    try:
        ctx = CredentialContext.from_cli(api_key_query="_TEST_QUIRK_JWT_KEY")
    finally:
        os.environ.pop("_TEST_QUIRK_JWT_KEY", None)

    assert ctx is not None
    assert ctx.scheme == "api_key_query"

    # Capture URLs that httpx.Client makes via a mock transport
    captured_urls = []

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_JWKS

    class _CapturingClientCM:
        """Context-manager stub for httpx.Client that captures request.url values."""
        def __init__(self, **kwargs):
            self._kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def get(self, url, **kwargs):
            captured_urls.append(url)
            return mock_resp

    with patch("quirk.scanner.jwt_scanner.httpx.Client", _CapturingClientCM):
        endpoints = scan_jwt_endpoint("https://api.example.com", timeout=5, cred_ctx=ctx)

    ctx.close()

    # At least one fetch URL must contain the api_key query parameter
    assert len(captured_urls) > 0, "httpx.Client.get was never called"
    assert any("api_key=test-api-key-value" in url for url in captured_urls), (
        f"api_key query param not found in fetched URLs: {captured_urls}"
    )
    # The key must NOT appear in headers (D-03: query-param scheme never uses headers)
    assert ctx.as_headers() == {}, "api_key_query scheme must return empty headers"


def test_jwt_bearer_cred_ctx_uses_header() -> None:
    """AUTH-01: a bearer CredentialContext causes Authorization: Bearer header to be set."""
    from quirk.auth.credentials import CredentialContext
    import os

    os.environ["_TEST_QUIRK_BEARER"] = "test-bearer-token"
    try:
        ctx = CredentialContext.from_cli(bearer="_TEST_QUIRK_BEARER")
    finally:
        os.environ.pop("_TEST_QUIRK_BEARER", None)

    assert ctx is not None
    hdrs = ctx.as_headers()
    assert "Authorization" in hdrs
    assert hdrs["Authorization"].startswith("Bearer ")
    ctx.close()


def test_jwt_no_cred_ctx_unchanged_behavior() -> None:
    """AUTH-01 / D-12: when cred_ctx=None, scan_jwt_targets behaves identically to baseline."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_JWKS

    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = mock_response
        endpoints = scan_jwt_targets(
            ["https://api.example.com"],
            timeout=5,
            cred_ctx=None,
        )

    assert len(endpoints) == 3
    for ep in endpoints:
        assert ep.protocol == "JWT"
