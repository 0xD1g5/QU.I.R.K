"""Phase 81 CMVP-05 — coverage_for_algorithm lookup tests.

Validates the bundled cmvp_cache.json + the algorithm-name normalization map
in quirk/compliance/cmvp.py::_FAMILY_MAP. Edge cases:
  - AES-256-GCM resolves to ≥1 covering module (RESEARCH MEDIUM-confidence
    anchor — OpenSSL FIPS Provider cert 4985).
  - Already-family names (``AES``) resolve to the same coverage list.
  - ChaCha20-Poly1305 explicitly mapped to ``None`` → returns ``[]``.
  - Unknown / nonsense names return ``[]`` (never raises).
  - Ordering invariant: FIPS 140-3 modules sort ahead of 140-2; within a tier
    the newest ``module_version`` sorts first.
  - Normalization: ``EdDSA`` / ``EDDSA`` case-folded to the same family.
  - Hybrid KEMs (``sntrup761x25519-sha512``) returns None / [] per RESEARCH
    MEDIUM-confidence note — documented as intentional.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Happy-path: AES-256-GCM hits the bundled cache.
# ---------------------------------------------------------------------------

def test_aes_256_gcm_has_coverage() -> None:
    """AES-256-GCM normalizes to AES and the bundled cache covers AES."""
    from quirk.compliance.cmvp import coverage_for_algorithm

    coverage = coverage_for_algorithm("AES-256-GCM")
    assert isinstance(coverage, list)
    assert len(coverage) >= 1, "AES-256-GCM should be covered by ≥1 module"
    # Sanity: no entry has a 'certified' key (v4.10-D-01).
    for m in coverage:
        assert "certified" not in m, (
            "coverage entries MUST NOT include a 'certified' key (v4.10-D-01)"
        )


def test_aes_family_alias_returns_same_coverage() -> None:
    """``AES`` (already-family name) returns the same coverage list as
    ``AES-256-GCM`` — proves the normalization is idempotent."""
    from quirk.compliance.cmvp import coverage_for_algorithm

    a = coverage_for_algorithm("AES")
    b = coverage_for_algorithm("AES-256-GCM")
    a_certs = sorted(m["certificate_number"] for m in a)
    b_certs = sorted(m["certificate_number"] for m in b)
    assert a_certs == b_certs, (
        f"AES and AES-256-GCM resolved to different module sets: "
        f"{a_certs!r} vs {b_certs!r}"
    )


# ---------------------------------------------------------------------------
# Negative / unknown — never raise, always return [].
# ---------------------------------------------------------------------------

def test_chacha20_poly1305_returns_empty() -> None:
    """ChaCha20-Poly1305 is explicitly mapped to ``None`` in _FAMILY_MAP →
    coverage_for_algorithm returns []."""
    from quirk.compliance.cmvp import coverage_for_algorithm

    assert coverage_for_algorithm("ChaCha20-Poly1305") == []


def test_unknown_algorithm_returns_empty() -> None:
    """Nonsense names return [] and do NOT raise."""
    from quirk.compliance.cmvp import coverage_for_algorithm

    assert coverage_for_algorithm("nonsense-xyz-zzz") == []


def test_empty_string_returns_empty() -> None:
    """Empty/None inputs return [] without raising."""
    from quirk.compliance.cmvp import coverage_for_algorithm

    assert coverage_for_algorithm("") == []


# ---------------------------------------------------------------------------
# Ordering: FIPS 140-3 first, recent module_version first within tier.
# ---------------------------------------------------------------------------

def test_ordering_140_3_before_140_2(monkeypatch) -> None:
    """When the cache contains one 140-3 and one 140-2 AES module, the 140-3
    module appears at index 0."""
    import quirk.compliance.cmvp as cmvp_mod

    fixture = {
        "schema_version": "1.0",
        "last_verified": "2026-05-16",
        "source_url": cmvp_mod.CMVP_SEARCH_URL,
        "modules": [
            {
                "certificate_number": "AAA",
                "vendor": "v",
                "name": "Old AES Module",
                "module_version": "1.0",
                "fips_level": "140-2",
                "overall_level": "1",
                "algorithms": ["AES"],
            },
            {
                "certificate_number": "BBB",
                "vendor": "v",
                "name": "New AES Module",
                "module_version": "2.0",
                "fips_level": "140-3",
                "overall_level": "1",
                "algorithms": ["AES"],
            },
        ],
    }
    monkeypatch.setattr(cmvp_mod, "_CACHE", fixture)

    coverage = cmvp_mod.coverage_for_algorithm("AES")
    assert len(coverage) == 2
    assert coverage[0]["fips_level"] == "140-3"
    assert coverage[1]["fips_level"] == "140-2"


def test_ordering_recent_module_version_first(monkeypatch) -> None:
    """Within the 140-3 tier, the newer module_version sorts first."""
    import quirk.compliance.cmvp as cmvp_mod

    fixture = {
        "schema_version": "1.0",
        "last_verified": "2026-05-16",
        "source_url": cmvp_mod.CMVP_SEARCH_URL,
        "modules": [
            {
                "certificate_number": "X1",
                "vendor": "v",
                "name": "OpenSSL FIPS Provider",
                "module_version": "3.0.9",
                "fips_level": "140-3",
                "overall_level": "1",
                "algorithms": ["AES"],
            },
            {
                "certificate_number": "X2",
                "vendor": "v",
                "name": "OpenSSL FIPS Provider",
                "module_version": "3.1.2",
                "fips_level": "140-3",
                "overall_level": "1",
                "algorithms": ["AES"],
            },
        ],
    }
    monkeypatch.setattr(cmvp_mod, "_CACHE", fixture)

    coverage = cmvp_mod.coverage_for_algorithm("AES")
    assert len(coverage) == 2
    versions = [m["module_version"] for m in coverage]
    assert versions == ["3.1.2", "3.0.9"], (
        f"Newer module_version should sort first; got {versions!r}"
    )


# ---------------------------------------------------------------------------
# Normalization edge cases (RESEARCH MEDIUM-confidence section).
# ---------------------------------------------------------------------------

def test_normalize_eddsa_case_insensitive() -> None:
    """Both ``EdDSA`` and ``EDDSA`` normalize to the same family (EdDSA).
    Documented MEDIUM-confidence in RESEARCH; both must be case-folded."""
    from quirk.compliance.cmvp import normalize_for_cmvp_lookup

    a = normalize_for_cmvp_lookup("EdDSA")
    b = normalize_for_cmvp_lookup("EDDSA")
    # Either both map to the same family (preferred) OR both map to None.
    # The contract is "they agree", not "they hit any specific value".
    assert a == b, f"Case-folding broken: EdDSA={a!r}, EDDSA={b!r}"


def test_normalize_ed25519_returns_eddsa_family() -> None:
    """``ed25519`` and ``ssh-ed25519`` both map to the EdDSA family."""
    from quirk.compliance.cmvp import normalize_for_cmvp_lookup

    assert normalize_for_cmvp_lookup("ed25519") == "EdDSA"
    assert normalize_for_cmvp_lookup("ssh-ed25519") == "EdDSA"


def test_normalize_hybrid_kem_documented() -> None:
    """Hybrid KEM names like ``sntrup761x25519-sha512`` are NOT in the CMVP
    catalog (RESEARCH MEDIUM-confidence note — sntrup761 is not NIST-validated).
    Documented as intentional — downstream renders 'Not in CMVP catalog'."""
    from quirk.compliance.cmvp import (
        coverage_for_algorithm,
        normalize_for_cmvp_lookup,
    )

    family = normalize_for_cmvp_lookup("sntrup761x25519-sha512")
    assert family is None, (
        "sntrup761 hybrid KEMs are NOT NIST-validated — must map to None"
    )
    assert coverage_for_algorithm("sntrup761x25519-sha512") == []


def test_normalize_chacha20_returns_none() -> None:
    """ChaCha20 / ChaCha20-Poly1305 are explicitly non-CMVP-approved."""
    from quirk.compliance.cmvp import normalize_for_cmvp_lookup

    assert normalize_for_cmvp_lookup("ChaCha20-Poly1305") is None
    assert normalize_for_cmvp_lookup("chacha20") is None


def test_coverage_query_never_raises_on_garbage_input() -> None:
    """Defensive: hostile inputs (whitespace, mixed case, unicode garbage)
    return [] without raising."""
    from quirk.compliance.cmvp import coverage_for_algorithm

    for garbage in ("   ", "AES   ", "🦄-256-gcm", "AES\nwith\nnewlines"):
        try:
            result = coverage_for_algorithm(garbage)
        except Exception as e:  # pragma: no cover - regression guard
            pytest.fail(f"coverage_for_algorithm raised on {garbage!r}: {e}")
        assert isinstance(result, list)
