"""Shared loopback JWKS server for Phase 230 DETECT-03/04 wire tests.

Do not import outside tests/.

The server records ``(path, headers)`` for every GET on ``server.seen`` and
answers each with a tiny JWKS document, so a test can assert exactly what a
real ``scan_jwt_endpoint`` fetch put on the wire (D-11).
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

_JWKS_BODY = json.dumps(
    {"keys": [{"kty": "RSA", "alg": "RS256", "kid": "t230", "n": "AQAB", "e": "AQAB"}]}
).encode("utf-8")


def make_jwks_server() -> HTTPServer:
    """Start a loopback JWKS server on an ephemeral port (daemon thread)."""

    class Handler(BaseHTTPRequestHandler):
        timeout = 5

        def do_GET(self) -> None:  # noqa: N802 (stdlib API)
            self.server.seen.append((self.path, dict(self.headers)))  # type: ignore[attr-defined]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(_JWKS_BODY)))
            self.end_headers()
            self.wfile.write(_JWKS_BODY)

        def log_message(self, *args, **kwargs) -> None:  # silence
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 5
    server.seen = []  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@pytest.fixture
def jwks_server():
    server = make_jwks_server()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
