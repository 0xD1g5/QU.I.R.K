"""Phase 77 D-02 / scanners-protocol/IN-02: DNSSEC alg map covers 9 and 11.

Per IANA DNS Security Algorithm Numbers registry / RFC 8624: algorithm
numbers 9 and 11 are Reserved. The map previously had no entry for these
values (alg 7 RSASHA1-NSEC3-SHA1 was already present — RESEARCH C-9
corrects the CONTEXT D-02 mis-identification).
"""
from __future__ import annotations

from quirk.scanner.dnssec_scanner import DNSSEC_ALG_MAP


def test_alg_9_present_as_reserved() -> None:
    assert 9 in DNSSEC_ALG_MAP, "Phase 77 D-02: alg 9 must be in DNSSEC_ALG_MAP"
    name, severity = DNSSEC_ALG_MAP[9]
    assert name == "Reserved"
    assert severity == "HIGH"


def test_alg_11_present_as_reserved() -> None:
    assert 11 in DNSSEC_ALG_MAP, "Phase 77 D-02: alg 11 must be in DNSSEC_ALG_MAP"
    name, severity = DNSSEC_ALG_MAP[11]
    assert name == "Reserved"
    assert severity == "HIGH"


def test_alg_7_remains_rsasha1_nsec3_sha1() -> None:
    """RESEARCH C-9 guard: do not regress alg 7 (which was already correct)."""
    assert DNSSEC_ALG_MAP[7][0] == "RSASHA1-NSEC3-SHA1"
