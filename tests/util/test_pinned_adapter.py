"""Unit tests for quirk.util.pinned_adapter.PinnedIPAdapter (Phase 123 SSRF-05 / D-03).

The adapter rewrites a request's URL netloc to a pre-resolved IP at send time so
the connect-time DNS lookup cannot rebind to an attacker-controlled address,
while leaving the Host header (set by requests at prepare time) untouched.
"""
from __future__ import annotations

from unittest.mock import patch

from quirk.util.pinned_adapter import PinnedIPAdapter


class _Req:
    """Minimal stand-in for a PreparedRequest — the adapter only touches .url / .headers."""

    def __init__(self, url: str, headers: dict | None = None):
        self.url = url
        self.headers = headers if headers is not None else {}


def _send(adapter: PinnedIPAdapter, req: _Req):
    """Call adapter.send with the super().send patched out; return (rewritten_url, ret)."""
    with patch("requests.adapters.HTTPAdapter.send", return_value="SENT") as sup:
        out = adapter.send(req)
    assert sup.called  # super().send must be invoked (request still dispatched)
    return req.url, out


def test_ipv4_netloc_rewritten_to_pinned_ip():
    """IPv4 pinned IP replaces the hostname in the netloc; path/query preserved."""
    url, out = _send(PinnedIPAdapter("93.184.216.34"), _Req("https://example.com/a/b?x=1"))
    assert "93.184.216.34" in url
    assert "example.com" not in url
    assert url.endswith("/a/b?x=1")
    assert out == "SENT"


def test_ipv4_port_preserved():
    """An explicit port survives the netloc rewrite."""
    url, _ = _send(PinnedIPAdapter("93.184.216.34"), _Req("https://example.com:8443/x"))
    assert "93.184.216.34:8443" in url


def test_ipv6_uses_bracket_notation():
    """IPv6 pinned IP is bracketed in the URL netloc."""
    url, _ = _send(PinnedIPAdapter("::1"), _Req("https://example.com:8443/x"))
    assert "[::1]:8443" in url


def test_non_ip_pinned_string_falls_back_without_raising():
    """A non-IP pinned string is used verbatim (no ValueError escapes)."""
    url, _ = _send(PinnedIPAdapter("not-an-ip"), _Req("https://example.com/x"))
    assert "not-an-ip" in url


def test_host_header_not_modified():
    """The adapter must not strip/alter the Host header (SNI/virtual-host preservation)."""
    req = _Req("https://example.com/x", headers={"Host": "example.com"})
    _send(PinnedIPAdapter("93.184.216.34"), req)
    assert req.headers["Host"] == "example.com"
