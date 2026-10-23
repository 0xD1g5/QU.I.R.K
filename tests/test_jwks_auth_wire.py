"""Phase 230 DETECT-03 / DETECT-04 wire proof (D-09..D-13).

A real ``scan_jwt_endpoint`` fetch against a loopback JWKS server must put the
operator credential on the wire under all four schemes, while no captured log
record (httpx/httpcore/quirk at DEBUG) contains the secret.

D-10a honesty note: only ``api_key_query`` has a log site that can render the
secret (httpx logs the request URL at INFO). httpx/httpcore never log request
headers, so the three header-scheme log assertions cannot go red under a
no-op redaction filter; they are guards, not mutation-proven.

Markers are distinctive so a leak is greppable.
"""
from __future__ import annotations

import base64
import logging
from urllib.parse import parse_qs, urlparse

import pytest

from quirk.auth.credentials import CredentialContext
from quirk.scanner.jwt_scanner import scan_jwt_endpoint
from tests.jwks_wire_helpers import jwks_server  # noqa: F401

BEARER = "ZQXV230bearer"
APIKEY = "ZQXV230apikey"
QUERYKEY = "ZQXV230query"
BASIC = "user230:pw:with:colons"


def _ctx(scheme: str) -> CredentialContext:
    secret = {
        "bearer": BEARER,
        "api_key_header": APIKEY,
        "api_key_query": QUERYKEY,
        "basic": BASIC,
    }[scheme]
    ctx = CredentialContext(scheme=scheme)
    ctx._secret_buf = bytearray(secret.encode("utf-8"))
    if scheme == "api_key_query":
        ctx._query_param = "api_key"
    return ctx


def _scan(server, ctx):
    port = server.server_address[1]
    return scan_jwt_endpoint(
        f"http://127.0.0.1:{port}", timeout=3, cred_ctx=ctx, allow_internal=True
    )


def _wire_check(scheme: str, path: str, headers: dict) -> None:
    h = {k.lower(): v for k, v in headers.items()}
    if scheme == "bearer":
        assert h.get("authorization") == f"Bearer {BEARER}"
    elif scheme == "api_key_header":
        assert h.get("x-api-key") == APIKEY
    elif scheme == "api_key_query":
        assert parse_qs(urlparse(path).query).get("api_key") == [QUERYKEY]
    else:
        auth = h.get("authorization", "")
        assert auth.startswith("Basic ")
        assert base64.b64decode(auth.split(" ", 1)[1]) == BASIC.encode("utf-8")


@pytest.mark.parametrize("scheme", ["bearer", "api_key_header", "api_key_query", "basic"])
def test_credential_reaches_wire_and_not_logs(scheme, jwks_server, caplog):
    ctx = _ctx(scheme)
    with caplog.at_level(logging.DEBUG), caplog.at_level(
        logging.DEBUG, logger="httpx"
    ), caplog.at_level(logging.DEBUG, logger="httpcore"):
        eps = _scan(jwks_server, ctx)

    assert eps, "scan produced no endpoints"
    assert jwks_server.seen, "server saw no request"
    path, headers = jwks_server.seen[0]
    _wire_check(scheme, path, headers)

    needles = {
        "bearer": [BEARER],
        "api_key_header": [APIKEY],
        "api_key_query": [QUERYKEY],
        "basic": [BASIC, base64.b64encode(BASIC.encode()).decode()],
    }[scheme]
    messages = [r.getMessage() for r in caplog.records]
    for needle in needles:
        # Do not echo the needle's context in the failure message beyond count.
        leaked = [m for m in messages if needle in m]
        assert not leaked, f"{scheme}: secret leaked into {len(leaked)} log record(s)"


def test_basic_header_decodes_to_user_password(jwks_server):
    secret = "usér:pässwörd"
    ctx = CredentialContext(scheme="basic")
    ctx._secret_buf = bytearray(secret.encode("utf-8"))
    _scan(jwks_server, ctx)
    assert jwks_server.seen
    h = {k.lower(): v for k, v in jwks_server.seen[0][1].items()}
    assert base64.b64decode(h["authorization"].split(" ", 1)[1]).decode("utf-8") == secret


def test_basic_without_colon_raises_from_cli(monkeypatch):
    monkeypatch.setenv("QUIRK_T230_BASIC", "nocolonvalue230")
    with pytest.raises(ValueError) as ei:
        CredentialContext.from_cli(basic="QUIRK_T230_BASIC")
    assert "user:password" in str(ei.value)
    assert "nocolonvalue230" not in str(ei.value)


def test_basic_without_colon_raises_from_as_headers():
    ctx = CredentialContext(scheme="basic")
    ctx._secret_buf = bytearray(b"dXNlcjpwYXNz")
    with pytest.raises(ValueError) as ei:
        ctx.as_headers()
    assert "dXNlcjpwYXNz" not in str(ei.value)


def test_auth_basic_help_text():
    from tests.cli_helpers import run_cli

    proc = run_cli(["--help"])
    out = " ".join(proc.stdout.split())
    assert "user:password" in out
    assert "base64-encoded user:pass" not in out


# ---------------------------------------------------------------------------
# 230-REVIEW CR-01: a cross-origin jwks_uri named by the target's discovery
# document must never receive the operator credential.
# ---------------------------------------------------------------------------

_AUTH_HEADER_NAMES = ("authorization", "x-api-key", "x-auth-token")


@pytest.fixture
def two_origin_servers():
    from tests.jwks_wire_helpers import make_discovery_server, make_jwks_server

    server_b = make_jwks_server()
    jwks_uri = f"http://127.0.0.1:{server_b.server_address[1]}/keys"
    server_a = make_discovery_server(jwks_uri)
    try:
        yield server_a, server_b
    finally:
        for s in (server_a, server_b):
            s.shutdown()
            s.server_close()


@pytest.mark.parametrize("scheme", ["bearer", "api_key_header", "api_key_query", "basic"])
def test_cross_origin_jwks_uri_gets_no_credentials(scheme, two_origin_servers, caplog):
    server_a, server_b = two_origin_servers
    ctx = _ctx(scheme)
    with caplog.at_level(logging.DEBUG):
        eps = _scan(server_a, ctx)

    assert eps, "scan produced no endpoints (jwks_uri was not followed)"
    assert server_b.seen, "cross-origin jwks_uri was never fetched"

    # Server B (the target-chosen origin) gets nothing.
    for path, headers in server_b.seen:
        h = {k.lower() for k in headers}
        for name in _AUTH_HEADER_NAMES:
            assert name not in h, f"{scheme}: {name} sent to cross-origin jwks_uri"
        assert "api_key" not in parse_qs(urlparse(path).query)

    # Server A (the operator-supplied origin) still gets the credential on
    # every request, discovery included.
    assert server_a.seen
    for path, headers in server_a.seen:
        _wire_check(scheme, path, headers)

    # One WARNING names the origin mismatch, and no record carries the secret.
    secret = _ctx(scheme)._secret_buf.decode("utf-8")
    mismatch = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "different origin" in r.getMessage()
    ]
    assert len(mismatch) == 1
    assert all(secret not in r.getMessage() for r in caplog.records)


def test_same_origin_default_port_is_same_origin():
    from quirk.scanner.jwt_scanner import _norm_origin

    assert _norm_origin("https://h.example/x") == _norm_origin("https://H.example:443/y")
    assert _norm_origin("http://h.example/x") == _norm_origin("http://h.example:80/")
    assert _norm_origin("http://h.example/x") != _norm_origin("https://h.example/x")
    assert _norm_origin("https://h.example/x") != _norm_origin("https://h.example:8443/x")
