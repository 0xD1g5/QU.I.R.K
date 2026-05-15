"""Phase 77 D-06 / scanners-protocol/IN-06: IPv4 detection via ipaddress.

The previous dotted-quad ``parts.isdigit()`` heuristic mis-classified
inputs like ``"::1"`` (IPv6) and was brittle for any non-octet-string
numeric tokens. The fix uses ``ipaddress.ip_address`` with try/except
(RESEARCH Pattern 4).
"""
from __future__ import annotations

import ast
import pathlib

from quirk.scanner.kerberos_scanner import _derive_realm


def test_ipv4_address_returned_uppercased_unchanged() -> None:
    assert _derive_realm("10.0.0.1") == "10.0.0.1"


def test_ipv6_address_is_now_recognised_and_returned_as_is() -> None:
    # Pre-fix: isdigit() failed on ":", so this fell through to the
    # "len(parts) >= 2" branch and produced the wrong result.
    assert _derive_realm("::1") == "::1"


def test_fqdn_yields_last_two_labels_uppercase() -> None:
    assert _derive_realm("host.example.com") == "EXAMPLE.COM"


def test_single_label_uppercased() -> None:
    assert _derive_realm("server") == "SERVER"


def test_module_uses_ipaddress_stdlib() -> None:
    src = pathlib.Path("quirk/scanner/kerberos_scanner.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    # Must import the ipaddress module somewhere.
    assert any(
        (isinstance(n, ast.Import) and any(a.name == "ipaddress" for a in n.names))
        or (isinstance(n, ast.ImportFrom) and n.module == "ipaddress")
        for n in ast.walk(tree)
    ), "Phase 77 D-06: kerberos_scanner must import the ipaddress stdlib module"
    # And must call ipaddress.ip_address somewhere.
    assert "ipaddress.ip_address" in src, (
        "Phase 77 D-06: kerberos_scanner must call ipaddress.ip_address"
    )
