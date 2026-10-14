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
