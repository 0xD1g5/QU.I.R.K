"""Phase 59 LEAK-01: safe_str credential-scrubbing unit corpus.

Decision enforcement:
  - LEAK-01: safe_str returns class-name-only when message matches any
    _SENSITIVE_PATTERNS regex; returns f'{ClassName}: {msg}' otherwise.

Public surface under test:
  quirk.util.safe_exc.safe_str(exc) -> str
"""
from __future__ import annotations

import pytest

from quirk.util.safe_exc import safe_str


def test_safe_str_default() -> None:
    result = safe_str(ValueError("some message"))
    assert result.startswith("ValueError")


def test_safe_str_scrubs_vault_token() -> None:
    exc = Exception("request to https://vault:8200?token=s.AbCdEfGhIjKlMnOpQrSt1234")
    assert safe_str(exc) == "Exception"


def test_safe_str_scrubs_connection_password() -> None:
    exc = Exception("cannot connect: postgresql://user:secret123@db:5432/mydb")
    assert safe_str(exc) == "Exception"


def test_safe_str_scrubs_gcp_adc() -> None:
    exc = Exception("File not found: /home/user/.config/gcloud/application_default_credentials.json")
    assert safe_str(exc) == "Exception"


def test_safe_str_scrubs_authorization_header() -> None:
    exc = Exception("HTTP 401: Authorization: Bearer abcdef.xyz123.token456")
    assert safe_str(exc) == "Exception"


def test_safe_str_scrubs_long_base64() -> None:
    exc = Exception("aws_secret=AKIAIOSFODNN7EXAMPLE0123456789abcdefghijkl")
    assert safe_str(exc) == "Exception"


def test_safe_str_benign_passthrough() -> None:
    result = safe_str(ConnectionRefusedError("[Errno 111] Connection refused"))
    assert result.startswith("ConnectionRefusedError:")
    assert "Connection refused" in result


def test_safe_str_handles_str_raise() -> None:
    class _BoomStr(Exception):
        def __str__(self) -> str:  # noqa: D401
            raise RuntimeError("boom")

    assert safe_str(_BoomStr()) == "_BoomStr"


# ---------------------------------------------------------------------------
# Phase 93 D-08: new credential shape corpus (API-key header, query-param, Basic)
# ---------------------------------------------------------------------------

def test_safe_str_scrubs_x_api_key_header() -> None:
    exc = Exception("X-Api-Key: QUIRK_SENTINEL_CRED_d41d8cd9")
    assert safe_str(exc) == "Exception"


def test_safe_str_scrubs_x_auth_token_header() -> None:
    exc = Exception("X-Auth-Token: QUIRK_SENTINEL_CRED_d41d8cd9")
    assert safe_str(exc) == "Exception"


def test_safe_str_scrubs_query_param_api_key() -> None:
    exc = Exception("https://api.host/v1?api_key=QUIRK_SENTINEL_CRED_d41d8cd9")
    assert safe_str(exc) == "Exception"


def test_safe_str_scrubs_query_param_token() -> None:
    exc = Exception("https://api.host/v1?token=QUIRK_SENTINEL_CRED_d41d8cd9")
    assert safe_str(exc) == "Exception"


def test_safe_str_scrubs_http_basic_credential() -> None:
    exc = Exception("Authorization: Basic dXNlcjpwYXNzd29yZA==")
    assert safe_str(exc) == "Exception"


def test_safe_str_scrubs_x_api_key_case_insensitive() -> None:
    exc = Exception("x-api-key: QUIRK_SENTINEL_CRED_d41d8cd9")
    assert safe_str(exc) == "Exception"
