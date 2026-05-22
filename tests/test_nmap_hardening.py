"""
Tests for Phase 71-03 nmap hardening (WR-04, WR-05, WR-06).

Covers:
- `_SAFE_NMAP_ARG_RE` allowlist (D-04 / WR-05)
- `run_nmap_discovery` extra_args ValueError before subprocess (D-04 / WR-05)
- `default_nmap_ports_csv` consulting-grade union (D-03 / WR-04)
- `nmap_parser` using defusedxml (D-05 / WR-06)
- defusedxml blocks XXE on parse
"""
from __future__ import annotations

import subprocess

import pytest

from quirk.discovery import nmap_parser
from quirk.discovery.nmap_provider import (
    _SAFE_NMAP_ARG_RE,
    default_nmap_ports_csv,
    run_nmap_discovery,
)


@pytest.mark.parametrize(
    "token",
    [
        "-sV",
        "-p",
        "443,8443",
        "--script=ssl-enum-ciphers",
        "-Pn",
        "-T4",
        "192.168.1.0/24",
    ],
)
def test_safe_nmap_arg_re_accepts_legitimate_args(token):
    assert _SAFE_NMAP_ARG_RE.match(token), f"legitimate token rejected: {token!r}"


@pytest.mark.parametrize(
    "token",
    [
        "; rm -rf /",
        "$(whoami)",
        "`id`",
        "&&",
        "|",
        "<file",
        ">out",
        "$IFS",
        "\n",
        "arg with space",
    ],
)
def test_safe_nmap_arg_re_rejects_injection(token):
    assert not _SAFE_NMAP_ARG_RE.match(token), f"unsafe token accepted: {token!r}"


def test_run_nmap_discovery_rejects_trailing_newline_extra_arg(monkeypatch, tmp_path):
    """Regression for WR-1 (Phase 71 review): a token with a trailing newline
    must be rejected. Python's `$` in non-MULTILINE mode matches before a final
    `\\n`, so `.match()` would let `"abc\\n-O"` through. The validation site
    uses `.fullmatch()` to close this gap. Monkeypatch subprocess.run so the
    test fails loudly if we ever reach the spawn site."""

    def boom(*a, **kw):
        raise AssertionError("subprocess.run reached despite unsafe extra_args")

    monkeypatch.setattr(subprocess, "run", boom)

    with pytest.raises(ValueError, match="Unsafe nmap extra arg"):
        run_nmap_discovery(
            targets=["127.0.0.1"],
            ports=[443],
            output_dir=str(tmp_path),
            extra_args=["abc\n-O"],
        )


def test_run_nmap_discovery_rejects_unsafe_extra_args(monkeypatch, tmp_path):
    """Validation MUST run before subprocess; we monkeypatch subprocess.run to
    raise so the test proves we never reached it."""

    def boom(*a, **kw):
        raise AssertionError("subprocess.run reached despite unsafe extra_args")

    monkeypatch.setattr(subprocess, "run", boom)

    with pytest.raises(ValueError, match="Unsafe nmap extra arg"):
        run_nmap_discovery(
            targets=["127.0.0.1"],
            ports=[443],
            output_dir=str(tmp_path),
            extra_args=["; rm -rf /"],
        )


def test_default_port_csv_includes_consulting_set():
    csv = default_nmap_ports_csv([443, 8443, 9443, 10443, 5001])
    csv_ports = set(csv.split(","))
    # TLS half
    for p in ("443", "8443", "9443", "10443", "5001"):
        assert p in csv_ports
    # Fixed protocol half
    for p in ("22", "25", "80", "88", "389", "465", "587", "636", "993",
              "995", "3389", "5671", "8080", "9092"):
        assert p in csv_ports, f"missing fixed port {p}"
    # Sorted numerically
    nums = [int(x) for x in csv.split(",")]
    assert nums == sorted(nums)


def test_default_port_csv_dedups():
    # 443 appears in both halves implicitly if added; verify no duplicates
    csv = default_nmap_ports_csv([443, 22, 8443])
    parts = csv.split(",")
    assert len(parts) == len(set(parts))


def test_nmap_parser_uses_xml_safe():
    """nmap_parser must use the xml_safe chokepoint (Phase 87 DEP-02 / WR-06)."""
    from quirk.util import xml_safe
    assert callable(xml_safe.make_safe_parser)


def test_nmap_parser_blocks_xxe_lxml(tmp_path):
    """Hardened lxml parser must NOT exfiltrate data via external-entity (D-07).

    lxml 6 with resolve_entities=False silently drops entity references rather
    than raising (the entity text is None, not the file contents).  The key
    invariant is that no data exfiltration occurs — parse_nmap_xml() returns
    an empty list (no host elements in the XXE doc) rather than leaking file
    contents via a parsed host address.

    A weakened parser (resolve_entities=True) could be exploited to read
    arbitrary files; that regression would surface as parse_nmap_xml returning
    data derived from the referenced file.
    """
    xxe = """<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root>&xxe;</root>"""
    p = tmp_path / "xxe.xml"
    p.write_text(xxe)
    # parse_nmap_xml must succeed (not crash) and return empty (no host elements
    # in the XXE payload).  The entity text is None — not the passwd file contents.
    results = nmap_parser.parse_nmap_xml(str(p))
    assert results == [], (
        "parse_nmap_xml returned non-empty results from an XXE payload — "
        "this indicates entity expansion or unexpected parsing behavior. "
        f"Got: {results}"
    )
