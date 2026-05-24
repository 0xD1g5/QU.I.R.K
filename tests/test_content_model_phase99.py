"""Phase 99 CTX-01/CTX-02 — content model unit tests.

Covers:
  - ALGO_IMPACT_MAP 3-tuple structure (quantum_risk_sentence at index [2])
  - REMEDIATION_CATALOG key parity with ALGO_IMPACT_MAP
  - CODESIGN_EXPIRY / CODESIGN_APPROACHING_EXPIRY keys in both maps
  - _classify_finding resolves codesign-expiry findings via check_id
  - _build_top_risks unpacks 3-tuple without ValueError

Fixture style mirrors test_exec_content_model.py (inline dict fixtures, one
assert per test with inline requirement-ID rationale string).
"""
from __future__ import annotations

import pytest

from quirk.reports.content_model import (
    ALGO_IMPACT_MAP,
    FALLBACK_QUANTUM_RISK,
    REMEDIATION_CATALOG,
    _classify_finding,
    build_exec_content,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_score_raw(score: int = 67, rating: str = "FAIR") -> dict:
    """CANONICAL score_raw shape (key 'score', not 'total')."""
    return {
        "score": score,
        "rating": rating,
        "subscores": {
            "hygiene": 20,
            "modern_tls": 18,
            "identity_trust": 25,
            "agility_signals": 15,
            "data_at_rest": 22,
            "data_in_motion": 21,
        },
        "drivers": [],
    }


def _make_rsa_finding(severity: str = "CRITICAL") -> dict:
    return {
        "title": "RSA-2048 certificate — quantum-vulnerable",
        "description": "Endpoint uses RSA-2048.",
        "severity": severity,
        "category": "RSA",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_quantum_risk_field_populated():
    """CTX-01: ALGO_IMPACT_MAP['RSA'][2] is a non-empty str (quantum_risk_sentence).

    Requirement: CTX-01 — each crypto class must carry a plain-language quantum-risk
    'so what' sentence in ALGO_IMPACT_MAP index [2].
    """
    entry = ALGO_IMPACT_MAP["RSA"]
    assert len(entry) == 3, (
        "ALGO_IMPACT_MAP RSA entry must be a 3-tuple. CTX-01 / D-01."
    )
    quantum_risk = entry[2]
    assert isinstance(quantum_risk, str) and quantum_risk.strip(), (
        "ALGO_IMPACT_MAP['RSA'][2] must be a non-empty string. CTX-01."
    )


def test_remediation_catalog_key_parity():
    """CTX-02: REMEDIATION_CATALOG has identical key set to ALGO_IMPACT_MAP.

    Requirement: CTX-02 — centralized remediation catalog (D-04) must cover
    every crypto class in ALGO_IMPACT_MAP; no gaps, no extra keys.
    """
    assert set(REMEDIATION_CATALOG) == set(ALGO_IMPACT_MAP), (
        f"Key mismatch: missing={set(ALGO_IMPACT_MAP) - set(REMEDIATION_CATALOG)}, "
        f"extra={set(REMEDIATION_CATALOG) - set(ALGO_IMPACT_MAP)}. "
        "CTX-02 / D-04: REMEDIATION_CATALOG and ALGO_IMPACT_MAP must share the same key set."
    )


def test_codesign_keys_present():
    """CTX-03: CODESIGN_EXPIRY and CODESIGN_APPROACHING_EXPIRY exist in both maps.

    Requirement: CTX-03 / D-07/D-08 — code-signing expiry must be a first-class
    crypto class with entries in both ALGO_IMPACT_MAP and REMEDIATION_CATALOG.
    """
    for key in ("CODESIGN_EXPIRY", "CODESIGN_APPROACHING_EXPIRY"):
        assert key in ALGO_IMPACT_MAP, (
            f"ALGO_IMPACT_MAP missing key '{key}'. CTX-03 / D-07."
        )
        assert key in REMEDIATION_CATALOG, (
            f"REMEDIATION_CATALOG missing key '{key}'. CTX-03 / D-04."
        )
        # Each entry must still be a 3-tuple
        assert len(ALGO_IMPACT_MAP[key]) == 3, (
            f"ALGO_IMPACT_MAP['{key}'] must be a 3-tuple. CTX-01 / D-01."
        )


def test_classify_finding_matches_codesign_via_check_id():
    """CTX-03 / A1: _classify_finding({'check_id': 'CODESIGN_EXPIRY', ...}) == 'CODESIGN_EXPIRY'.

    Requirement: CTX-03 / Research Assumption A1 — codesign-expiry findings are
    matched via their check_id field (not title/description text matching).
    """
    finding = {
        "severity": "HIGH",
        "title": "Code-signing certificate expired: CN=test",
        "description": "The certificate expired.",
        "check_id": "CODESIGN_EXPIRY",
    }
    result = _classify_finding(finding)
    assert result == "CODESIGN_EXPIRY", (
        f"_classify_finding returned '{result}', expected 'CODESIGN_EXPIRY'. "
        "CTX-03 / A1: check_id route must match codesign-expiry findings."
    )


def test_build_top_risks_unpacks_three_tuple():
    """CTX-01: _build_top_risks (via build_exec_content) handles 3-tuple without ValueError.

    Requirement: CTX-01 / D-01 — after ALGO_IMPACT_MAP extended to 3-tuple, all
    internal unpacks must be updated so build_exec_content still runs cleanly.
    """
    score_raw = _make_score_raw(rating="FAIR")
    findings = [_make_rsa_finding(severity="CRITICAL")]

    # Should not raise ValueError: "too many values to unpack"
    result = build_exec_content(
        score_raw=score_raw,
        findings=findings,
        roadmap_items=[],
    )
    assert result.top_risks, (
        "build_exec_content with an RSA CRITICAL finding must produce at least one "
        "RiskItem — _build_top_risks must successfully unpack the 3-tuple. CTX-01."
    )


def test_fallback_quantum_risk_is_nonempty():
    """CTX-01: FALLBACK_QUANTUM_RISK is a non-empty string.

    Requirement: CTX-01 / 99-UI-SPEC.md §Field Name Contract — fallback copy must
    be defined for findings with no crypto-class match.
    """
    assert isinstance(FALLBACK_QUANTUM_RISK, str) and FALLBACK_QUANTUM_RISK.strip(), (
        "FALLBACK_QUANTUM_RISK must be a non-empty string. CTX-01."
    )
