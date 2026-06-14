"""Phase 127 — HWCOMPAT-01 hardware scanner behavior contract tests.

No network connections are made. CryptoEndpoint fixtures have service_detail
set directly to simulate SSH banner data already captured by ssh_scanner.py.
HTTP mgmt path is out of scope for these unit tests (no live socket/HTTP).

Fixture note: CryptoEndpoint.__new__(CryptoEndpoint) creates an uninstrumented
SQLAlchemy object. Attributes are set via ep.__dict__ to bypass ORM
instrumentation (avoids AttributeError on NoneType in SQLAlchemy 2.x when
there is no active mapper state — the conftest DB session is not required for
these pure-logic tests).
"""
from __future__ import annotations


def _make_ep(host: str, port: int, service_detail: str):
    """Create a CryptoEndpoint fixture without DB/ORM setup."""
    from quirk.models import CryptoEndpoint
    ep = CryptoEndpoint.__new__(CryptoEndpoint)
    ep.__dict__["host"] = host
    ep.__dict__["port"] = port
    ep.__dict__["protocol"] = "SSH"
    ep.__dict__["service_detail"] = service_detail
    return ep


# ------------ Cisco SSH banner: high-confidence match ------------

def test_cisco_ssh_banner_high_confidence() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep("10.0.0.1", 22, "SSH-2.0-Cisco-1.25")
    device = fingerprint_one(ep, timeout=3)

    assert device.vendor == "Cisco"
    assert device.confidence in {"high", "medium"}
    assert device.fingerprint_method == "ssh_banner"


# ------------ Unknown banner: never suppressed (D-06) ------------

def test_unknown_banner_not_suppressed() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep("10.0.0.2", 22, "SSH-2.0-OpenSSH_9.6")
    device = fingerprint_one(ep)

    # D-06: vendor=Unknown rows are never suppressed
    assert device.vendor == "Unknown"
    assert device.confidence in {"low", "unknown"}


# ------------ Batch function: one result per endpoint, Unknown emitted ------------

def test_fingerprint_hardware_returns_one_per_endpoint() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_hardware

    ep_cisco = _make_ep("10.0.0.1", 22, "SSH-2.0-Cisco-1.25")
    ep_unknown = _make_ep("10.0.0.3", 22, "SSH-2.0-dropbear_2022.83")

    results = fingerprint_hardware([ep_cisco, ep_unknown])

    assert len(results) == 2

    hosts_in_output = {d.host for d in results}
    assert "10.0.0.1" in hosts_in_output
    assert "10.0.0.3" in hosts_in_output

    # D-06: Unknown rows must appear in results (not dropped)
    unknown_rows = [d for d in results if d.vendor == "Unknown"]
    assert len(unknown_rows) >= 1
