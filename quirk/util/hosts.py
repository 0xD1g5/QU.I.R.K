"""Dependency-light host classification helpers.

Kept free of web-stack imports so the frozen Windows sensor build can
use it without pulling in the web stack.
"""
from __future__ import annotations

import ipaddress

_LOOPBACK_NAMES: frozenset[str] = frozenset({"localhost"})


def is_loopback_host(host: str) -> bool:
    """Return True when *host* can only be reached from the local machine.

    Accepts ``localhost``, any IPv4/IPv6 loopback address (``127.0.0.0/8``,
    ``::1``) and IPv4-mapped loopback (``::ffff:127.0.0.1``). Bind-all
    addresses, routable addresses and unknown hostnames return False.
    """
    h = (host or "").strip()
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    h = h.strip().lower()
    if not h:
        return False
    if h in _LOOPBACK_NAMES:
        return True
    pct = h.find("%")
    if pct >= 0:
        h = h[:pct]
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped.is_loopback
    return False
