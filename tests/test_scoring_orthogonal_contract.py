"""Phase 88 D-02 / EVIDENCE-TALLY-01: Orthogonal subscore contract forward-locking invariant.

Resolved correct-by-design. The scoring model (quirk/intelligence/scoring.py) assigns each
of the six subscores independently: subscore = 25 + sum(category_local_penalties), clamped
[0, 25]. A category with no findings of its own type scores 25/25 regardless of findings in
other categories. Cross-category penalties are explicitly rejected (Phase 88 D-01).

EVIDENCE-TALLY-01 resolution: won't-fix at the subscore level.
This is consistent with the scoring model as defined throughout the application — the model
uses _apply_weighted_impacts(impacts, score_cap=25.0) where each category's impacts list
contains ONLY that category's signals. A clean category such as 'hygiene' will score 25/25
even when CRITICAL/HIGH findings exist in 'modern_tls', 'identity_trust', or other categories.
Forcing cross-category penalties would contradict the architecture and is explicitly rejected
per Phase 88 D-01.

This parametrized test suite forward-locks that contract in perpetuity.
"""
from __future__ import annotations

import pytest
from quirk.intelligence.scoring import compute_readiness_score


@pytest.mark.parametrize("category,trigger_key,trigger_value,clean_categories", [
    (
        "hygiene",
        "plaintext_http_count",
        10,
        ["modern_tls", "identity_trust", "agility_signals", "data_at_rest", "data_in_motion"],
    ),
    (
        "modern_tls",
        "finding_severity_counts",
        {"LOW": 5},
        ["hygiene", "identity_trust", "agility_signals", "data_at_rest", "data_in_motion"],
    ),
    (
        "identity_trust",
        "identity_weak_etype_count",
        5,
        ["hygiene", "modern_tls", "agility_signals", "data_at_rest", "data_in_motion"],
    ),
    (
        "agility_signals",
        "cert_key_type_counts",
        {"RSA": 10},
        ["hygiene", "modern_tls", "identity_trust", "data_at_rest", "data_in_motion"],
    ),
    (
        "data_at_rest",
        "dar_db_plaintext_count",
        5,
        ["hygiene", "modern_tls", "identity_trust", "agility_signals", "data_in_motion"],
    ),
    (
        "data_in_motion",
        "motion_email_plaintext_num",
        5,
        ["hygiene", "modern_tls", "identity_trust", "agility_signals", "data_at_rest"],
    ),
])
def test_subscore_orthogonality(category, trigger_key, trigger_value, clean_categories):
    """Forward-locking invariant: a finding in one category only affects that category's subscore."""
    evidence: dict = {
        trigger_key: trigger_value,
        "totals": {"endpoints": 10, "findings": 5},
    }
    # data_in_motion uses motion_email_plaintext_num which folds into
    # motion_email_plaintext_count; supply the canonical key the scorer reads.
    if category == "data_in_motion":
        # scoring.py reads motion_email_plaintext_count + motion_email_starttls_missing_count
        evidence = {
            "motion_email_plaintext_count": 5,
            "totals": {"endpoints": 10, "findings": 5},
        }

    result = compute_readiness_score(evidence)
    subscores = result["subscores"]

    for clean_cat in clean_categories:
        assert subscores[clean_cat] == 25, (
            f"{clean_cat} must be 25 when only {category} has findings. "
            f"Got {subscores[clean_cat]}. Orthogonality contract violated."
        )
