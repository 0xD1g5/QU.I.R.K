"""Pinned-IP HTTP adapter for QUIRK — Phase 123 SSRF-05 / D-03.

Provides PinnedIPAdapter, a requests.HTTPAdapter subclass that connects to a
pre-resolved IP address while preserving the original Host header. This closes
the TOCTOU / DNS-rebinding window on the requests/httpx path: the caller
resolves once via validate_external_url (which returns resolved_ip), then mounts
this adapter on the session so the connect-time DNS lookup never re-resolves the
hostname to a different (attacker-controlled) address.

Usage::

    result = validate_external_url(url, allow_internal=allow_internal)
    if not result.ok:
        raise ValueError(result.reason)
    session = requests.Session()
    if result.resolved_ip:
        session.mount(url, PinnedIPAdapter(result.resolved_ip))
    resp = session.get(url, timeout=10)

Note on SNI: the netloc is rewritten to the pinned IP at send time, so the
TLS SNI urllib3 derives from the connection host follows the pinned IP. The
``Host`` header (set by requests at prepare time from the original URL) is
preserved, so HTTP virtual-hosting still works. Full SNI preservation would
require overriding urllib3 connection creation and is out of scope for Phase
123 (the rest_fuzzer probe path uses CERT_NONE; the requests path relies on the
Host header). The primary goal here is pinning the connect address.

Public surface:
    PinnedIPAdapter(pinned_ip: str)
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urlparse, urlunparse

from requests.adapters import HTTPAdapter


class PinnedIPAdapter(HTTPAdapter):
    """HTTPAdapter that connects to *pinned_ip*, preserving the Host header.

    The original URL is rewritten at send time to replace the netloc with the
    pre-resolved IP. The Host header (already set by requests during prepare)
    remains the original hostname, so HTTP virtual-hosting continues to work.

    Args:
        pinned_ip: The numeric IP address string (IPv4 or IPv6) returned by
            validate_external_url's resolved_ip field.
    """

    def __init__(self, pinned_ip: str, *args, **kwargs):
        self._pinned_ip = pinned_ip
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        parsed = urlparse(request.url)
        port = parsed.port
        # Build the replacement netloc: [ip]:port or ip:port.
        # IPv6 addresses require bracket notation in URLs.
        try:
            addr = ipaddress.ip_address(self._pinned_ip)
            ip_str = f"[{addr}]" if addr.version == 6 else str(addr)
        except ValueError:
            ip_str = self._pinned_ip
        netloc = f"{ip_str}:{port}" if port else ip_str
        request.url = urlunparse(parsed._replace(netloc=netloc))
        return super().send(request, **kwargs)
