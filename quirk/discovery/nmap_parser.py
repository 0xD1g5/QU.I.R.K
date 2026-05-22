from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
from lxml import etree as ET
from quirk.util.xml_safe import make_safe_parser
# WR-06 mitigation: XML parsed via quirk/util/xml_safe.py hardened lxml parser
# (resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False,
# huge_tree=False).  Phase 87 DEP-02 migration to the xml_safe chokepoint.
# Invariant test: tests/test_xml_safe.py::test_nmap_parser_blocks_xxe_lxml (D-07).
# DO NOT replace make_safe_parser() with a shared parser constant — see D-04.


@dataclass
class NmapOpenPort:
    host: str
    port: int
    protocol: str
    service: Optional[str] = None


def parse_nmap_xml(xml_path: str) -> List[NmapOpenPort]:
    """
    Parse Nmap XML output and return a list of open ports.
    Only returns ports with state="open".
    """
    tree = ET.parse(xml_path, parser=make_safe_parser())
    root = tree.getroot()

    results: List[NmapOpenPort] = []

    for host_el in root.findall("host"):
        status_el = host_el.find("status")
        if status_el is not None and status_el.get("state") not in (None, "up"):
            continue

        # Prefer IPv4, then any address
        addr = None
        for addr_el in host_el.findall("address"):
            if addr_el.get("addrtype") == "ipv4":
                addr = addr_el.get("addr")
                break
        if addr is None:
            addr_el = host_el.find("address")
            addr = addr_el.get("addr") if addr_el is not None else None

        if not addr:
            continue

        ports_el = host_el.find("ports")
        if ports_el is None:
            continue

        for port_el in ports_el.findall("port"):
            proto = (port_el.get("protocol") or "tcp").lower()
            portid = port_el.get("portid")
            if not portid:
                continue

            state_el = port_el.find("state")
            if state_el is None:
                continue

            if state_el.get("state") != "open":
                continue

            svc_el = port_el.find("service")
            svc_name = svc_el.get("name") if svc_el is not None else None

            try:
                p = int(portid)
            except ValueError:
                continue

            results.append(NmapOpenPort(host=addr, port=p, protocol=proto, service=svc_name))

    return results


def to_targets(open_ports: List[NmapOpenPort], tcp_only: bool = True) -> List[Tuple[str, int]]:
    """
    Convert parsed open ports into (host, port) targets for downstream scanning.
    """
    targets: List[Tuple[str, int]] = []
    for item in open_ports:
        if tcp_only and item.protocol != "tcp":
            continue
        targets.append((item.host, item.port))
    return targets

