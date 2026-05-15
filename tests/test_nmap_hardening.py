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


def test_nmap_parser_uses_defusedxml():
    assert nmap_parser.ET.__name__.startswith("defusedxml")


def test_nmap_parser_blocks_xxe(tmp_path):
    """defusedxml must raise on external-entity declarations."""
    from defusedxml.common import EntitiesForbidden

    xxe = """<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root>&xxe;</root>"""
    p = tmp_path / "xxe.xml"
    p.write_text(xxe)
    with pytest.raises(EntitiesForbidden):
        nmap_parser.ET.parse(str(p))
