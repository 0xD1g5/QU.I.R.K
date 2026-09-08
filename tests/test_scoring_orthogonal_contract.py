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

# Phase 188 SCORE-06: one representative protocol_counts literal per
# assessed-predicate (KERBEROS for identity_trust, POSTGRESQL for
# data_at_rest, KAFKA-PLAIN for data_in_motion; hygiene/modern_tls/agility
# are assessed by endpoints > 0 alone) so every category in this fixture is
# ASSESSED. A "clean" category must score 25 because it WAS assessed and
# found nothing wrong -- orthogonal to other categories' problems -- not
# because it was silently excluded as unassessed (which would make this
# test vacuously pass by asserting None == 25, a failure, not a pass).
_ALL_ASSESSED_PROTOCOL_COUNTS = {"KERBEROS": 1, "POSTGRESQL": 1, "KAFKA-PLAIN": 1}


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
        "protocol_counts": dict(_ALL_ASSESSED_PROTOCOL_COUNTS),
    }
    # data_in_motion uses motion_email_plaintext_num which folds into
    # motion_email_plaintext_count; supply the canonical key the scorer reads.
    if category == "data_in_motion":
        # scoring.py reads motion_email_plaintext_count + motion_email_starttls_missing_count
        evidence = {
            "motion_email_plaintext_count": 5,
            "totals": {"endpoints": 10, "findings": 5},
            "protocol_counts": dict(_ALL_ASSESSED_PROTOCOL_COUNTS),
        }
    # trigger_key may itself be "protocol_counts"-adjacent (none of the current
    # parametrizations are), but if trigger_key == "protocol_counts" in a future
    # addition it would clobber the assessed markers above -- merge defensively.
    if trigger_key == "protocol_counts" and isinstance(trigger_value, dict):
        evidence["protocol_counts"] = {**_ALL_ASSESSED_PROTOCOL_COUNTS, **trigger_value}

    result = compute_readiness_score(evidence)
    subscores = result["subscores"]

    assert result["domains_assessed"] == 6, (
        f"Fixture precondition failed: expected all 6 categories assessed, got "
        f"{result['domains_assessed']} (subscores={subscores}). The orthogonality "
        f"contract only means something when every category was actually assessed."
    )

    for clean_cat in clean_categories:
        assert subscores[clean_cat] == 25, (
            f"{clean_cat} must be 25 when only {category} has findings. "
            f"Got {subscores[clean_cat]}. Orthogonality contract violated."
        )


def test_severity_floor_caps_band_not_score():
    """Phase 184.4 D-03: the severity floor caps the BAND only, never the score.

    Executable form of "the floor caps the band, not the number" — this is what
    fails loudly if a future contributor "simplifies" `high_impact` per RESEARCH
    Pitfall 2, or moves the cap onto `total_score` instead of `rating`.

    Toggling `finding_severity_counts["CRITICAL"]` between 0 and 1, with every
    other evidence input fixed, must change `rating` (EXCELLENT -> FAIR) but
    leave `score` and every `subscores` value byte-identical.

    `findings` is fixed at 1000 so the pre-existing `high_impact` /
    `agility_high_impact_ratio` ratio contribution (D-03) from a single
    CRITICAL rounds to zero (`-1/1000 * 14.0 = -0.014`, clamped/rounded away)
    — isolating the band-cap mechanism under test from that ratio's own,
    intentional, much smaller effect on the number. This is not evading D-03;
    it is testing D-01's "the cap moves the band, not the number" claim
    directly, without also re-proving D-03's separate (and already-covered)
    "the ratio moves the number a little" claim in the same assertion.
    """
    base_evidence = {
        "totals": {"endpoints": 10, "findings": 1000},
        "finding_severity_counts": {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        },
    }

    uncapped = compute_readiness_score(base_evidence)
    assert uncapped["rating"] == "EXCELLENT", (
        f"Fixture precondition failed: expected EXCELLENT with zero CRITICAL, "
        f"got {uncapped['rating']!r} (score {uncapped['score']})."
    )
    assert uncapped["rating_cap_reason"] is None

    capped_evidence = {
        "totals": {"endpoints": 10, "findings": 1000},
        "finding_severity_counts": {
            "CRITICAL": 1,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        },
    }
    capped = compute_readiness_score(capped_evidence)

    assert capped["rating"] == "FAIR", (
        f"Expected the CRITICAL=1 case to cap to FAIR per D-02, got {capped['rating']!r}."
    )
    assert capped["rating"] != uncapped["rating"], (
        "Toggling CRITICAL 0->1 must change the emitted rating."
    )
    assert capped["score"] == uncapped["score"], (
        "D-01/D-03 violated: the numeric score moved when only the band should "
        f"have capped. uncapped={uncapped['score']} capped={capped['score']}."
    )
    assert capped["subscores"] == uncapped["subscores"], (
        "D-01/D-03 violated: a subscore moved when only the band should have "
        f"capped. uncapped={uncapped['subscores']} capped={capped['subscores']}."
    )
    assert capped["rating_cap_reason"] and "FAIR" in capped["rating_cap_reason"]
