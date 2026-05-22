"""Phase 87 / Plan 02 (DEP-02): hardened lxml XML parser chokepoint.

All XML parsing in quirk/ MUST go through this module.  The factory and helper
below provide a single, auditable entry point that enforces XXE/SSRF/DoS
protection as a CI-locked invariant (see tests/test_xml_safe.py, D-07).

Public surface:

- ``make_safe_parser()`` — fresh hardened ``lxml.etree.XMLParser`` per call.
  MUST be called per-use (not stored as a module-level constant) because lxml
  parser objects are not thread-safe (D-04).
- ``parse_safely(source)`` — convenience wrapper around ``etree.parse()`` for
  file-path and file-like consumers (e.g. nmap_parser.py).  SAML/fromstring
  callers use ``make_safe_parser()`` directly.
"""
from __future__ import annotations

from lxml import etree


def make_safe_parser() -> etree.XMLParser:
    """Return a fresh hardened lxml XMLParser (D-04, D-07).

    Callers MUST use this factory (not a shared constant) because lxml
    XMLParser objects are not thread-safe and the SSH/SAML scanners run
    threaded.  All five flags are explicit so audit reviewers can verify
    XXE protection at a glance.

    Flags:
        resolve_entities=False  — block XXE entity expansion (primary control)
        no_network=True         — block SSRF via external DTD/entity URIs
        load_dtd=False          — prevent DTD loading (filesystem + network vectors)
        dtd_validation=False    — prevent DTD-triggered fetches during validation
        huge_tree=False         — keep memory/depth limits active (billion-laughs)

    DO NOT replace calls to make_safe_parser() with a shared parser constant
    — see D-04 (lxml parsers are not thread-safe).
    """
    return etree.XMLParser(
        resolve_entities=False,   # block XXE entity expansion (primary control)
        no_network=True,          # block SSRF via external DTD/entity URIs
        load_dtd=False,           # prevent DTD loading (filesystem + network vectors)
        dtd_validation=False,     # prevent DTD-triggered fetches during validation
        huge_tree=False,          # keep memory/depth limits active
    )


def parse_safely(source) -> etree._ElementTree:
    """Parse XML from a path or file-like object using the hardened parser.

    Convenience wrapper for ``etree.parse()`` consumers (e.g. nmap_parser.py).
    Call sites needing ``fromstring(bytes)`` must call ``make_safe_parser()``
    directly and pass it to ``etree.fromstring()``.

    Raises:
        lxml.etree.XMLSyntaxError — on XXE, billion-laughs, or malformed XML.
    """
    return etree.parse(source, parser=make_safe_parser())
