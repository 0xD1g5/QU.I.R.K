"""Tests for quirk/util/outbound_fetch.py (validated outbound fetches, one hop at a time)."""
from __future__ import annotations

import ast
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from quirk.util import outbound_fetch
from quirk.util.outbound_fetch import (
    MAX_REDIRECT_HOPS,
    OutboundFetchRejected,
    fetch_validated,
)
from quirk.util.url_allowlist import ValidationResult


def _resp(status, location=None):
    r = MagicMock()
    r.status_code = status
    r.headers = {"location": location} if location else {}
    return r


def _ok(url, allow_internal=False):
    return ValidationResult(ok=True, reason="", redacted_preview=url, resolved_ip="93.184.216.34")


@pytest.fixture
def public():
    with patch("quirk.util.outbound_fetch.validate_external_url", side_effect=_ok) as m:
        yield m


def test_hop0_rejected_without_fetch():
    fetch = MagicMock()
    with pytest.raises(OutboundFetchRejected) as ei:
        fetch_validated("http://169.254.169.254/x", fetch=fetch, allow_internal=True)
    assert ei.value.hop == 0
    assert ei.value.reason == "metadata_service_ip"
    fetch.assert_not_called()


def test_metadata_hop_refused_at_hop1():
    calls = []

    def fetch(u, h):
        calls.append(u)
        return _resp(302, "http://169.254.169.254/latest/")

    with patch("quirk.util.outbound_fetch.validate_external_url",
               wraps=lambda u, allow_internal=False: (
                   __import__("quirk.util.url_allowlist", fromlist=["x"]).validate_external_url(
                       u, allow_internal=allow_internal))):
        with pytest.raises(OutboundFetchRejected) as ei:
            fetch_validated("http://127.0.0.1/a", fetch=fetch, allow_internal=True)
    assert ei.value.hop == 1
    assert ei.value.reason == "metadata_service_ip"
    assert calls == ["http://127.0.0.1/a"]


def test_relative_location_and_303(public):
    seen = []

    def fetch(u, h):
        seen.append(u)
        return _resp(303, "/real.yaml") if len(seen) == 1 else _resp(200)

    r = fetch_validated("http://example.com/a/spec", fetch=fetch, allow_internal=False)
    assert r.status_code == 200
    assert seen == ["http://example.com/a/spec", "http://example.com/real.yaml"]


def test_header_stripping_on_origin_change(public):
    seen = []
    hdrs = {"Authorization": "x", "x-api-key": "y", "X-Auth-Token": "z", "Cookie": "c",
            "Proxy-Authorization": "p", "Accept": "a"}

    def fetch(u, h):
        seen.append(dict(h))
        return _resp(302, "http://other.example.org/x") if len(seen) == 1 else _resp(200)

    fetch_validated("http://example.com/a", fetch=fetch, allow_internal=False, headers=hdrs)
    assert len(seen[0]) == 6
    assert seen[1] == {"Accept": "a"}


def test_header_kept_on_same_origin(public):
    seen = []

    def fetch(u, h):
        seen.append(dict(h))
        return _resp(302, "/b") if len(seen) == 1 else _resp(200)

    fetch_validated("http://example.com/a", fetch=fetch, allow_internal=False,
                    headers={"Authorization": "x"})
    assert seen[1] == {"Authorization": "x"}


def test_too_many_redirects(public):
    fetch = MagicMock(side_effect=lambda u, h: _resp(302, "/next"))
    with pytest.raises(OutboundFetchRejected) as ei:
        fetch_validated("http://example.com/a", fetch=fetch, allow_internal=False,
                        max_hops=5)
    assert ei.value.reason == "too_many_redirects"
    assert MAX_REDIRECT_HOPS == 5


def test_extra_check_exception_propagates(public):
    class Boom(Exception):
        pass

    def check(u):
        if u.endswith("/b"):
            raise Boom()

    fetch = MagicMock(side_effect=lambda u, h: _resp(302, "/b"))
    with pytest.raises(Boom):
        fetch_validated("http://example.com/a", fetch=fetch, allow_internal=False,
                        extra_check=check)
    assert fetch.call_count == 1


def test_mock_response_without_status_is_final(public):
    m = MagicMock()
    assert fetch_validated("http://example.com/a", fetch=lambda u, h: m,
                           allow_internal=False) is m


def test_redirect_without_location_is_final(public):
    r = _resp(302)
    assert fetch_validated("http://example.com/a", fetch=lambda u, h: r,
                           allow_internal=False) is r


def test_helper_imports_no_http_client():
    src = pathlib.Path(outbound_fetch.__file__).read_text()
    tree = ast.parse(src)
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            names.add((n.module or "").split(".")[0])
    assert not names & {"httpx", "requests"}


# ---------------------------------------------------------------------------
# Loopback two-server integration tests
# ---------------------------------------------------------------------------
import logging
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

from quirk.scanner.openapi_scanner import SpecParsingError, _fetch_spec_bytes_from_url
from quirk.scanner.saml_scanner import _fetch_metadata
from quirk.scanner.jwt_scanner import _fetch_jwks
from quirk.util import url_allowlist


def _make_server(routes):
    hits = []

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            status, loc, body = routes.get(self.path.split("?")[0], (404, None, b"nope"))
            self.send_response(status)
            if loc:
                self.send_header("Location", loc)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    srv.hits = hits
    return srv


@pytest.fixture
def servers():
    made = []

    def make(routes):
        s = _make_server(routes)
        made.append(s)
        return s

    yield make
    for s in made:
        s.shutdown()
        s.server_close()


def test_openapi_hop_out_of_scope_rejected(servers):
    b = servers({"/real.yaml": (200, None, b"openapi: 3.0.0\n")})
    a = servers({"/spec.yaml": (302, f"http://localhost:{b.server_port}/real.yaml", b"")})
    with pytest.raises(SpecParsingError, match="scope"):
        _fetch_spec_bytes_from_url(
            f"http://127.0.0.1:{a.server_port}/spec.yaml", ["127.0.0.1"], allow_internal=True)
    assert b.hits == []


def test_openapi_same_host_redirect_followed(servers):
    routes_a = {}
    a2 = servers(routes_a)
    routes_a["/spec.yaml"] = (302, f"http://127.0.0.1:{a2.server_port}/real.yaml", b"")
    routes_a["/real.yaml"] = (200, None, b"openapi: 3.0.0\n")
    out = _fetch_spec_bytes_from_url(
        f"http://127.0.0.1:{a2.server_port}/spec.yaml", ["127.0.0.1"], allow_internal=True)
    assert out == b"openapi: 3.0.0\n"


class _Spy:
    def __init__(self):
        self.urls = []

    def __call__(self, url, allow_internal=False):
        self.urls.append(url)
        return url_allowlist.validate_external_url(url, allow_internal=allow_internal)


def test_openapi_metadata_hop_refused(servers):
    a = servers({"/s.yaml": (302, "http://169.254.169.254/x", b"")})
    spy = _Spy()
    with patch("quirk.util.outbound_fetch.validate_external_url", spy):
        with pytest.raises(SpecParsingError):
            _fetch_spec_bytes_from_url(
                f"http://127.0.0.1:{a.server_port}/s.yaml", ["127.0.0.1"], allow_internal=True)
    assert len(a.hits) == 1
    assert spy.urls[-1] == "http://169.254.169.254/x"


def test_saml_metadata_hop_refused(servers):
    a = servers({"/m": (302, "http://169.254.169.254/x", b"")})
    spy = _Spy()
    with patch("quirk.util.outbound_fetch.validate_external_url", spy):
        assert _fetch_metadata(f"http://127.0.0.1:{a.server_port}/m", 5, allow_internal=True) is None
    assert len(a.hits) == 1
    assert spy.urls[-1] == "http://169.254.169.254/x"


def test_jwks_metadata_hop_refused(servers):
    a = servers({"/.well-known/jwks.json": (302, "http://169.254.169.254/x", b"")})
    spy = _Spy()
    with patch("quirk.util.outbound_fetch.validate_external_url", spy):
        keys, path, _ = _fetch_jwks(f"http://127.0.0.1:{a.server_port}", 3, allow_internal=True)
    assert keys is None
    assert any(u == "http://169.254.169.254/x" for u in spy.urls)


def test_openapi_fetch_error_message_has_no_query_value(servers):
    a = servers({})
    sentinel = "SENTINEL-" + uuid.uuid4().hex
    with pytest.raises(SpecParsingError) as ei:
        _fetch_spec_bytes_from_url(
            f"http://127.0.0.1:{a.server_port}/missing.yaml?access_token={sentinel}",
            ["127.0.0.1"], allow_internal=True)
    msg = str(ei.value)
    assert "HTTPStatusError" in msg and "404" in msg
    assert sentinel not in msg


def test_saml_failure_log_uses_redacted_preview(servers, caplog):
    a = servers({})
    sentinel = "SENTINEL-" + uuid.uuid4().hex
    with caplog.at_level(logging.WARNING):
        assert _fetch_metadata(
            f"http://127.0.0.1:{a.server_port}/m?k={sentinel}", 3, allow_internal=True) is None
    assert "404" in caplog.text
    assert sentinel not in caplog.text
    # connection-level failure: closed port
    s2 = _make_server({})
    port = s2.server_port
    s2.shutdown()
    s2.server_close()
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert _fetch_metadata(
            f"http://127.0.0.1:{port}/m?k={sentinel}", 2, allow_internal=True) is None
    assert sentinel not in caplog.text
    assert "ConnectError" in caplog.text
