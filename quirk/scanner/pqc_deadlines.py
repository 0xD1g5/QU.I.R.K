"""Phase 180 (CLOSE-03): EO 14412 PQC transition deadline catalog.

Eighth staleness-gated catalog in CLAUDE.md's "Staleness Review Cadence" —
after ``quirk/qramm/model_meta.py`` (QRAMM, 90-day), ``quirk/compliance/__init__.py``
(compliance mappings, 365-day), ``quirk/compliance/cmvp.py`` (CMVP, 90-day),
``quirk/scanner/hw_cve.py`` (firmware CVE, 30-day), ``quirk/scanner/snmp_meta.py``
(SNMP vendor matrix, 90-day), ``quirk/scanner/bacnet_vendors.py`` (BACnet vendors,
365-day), and ``quirk/scanner/hardware_eol.py`` (hardware EOL, 365-day). This module
mirrors ``hw_cve.py``'s ``STALENESS_THRESHOLD_DAYS`` / ``*_TABLE_META`` /
``is_*_stale()`` triad exactly.

Purpose: burndown "relative to a named target date" rather than a single scalar —
an endpoint using RSA key exchange is late against the key_establishment deadline
while an RSA *signature* is late against the digital_signature deadline (see
``PQC_DEADLINES`` below for the literal dates). One scalar cannot express that.

Cadence: 90 days, matching QRAMM and CMVP (the precedent for policy catalogs, not
the 30-day CVE cadence or the 365-day static-registry cadence). EO 14412 and
OMB M-26-15 invalidated the prior consensus inside a 3-day window (2026-09) — this
catalog needs real pressure.

Source: Federal Register Vol. 91 No. 121 (2026-06-25), FR Doc 2026-12909, Executive
Order 14412, "Securing the Nation Against Advanced Cryptographic Attacks". Re-verifying
this catalog means re-reading that Federal Register URL — it is the operative US federal
instrument and binds "key establishment" to FIPS 203 (ML-KEM) and "digital signature" to
FIPS 186-5 (DSS).

Scope split (D-16): ``key_establishment`` and ``digital_signature`` are ALGORITHM-CLASS
deadlines — a finding maps to one of them via its ``CryptoPrimitive`` (see
``deadline_for_algorithm`` below). ``nist_subset`` and ``far_contractor`` are
ORGANISATION-SCOPE deadlines — scoped by WHO operates the system, not by which
algorithm a finding uses. They are catalogued here because CLOSE-03 requires all four
EO dates to be recorded, but ``deadline_for_algorithm()`` NEVER returns them
(``test_organisation_scope_deadlines_are_never_returned`` asserts this by sweeping
every algorithm the classifier knows).

CNSA 2.0 is a DELIBERATE, DOCUMENTED omission, not a silent gap: ``media.defense.gov``
returns HTTP 403 to non-browser user agents (re-confirmed 2026-09-02). No CNSA 2.0 date
literal appears anywhere in this module. Do NOT add CNSA 2.0 dates from secondary
sources (blog posts, vendor whitepapers, concurring-but-unverifiable summaries) — that
would launder an inaccessible primary source into an apparent fact, which is exactly the
failure this catalog exists to prevent. If CNSA 2.0 dates are ever needed, the correct
fix is to re-attempt a primary-source fetch of the NSA PDF (e.g. via a browser-like
fetch path), not to substitute a secondary source.

Zero network calls, stdlib only (``datetime``).
"""
from __future__ import annotations

import datetime
from typing import Optional

from cyclonedx.model.crypto import CryptoPrimitive

from quirk.cbom.classifier import classify_algorithm, _ALGORITHM_TABLE

# ---------------------------------------------------------------------------
# Staleness gate — mirrors quirk/scanner/hw_cve.py::is_cve_table_stale
# ---------------------------------------------------------------------------

# 90-day cadence, matching QRAMM/CMVP — see module docstring.
STALENESS_THRESHOLD_DAYS: int = 90

PQC_DEADLINE_TABLE_META = {
    "last_verified": "2026-09-02",
    "source": (
        "Federal Register Vol. 91 No. 121 (2026-06-25), FR Doc 2026-12909, "
        "Executive Order 14412"
    ),
    "source_url": (
        "https://www.federalregister.gov/documents/2026/06/25/2026-12909/"
        "securing-the-nation-against-advanced-cryptographic-attacks"
    ),
}


def is_pqc_deadline_table_stale(today: Optional[datetime.date] = None) -> bool:
    """Returns True when the catalog has not been re-verified within
    ``STALENESS_THRESHOLD_DAYS`` (90) days of ``today`` (default: ``today()``).

    Boundary: ``age > STALENESS_THRESHOLD_DAYS`` (strict greater-than), so exactly
    90 days old is NOT stale.
    """
    reference = today or datetime.date.today()
    last_verified = datetime.date.fromisoformat(
        PQC_DEADLINE_TABLE_META["last_verified"]
    )
    age = (reference - last_verified).days
    return age > STALENESS_THRESHOLD_DAYS


# ---------------------------------------------------------------------------
# Catalog — the four EO 14412 dates, verbatim from the Federal Register text
# ---------------------------------------------------------------------------

PQC_DEADLINES: dict = {
    "key_establishment": {
        "date": "2030-12-31",
        "standard": "FIPS 203 (ML-KEM)",
        "description": (
            "Transition all HVAs and high impact systems to use PQC for key "
            "establishment by December 31, 2030."
        ),
        "scope": "algorithm_class",
    },
    "digital_signature": {
        "date": "2031-12-31",
        "standard": "FIPS 186-5 (DSS)",
        "description": (
            "Transition all HVAs and high impact systems to use PQC for digital "
            "signatures by December 31, 2031."
        ),
        "scope": "algorithm_class",
    },
    "nist_subset": {
        "date": "2027-12-31",
        "standard": None,
        "description": (
            "An appropriate subset of NIST-owned/operated systems must complete "
            "PQC transition no later than December 31, 2027."
        ),
        "scope": "organisation",
    },
    "far_contractor": {
        "date": "2030-12-31",
        "standard": None,
        "description": (
            "FAR amendment requiring covered contractors to comply with NIST FIPS "
            "including all applicable FIPS incorporating PQC-compliant algorithms, "
            "by December 31, 2030."
        ),
        "scope": "organisation",
    },
}


# ---------------------------------------------------------------------------
# Finding -> deadline mapping — classify_algorithm() is the ONLY source of
# algorithm truth (D-17/D-18). No parallel algorithm->deadline table.
# ---------------------------------------------------------------------------

# D-18: every CryptoPrimitive the classifier emits (measured 2026-09-02: SIGNATURE,
# BLOCK_CIPHER, KEY_AGREE, HASH, PKE, AE, KEM, MAC, STREAM_CIPHER, UNKNOWN — 10
# distinct primitives across 120 _ALGORITHM_TABLE rows) has an EXPLICIT disposition.
# PKE is routed through the sentinel below, never bucketed directly here, because a
# single CryptoPrimitive cannot distinguish key-transport RSA from signature RSA
# (D-17). Every other primitive maps directly, including an explicit `None` for
# primitive classes EO 14412 does not date (symmetric/hash/MAC primitives).
_PKE_SENTINEL = "_pke_disambiguation"

PRIMITIVE_DEADLINE: dict = {
    CryptoPrimitive.KEM: "key_establishment",
    CryptoPrimitive.KEY_AGREE: "key_establishment",
    CryptoPrimitive.SIGNATURE: "digital_signature",
    CryptoPrimitive.PKE: _PKE_SENTINEL,
    CryptoPrimitive.AE: None,
    CryptoPrimitive.BLOCK_CIPHER: None,
    CryptoPrimitive.HASH: None,
    CryptoPrimitive.MAC: None,
    CryptoPrimitive.STREAM_CIPHER: None,
    CryptoPrimitive.UNKNOWN: None,
}

# D-17 — the PKE resolution rule, per slug, drift-guarded.
#
# CryptoPrimitive.PKE alone cannot resolve a deadline: the classifier tags BOTH
# `rsa-kex` (key transport, TLS/SSH key exchange) AND DNSSEC's RRSIG-signing slugs
# (`rsasha256`, `rsasha512`, etc.) with the same enum member. The three-part rule:
#
#   1. `rsa-kex` -> `key_establishment` (2030-12-31). The classifier's own inline
#      comment states this slug exists specifically to disambiguate key-transport
#      RSA from certificate-signature RSA.
#   2. The five DNSSEC RRSIG-signing slugs (`rsamd5`, `rsasha1`,
#      `rsasha1-nsec3-sha1`, `rsasha256`, `rsasha512`) -> `digital_signature`
#      (2031-12-31). These sign DNS resource records.
#   3. The five bare-modulus X.509/SSH slugs (`rsa`, `rsa-1024`, `rsa-2048`,
#      `rsa-3072`, `rsa-4096`) -> `digital_signature` (2031-12-31). They name an
#      X.509/SSH public KEY, whose PQC exposure in every family that emits them is
#      certificate or host-key SIGNATURE verification — the key-transport case is
#      carved out under its own `rsa-kex` slug.
#
# This is a DISAMBIGUATION OVERLAY over PKE only — never a parallel
# algorithm->deadline table. `test_pke_disambiguation_covers_every_pke_row` asserts
# this dict's key set is EXACTLY the set of PKE slugs in `_ALGORITHM_TABLE` (11
# today), so a new upstream PKE row fails RED instead of silently defaulting.
_PKE_DISAMBIGUATION: dict = {
    "rsa-kex": "key_establishment",
    "rsamd5": "digital_signature",
    "rsasha1": "digital_signature",
    "rsasha1-nsec3-sha1": "digital_signature",
    "rsasha256": "digital_signature",
    "rsasha512": "digital_signature",
    "rsa": "digital_signature",
    "rsa-1024": "digital_signature",
    "rsa-2048": "digital_signature",
    "rsa-3072": "digital_signature",
    "rsa-4096": "digital_signature",
}


def deadline_for_algorithm(
    algorithm: str, family: Optional[str] = None
) -> Optional[str]:
    """Map a raw algorithm string to an EO 14412 deadline bucket key
    (``"key_establishment"``, ``"digital_signature"``) or ``None`` if the
    algorithm's primitive class has no EO 14412 date.

    Dispatches entirely through ``classify_algorithm()`` (the classifier is the
    single source of algorithm truth — no algorithm class is restated here) and
    ``PRIMITIVE_DEADLINE`` / ``_PKE_DISAMBIGUATION`` (D-17/D-18). Never returns
    ``"nist_subset"`` or ``"far_contractor"`` — those are organisation-scope
    deadlines (D-16), not algorithm-scope ones.

    ``family`` is accepted for call-site symmetry with Plan 04's closure code
    (which resolves family via ``scope_signature.family_for_protocol``) and to
    keep the door open for a future family-conditioned rule. Under D-17 the
    resolution is per-slug and ``family`` does NOT currently change the result —
    this is a documented no-op, not an oversight.
    """
    primitive, _quantum_level, _classical_level = classify_algorithm(algorithm)
    bucket = PRIMITIVE_DEADLINE.get(primitive)
    if bucket is None:
        return None
    if bucket == _PKE_SENTINEL:
        normalized = (algorithm or "").split("@", 1)[0].lower()
        return _PKE_DISAMBIGUATION.get(normalized)
    return bucket
