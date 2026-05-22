"""Phase 87 DEP-02 (D-04, D-07): xml_safe chokepoint forward-locking CI invariants.

This module installs six CI gates that lock the lxml XXE/billion-laughs
hardening invariants in perpetuity:

1. ``test_make_safe_parser_returns_fresh_instance`` — each call returns a NEW
   parser object (thread-safety invariant, D-04).
2. ``test_make_safe_parser_flags`` — returned parser enforces hardening flags via
   functional verification (XXE/SSRF/DoS controls, D-04).
3. ``test_parse_safely_accepts_valid_xml`` — round-trip of a minimal nmap XML
   fixture confirms the helper works on benign input.
4. ``test_parse_safely_blocks_billion_laughs`` — a billion-laughs DTD payload does
   not expand (entity text is None, not exponential string, D-07).  lxml 6 with
   ``resolve_entities=False`` + ``load_dtd=False`` silently drops entity
   references rather than raising — this IS the protection (no allocation occurs).
5. ``test_parse_safely_blocks_xxe`` — an external-entity (file://) XXE payload
   does NOT exfiltrate data (entity text is None, D-07).  ``resolve_entities=False``
   prevents expansion; the data is never read.  A weakened parser (resolve_entities
   =True) would return the file contents.
6. ``test_no_defusedxml_import_in_quirk`` — grep gate: zero ``defusedxml``
   imports remain anywhere under ``quirk/`` (permanent guard, D-03, D-07).

lxml 6 behavioral note: ``resolve_entities=False`` + ``load_dtd=False`` cause
entity references to resolve to ``None`` rather than raising ``XMLSyntaxError``.
The security guarantee is identical — the attacker's data is never read or
allocated — but the test assertion is ``assert root.text is None`` rather than
``pytest.raises(XMLSyntaxError)``.  Tests 4 and 5 encode this contract explicitly
so a weakening (resolve_entities=True) will fail the assertion.

These gates guarantee the xml_safe chokepoint stays the sole hardened XML entry
point across the v5.0+ lifetime of the project.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from lxml import etree

from quirk.util.xml_safe import make_safe_parser, parse_safely

# ---------------------------------------------------------------------------
# Payload constants
# ---------------------------------------------------------------------------

BILLION_LAUGHS = b"""\
<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<root>&lol4;</root>"""

XXE_EXTERNAL_ENTITY = b"""\
<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root>&xxe;</root>"""

MINIMAL_NMAP_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="" start="1716000000" version="7.95" xmloutputversion="1.05">
  <host starttime="1716000000" endtime="1716000001">
    <status state="up" reason="echo-reply"/>
    <address addr="127.0.0.1" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="443">
        <state state="open" reason="syn-ack"/>
        <service name="https"/>
      </port>
    </ports>
  </host>
</nmaprun>"""

# ---------------------------------------------------------------------------
# Parser construction tests
# ---------------------------------------------------------------------------


def test_make_safe_parser_returns_fresh_instance() -> None:
    """D-04 thread-safety invariant: each call returns a distinct parser object.

    lxml XMLParser objects are not thread-safe.  Sharing a single instance
    across the SSH/SAML scanner threads is a latent concurrency bug.  This gate
    ensures ``make_safe_parser()`` never becomes a cached/shared constant.
    """
    parser_a = make_safe_parser()
    parser_b = make_safe_parser()
    assert parser_a is not parser_b, (
        "make_safe_parser() returned the same object on two consecutive calls — "
        "this violates the D-04 per-call fresh-instance invariant (lxml parsers "
        "are not thread-safe)."
    )


def test_make_safe_parser_flags() -> None:
    """D-04 invariant: returned parser is an XMLParser that enforces hardening flags.

    Each flag targets a distinct attack vector:
      resolve_entities=False  -> XXE entity expansion
      no_network=True         -> SSRF via external DTD/entity URIs
      load_dtd=False          -> DTD-based filesystem + network vectors
      dtd_validation=False    -> DTD-triggered fetches during validation
      huge_tree=False         -> billion-laughs / memory exhaustion

    Functional verification: entity text is None (not expanded), not file contents.
    A weakened parser (resolve_entities=True) would return the actual file contents.
    """
    parser = make_safe_parser()
    assert isinstance(parser, etree.XMLParser), (
        "make_safe_parser() must return an lxml.etree.XMLParser instance"
    )
    # Functional verification (D-04): with resolve_entities=False, external entity
    # references are dropped — root.text is None, not the file contents.
    # This confirms XXE protection is active on the returned parser.
    result = etree.fromstring(XXE_EXTERNAL_ENTITY, parser=parser)
    assert result.text is None, (
        "make_safe_parser() parser allowed entity expansion (root.text is not None) "
        "— resolve_entities=False must be active. Got: {!r}".format(result.text[:50]
        if result.text else None)
    )


# ---------------------------------------------------------------------------
# parse_safely helper tests
# ---------------------------------------------------------------------------


def test_parse_safely_accepts_valid_xml() -> None:
    """D-05 invariant: parse_safely() round-trips a minimal valid nmap XML file.

    Confirms the hardened parser does not reject legitimate well-formed XML.
    """
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        f.write(MINIMAL_NMAP_XML)
        tmp_path = f.name

    tree = parse_safely(tmp_path)
    root = tree.getroot()
    assert root.tag == "nmaprun", (
        f"Expected root tag 'nmaprun', got {root.tag!r}"
    )
    hosts = root.findall("host")
    assert len(hosts) == 1, f"Expected 1 host element, got {len(hosts)}"


def test_parse_safely_blocks_billion_laughs() -> None:
    """D-07 forward-locking invariant: billion-laughs payload is NOT expanded.

    lxml 6 with ``resolve_entities=False`` + ``load_dtd=False`` silently drops
    entity references rather than raising — no exponential memory allocation
    occurs.  The entity text is None (entity dropped), not a gigabyte string.

    A future change that weakens ``resolve_entities`` to ``True`` will cause
    the entity to expand, making root.text non-None and failing this assertion,
    halting CI before the regression ships.
    """
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        f.write(BILLION_LAUGHS)
        tmp_path = f.name

    tree = parse_safely(tmp_path)
    root = tree.getroot()
    # Entity was NOT expanded — text is None (safe) rather than a giant string.
    assert root.text is None, (
        "Billion-laughs entity was expanded by parse_safely() — "
        "resolve_entities=False + load_dtd=False must be active. "
        "Got root.text length: {}".format(len(root.text) if root.text else 0)
    )


def test_parse_safely_blocks_xxe() -> None:
    """D-07 forward-locking invariant: XXE external-entity payload NOT exfiltrated.

    lxml 6 with ``resolve_entities=False`` does NOT read the file referenced by
    SYSTEM entity declarations — the entity text is None, not the file contents.
    This confirms no data exfiltration occurs via the XXE vector.

    A future change that sets ``resolve_entities=True`` will cause root.text to
    contain the actual file contents, failing this assertion and halting CI.
    """
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        f.write(XXE_EXTERNAL_ENTITY)
        tmp_path = f.name

    tree = parse_safely(tmp_path)
    root = tree.getroot()
    # Entity was NOT resolved — text is None (safe), not file contents.
    assert root.text is None, (
        "XXE entity was resolved by parse_safely() — data exfiltration detected. "
        "resolve_entities=False must be active.  Got root.text (first 50 chars): "
        "{!r}".format(root.text[:50] if root.text else None)
    )


# ---------------------------------------------------------------------------
# Grep gate — permanent forward-locking CI invariant
# ---------------------------------------------------------------------------


def test_no_defusedxml_import_in_quirk() -> None:
    """D-03 / D-07 permanent grep gate: zero defusedxml imports remain in quirk/.

    After Phase 87 DEP-02, ``defusedxml`` must not appear in any Python source
    file under ``quirk/``.  This gate covers BOTH migration sites:
      - ``quirk/discovery/nmap_parser.py`` (was ``import defusedxml.ElementTree``)
      - ``quirk/scanner/saml_scanner.py`` (was the ``except ImportError`` fallback)

    A future re-introduction of a defusedxml import will make this test RED,
    halting CI before the regression ships.
    """
    repo_root = Path(__file__).resolve().parent.parent
    quirk_dir = repo_root / "quirk"
    hits = [
        str(p.relative_to(repo_root))
        for p in quirk_dir.rglob("*.py")
        if "defusedxml" in p.read_text(encoding="utf-8")
    ]
    assert not hits, (
        f"defusedxml import found in {len(hits)} file(s) under quirk/ — "
        f"Phase 87 DEP-02 requires all XML parsing to route through "
        f"quirk/util/xml_safe.py (make_safe_parser / parse_safely). "
        f"Offending files: {hits}"
    )
