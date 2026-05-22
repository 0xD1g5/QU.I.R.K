"""Phase 86 Plan 01 — Scoring normalization boundary tests (RED gate).

Tests assert the correct post-fix behavior for SCORE-FIX-01 / SCORE-FIX-03:
  - All subscores at 25  → overall = 100 (int(round(150/1.5))), EXCELLENT
  - All subscores at 0   → overall = 0 (int(round(0/1.5))),     POOR
  - Canonical 25+25+23+3+25+19 = 120 → overall = 80 (int(round(120/1.5))), GOOD

D-09: These tests MUST initially fail against the unmodified scoring.py because
the clamp at 100 returns 100 for the canonical example (sum=120 → clamped 100)
instead of the correct normalized value of 80.

Cite: CONTEXT.md D-09, D-01.
"""
from __future__ import annotations

import pytest

from quirk.intelligence.scoring import compute_readiness_score, _rating


# ---------------------------------------------------------------------------
# Evidence fixtures
# ---------------------------------------------------------------------------

def _max_subscore_evidence() -> dict:
    """Empty evidence — all counters default to zero, all ratios zero,
    no negative impacts ⇒ _apply_weighted_impacts returns score_cap=25 per category.
    Result: all six subscores = 25, sum = 150 → int(round(150/1.5)) = 100, EXCELLENT.
    """
    return {}


def _zero_subscore_evidence() -> dict:
    """Evidence that drives every subscore to 0.

    Each category's negative impacts must exceed score_cap=25.  Setting
    endpoints=1 and all finding/defect counters to 1 maximizes each per-ratio
    penalty at the full weight value, sinking every subscore below 0 (then
    clamped to 0 by _apply_weighted_impacts).
    """
    return {
        "totals": {"endpoints": 1, "findings": 100},
        "scan_error": {"rate": 1.0},
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 1,
        "protocol_counts": {"UNKNOWN": 100},
        "finding_severity_counts": {"HIGH": 100, "CRITICAL": 100, "LOW": 100},
        "certificate_observations": {
            "expired_count": 1,
            "expiring_count": 1,
            "self_signed_count": 1,
        },
        "mtls_present_count": 0,
        "cert_key_type_counts": {"RSA": 1, "ECDSA": 0},
        "identity_weak_etype_count": 1,
        "saml_weak_signing_count": 1,
        "dnssec_weak_algo_count": 1,
        "smime_weak_signing_count": 1,
        "smime_expired_count": 1,
        "smime_weak_key_count": 1,
        "adcs_weak_template_count": 1,
        "adcs_misconfig_count": 1,
        "adcs_weak_signing_count": 1,
        "adcs_coverage_gap_count": 1,
        "dar_db_plaintext_count": 1,
        "dar_db_weak_ssl_count": 1,
        "dar_storage_unencrypted_count": 1,
        "dar_storage_aws_managed_count": 1,
        "dar_k8s_unencrypted_count": 1,
        "dar_k8s_inaccessible_count": 1,
        "dar_vault_weak_count": 1,
        "motion_email_plaintext_count": 1,
        "motion_email_starttls_missing_count": 1,
        "motion_email_weak_cipher_count": 1,
        "motion_broker_plaintext_count": 1,
        "motion_broker_weak_tls_count": 1,
        "motion_broker_weak_cipher_count": 1,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_overall_score_max_when_all_subscores_at_25():
    """All six subscores at 25 → overall must be exactly 100, rating EXCELLENT.

    With no negative evidence, _apply_weighted_impacts returns score_cap=25 for
    each category.  Under the normalized formula int(round(150/1.5)) = 100.
    """
    result = compute_readiness_score(_max_subscore_evidence())
    subscores = result["subscores"]

    # Verify the premise: all subscores really are 25
    for category, val in subscores.items():
        assert val == 25, (
            f"Expected subscore {category}=25 for empty evidence, got {val}"
        )

    assert result["score"] == 100, (
        f"Expected overall=100 when all subscores=25 (sum=150 → int(round(150/1.5))), "
        f"got {result['score']}"
    )
    assert result["rating"] == "EXCELLENT", (
        f"Expected EXCELLENT for score 100, got {result['rating']}"
    )


def test_overall_score_zero_when_all_subscores_zero():
    """All six subscores at 0 → overall must be exactly 0, rating POOR.

    Under the normalized formula int(round(0/1.5)) = 0.
    """
    result = compute_readiness_score(_zero_subscore_evidence())
    subscores = result["subscores"]

    # Verify the premise: all subscores really are 0
    for category, val in subscores.items():
        assert val == 0, (
            f"Expected subscore {category}=0 for max-penalty evidence, got {val}"
        )

    assert result["score"] == 0, (
        f"Expected overall=0 when all subscores=0, got {result['score']}"
    )
    assert result["rating"] == "POOR", (
        f"Expected POOR for score 0, got {result['rating']}"
    )


def test_overall_score_canonical_example_120_to_80(monkeypatch):
    """Canonical live-dashboard subscores 25+25+23+3+25+19=120 → overall=80, GOOD.

    D-09: This test exercises the REAL compute_readiness_score aggregator end-to-end
    by monkeypatching quirk.intelligence.scoring._apply_weighted_impacts to return
    the exact canonical (subscore, drivers) tuples, confirming the aggregation
    formula — NOT just arithmetic identity.

    Before the fix (clamp): int(min(120, 100)) = 100, EXCELLENT  ← FAILS this test
    After the fix (normalize): int(round(120 / 1.5)) = 80, GOOD  ← PASSES

    Canonical source: 2026-05-22 live dashboard scan (CONTEXT.md D-01).
    """
    # The canonical subscores from the live bug report (in call order within
    # compute_readiness_score): hygiene=25, modern_tls=25, identity_trust=23,
    # agility=3, dar=25, data_in_motion=19.
    canonical_subscores = [25, 25, 23, 3, 25, 19]
    call_index = [0]  # mutable cell for closure

    def _patched_apply(impacts, score_cap=25.0):
        idx = call_index[0]
        call_index[0] += 1
        return (canonical_subscores[idx], [])

    import quirk.intelligence.scoring as scoring_module
    monkeypatch.setattr(scoring_module, "_apply_weighted_impacts", _patched_apply)

    result = compute_readiness_score({})

    assert result["score"] == 80, (
        f"Canonical sum 25+25+23+3+25+19=120: expected int(round(120/1.5))=80, "
        f"got {result['score']}. "
        f"If this returns 100, the broken clamp is still in effect."
    )
    assert result["rating"] == "GOOD", (
        f"Expected GOOD for score 80, got {result['rating']}"
    )
