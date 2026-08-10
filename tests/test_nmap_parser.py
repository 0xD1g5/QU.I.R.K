"""Phase 145 / Plan 01 (DISC-03): tests for nmap_parser.parse_nmap_host_status.

Covers the up/down host-status parser used by the liveness pre-pass. Unlike
parse_nmap_xml(), parse_nmap_host_status() must return a row for every host
nmap reported on, including hosts whose status is "down" (D-04: record, don't
silently drop non-responsive hosts).
"""
from __future__ import annotations

from quirk.discovery.nmap_parser import (
    parse_nmap_host_status,
    NmapHostStatus,
    parse_nmap_run_summary,
    NmapRunSummary,
)


_XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'


def _write_xml(tmp_path, body: str, name: str = "nmap.xml") -> str:
    xml_path = tmp_path / name
    xml_path.write_text(_XML_HEADER + f"<nmaprun>{body}</nmaprun>")
    return str(xml_path)


def test_parse_host_status_up_and_down(tmp_path):
    body = """
    <host>
      <status state="up" reason="syn-ack" reason_ttl="0"/>
      <address addr="10.0.0.1" addrtype="ipv4"/>
    </host>
    <host>
      <status state="down" reason="no-response" reason_ttl="0"/>
      <address addr="10.0.0.2" addrtype="ipv4"/>
    </host>
    """
    xml_path = _write_xml(tmp_path, body)

    results = parse_nmap_host_status(xml_path)

    assert len(results) == 2, "down host must NOT be filtered out"
    up_row = next(r for r in results if r.host == "10.0.0.1")
    down_row = next(r for r in results if r.host == "10.0.0.2")
    assert up_row.up is True
    assert up_row.reason == "syn-ack"
    assert down_row.up is False
    assert down_row.reason == "no-response"


def test_parse_host_status_missing_reason_attribute(tmp_path):
    body = """
    <host>
      <status state="up"/>
      <address addr="10.0.0.5" addrtype="ipv4"/>
    </host>
    """
    xml_path = _write_xml(tmp_path, body)

    results = parse_nmap_host_status(xml_path)

    assert len(results) == 1
    assert results[0].reason == ""


def test_parse_host_status_prefers_ipv4_over_ipv6(tmp_path):
    body = """
    <host>
      <status state="up" reason="syn-ack"/>
      <address addr="fe80::1" addrtype="ipv6"/>
      <address addr="10.0.0.9" addrtype="ipv4"/>
    </host>
    """
    xml_path = _write_xml(tmp_path, body)

    results = parse_nmap_host_status(xml_path)

    assert len(results) == 1
    assert results[0].host == "10.0.0.9"


def test_parse_host_status_skips_host_with_no_address(tmp_path):
    body = """
    <host>
      <status state="up" reason="syn-ack"/>
    </host>
    """
    xml_path = _write_xml(tmp_path, body)

    results = parse_nmap_host_status(xml_path)

    assert results == []


def test_parse_host_status_skips_host_with_no_status(tmp_path):
    body = """
    <host>
      <address addr="10.0.0.3" addrtype="ipv4"/>
    </host>
    """
    xml_path = _write_xml(tmp_path, body)

    results = parse_nmap_host_status(xml_path)

    assert results == []


def test_parse_host_status_blocks_xxe(tmp_path):
    """Hardened lxml parser must NOT exfiltrate data via external-entity (D-07).

    Mirrors tests/test_nmap_hardening.py::test_nmap_parser_blocks_xxe_lxml:
    the XXE payload has no <host> elements, so the invariant is simply that
    parsing succeeds (no crash) and returns an empty list rather than leaking
    file contents.
    """
    xxe = """<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root>&xxe;</root>"""
    xml_path = tmp_path / "xxe.xml"
    xml_path.write_text(xxe)

    results = parse_nmap_host_status(xml_path.as_posix())

    assert results == [], (
        "parse_nmap_host_status returned non-empty results from an XXE payload — "
        f"got: {results}"
    )


def test_parse_run_summary_reads_runstats(tmp_path):
    """Reproduces the real nmap -sn -PS subnet-sweep XML shape (Phase 145
    D-06 human-UAT, 2026-08-10): only up hosts get a <host> element; the
    down count is exposed solely via <runstats><hosts total up down/>."""
    body = """
    <host>
      <status state="up" reason="syn-ack" reason_ttl="0"/>
      <address addr="10.0.0.1" addrtype="ipv4"/>
    </host>
    <runstats>
      <finished time="1786372704" exit="success"/>
      <hosts up="1" down="254" total="255"/>
    </runstats>
    """
    xml_path = _write_xml(tmp_path, body)

    summary = parse_nmap_run_summary(xml_path)

    assert summary == NmapRunSummary(exit_status="success", total=255, up=1, down=254)


def test_parse_run_summary_missing_runstats_returns_none(tmp_path):
    body = """
    <host>
      <status state="up" reason="syn-ack" reason_ttl="0"/>
      <address addr="10.0.0.1" addrtype="ipv4"/>
    </host>
    """
    xml_path = _write_xml(tmp_path, body)

    assert parse_nmap_run_summary(xml_path) is None


def test_parse_run_summary_malformed_counts_returns_none(tmp_path):
    body = """
    <runstats>
      <finished time="1786372704" exit="success"/>
      <hosts up="not-a-number" down="254" total="255"/>
    </runstats>
    """
    xml_path = _write_xml(tmp_path, body)

    assert parse_nmap_run_summary(xml_path) is None
