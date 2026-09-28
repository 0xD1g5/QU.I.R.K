"""Property test: compute_readiness_score() always returns score in [0, 100], or
None when zero domains were assessed.

Uses seeded random.Random(42) for 1,000 randomised evidence dicts.
Per CONTEXT.md D-03.

Phase 188 SCORE-06: this fixture's evidence dict never populates any DAR/
identity/motion protocol_counts keys, so those three categories are always
unassessed here; when `endpoints == 0` too, ALL six categories are unassessed
and `compute_readiness_score()` now returns `score=None` / `rating=
"NOT_ASSESSED"` (the locked "never fabricate 0/100" edge case) instead of a
numeric score. The bound check below allows that explicit not-computed
sentinel in addition to the numeric range.

Phase 211 plan 01 (DENOM-04 sub-item 3): the second class of test in this file
locks the 25-point-per-category clamp's SATURATION behaviour on the live
reference estate (`quirk-output/intelligence-20260928-014244.json`), measured
2026-09-28. This is a pinned-oracle regression instrument, not a property
test over randomised input -- it exists so a future change to the clamp
ceiling or to any category's weighted-impact math cannot silently start (or
stop) absorbing real signal without a test going red. See
`211-DENOM-EVIDENCE.md` for the red-proof output.
"""
from __future__ import annotations

import inspect
import json
import random
from pathlib import Path

import pytest

import quirk.intelligence.scoring as scoring
from quirk.intelligence.scoring import compute_readiness_score

_EVIDENCE_KEYS = [
    "plaintext_http_count",
    "http_on_tls_port_count",
    "mtls_present_count",
    "identity_weak_etype_count",
    "saml_weak_signing_count",
    "dnssec_weak_algo_count",
    "dar_db_plaintext_count",
    "dar_db_weak_ssl_count",
    "dar_storage_unencrypted_count",
    "dar_storage_aws_managed_count",
    "dar_k8s_unencrypted_count",
    "dar_k8s_inaccessible_count",
    "dar_vault_weak_count",
    "motion_email_plaintext_count",
    "motion_email_starttls_missing_count",
    "motion_email_weak_cipher_count",
    "motion_broker_plaintext_count",
    "motion_broker_weak_tls_count",
    "motion_broker_weak_cipher_count",
]


def _random_evidence(rng: random.Random) -> dict:
    endpoints = rng.randint(0, 200)
    findings = rng.randint(0, 500)
    protocol_counts = {
        "TLS": rng.randint(0, endpoints),
        "SSH": rng.randint(0, max(0, endpoints - 10)),
        "UNKNOWN": rng.randint(0, 50),
        "LOW": rng.randint(0, findings),
    }
    sev = {
        "HIGH": rng.randint(0, findings),
        "CRITICAL": rng.randint(0, findings // 2 if findings else 0),
        "LOW": rng.randint(0, findings),
    }
    ev: dict = {
        "totals": {"endpoints": endpoints, "findings": findings},
        "protocol_counts": protocol_counts,
        "finding_severity_counts": sev,
        "scan_error": {"rate": rng.uniform(0.0, 1.0)},
        "certificate_observations": {
            "expired_count": rng.randint(0, 50),
            "expiring_count": rng.randint(0, 50),
            "self_signed_count": rng.randint(0, 50),
        },
        "cert_key_type_counts": {
            "RSA": rng.randint(0, 100),
            "ECDSA": rng.randint(0, 100),
        },
    }
    for key in _EVIDENCE_KEYS:
        ev[key] = rng.randint(0, max(1, endpoints))
    return ev


def test_score_always_bounded_1000_iterations():
    rng = random.Random(42)
    for i in range(1_000):
        ev = _random_evidence(rng)
        result = compute_readiness_score(ev)
        score = result["score"]
        assert score is None or 0 <= score <= 100, (
            f"Iteration {i}: score={score} out of bounds. "
            f"evidence snapshot: endpoints={ev['totals']['endpoints']}"
        )
        if score is None:
            assert result["domains_assessed"] == 0
            assert result["rating"] == "NOT_ASSESSED"


# --- Clamp saturation on the live reference estate (Phase 211 plan 01) -----

_REFERENCE_ARTIFACT = (
    Path(__file__).resolve().parent.parent
    / "quirk-output"
    / "intelligence-20260928-014244.json"
)

# Category call order inside compute_readiness_score() -- the ONLY available
# discriminator for matching a captured _apply_weighted_impacts() call to its
# category, since the spy sees positional impacts lists, not category names.
# Established by the six `_apply_weighted_impacts(...)` call sites read at
# quirk/intelligence/scoring.py:485 (hygiene), :492 (modern_tls), :510
# (identity_trust), :565 (agility), :576 (dar), :600 (motion) -- in that
# source order. If a future edit reorders these calls, this list must be
# updated to match, and the length assertion below will at least catch a
# category being added or removed (though not a same-length reorder).
_CATEGORY_CALL_ORDER = [
    "hygiene",
    "modern_tls",
    "identity_trust",
    "agility",
    "dar",
    "motion",
]

# Pinned oracles measured directly against the reference estate on
# 2026-09-28 via the spy technique below. Tolerance 0.05 per D-05. These are
# NOT the CONTEXT.md planning-time hypotheses copied verbatim -- they are
# this plan's own re-measurement, which happened to match those hypotheses
# to four decimal places (see 211-DENOM-EVIDENCE.md for the side-by-side).
_PINNED_PRE_CLAMP_TOTALS = {
    "hygiene": 16.9306,
    "modern_tls": 16.8347,
    "identity_trust": 8.9191,
    "agility": 36.5918,
    "dar": 22.4242,
    "motion": 13.2079,
}
_TOLERANCE = 0.05


def _capture_pre_clamp_totals(monkeypatch, evidence: dict) -> dict[str, float]:
    """Spy on _apply_weighted_impacts to recover each category's pre-clamp
    total (score_cap + sum(impacts)) without altering its behaviour."""
    captured: list[list[tuple[str, float]]] = []
    real_fn = scoring._apply_weighted_impacts
    cap = inspect.signature(real_fn).parameters["score_cap"].default

    def spy(impacts, score_cap=cap):
        captured.append(list(impacts))
        return real_fn(impacts, score_cap)

    monkeypatch.setattr(scoring, "_apply_weighted_impacts", spy)

    result = scoring.compute_readiness_score(evidence)

    assert len(captured) == len(_CATEGORY_CALL_ORDER), (
        f"Expected {len(_CATEGORY_CALL_ORDER)} _apply_weighted_impacts calls "
        f"(one per category), got {len(captured)}. A category was added or "
        f"removed from compute_readiness_score() -- update "
        f"_CATEGORY_CALL_ORDER."
    )

    totals = {}
    for name, impacts in zip(_CATEGORY_CALL_ORDER, captured):
        totals[name] = cap + sum(v for _, v in impacts)
    return totals, result


def test_agility_ceiling_saturates_on_reference_estate(monkeypatch):
    """The 25-point clamp on Agility absorbs real signal on the reference
    estate: the pre-clamp total exceeds the cap, and the emitted subscore is
    pinned at exactly the cap. This is the exact insensitivity this
    milestone exists to remove -- P7a already tracks it (see
    211-DENOM-EVIDENCE.md's ownership check)."""
    if not _REFERENCE_ARTIFACT.exists():
        pytest.skip(f"reference artifact not on disk: {_REFERENCE_ARTIFACT}")

    evidence = json.loads(_REFERENCE_ARTIFACT.read_text())["evidence_summary"]
    totals, result = _capture_pre_clamp_totals(monkeypatch, evidence)

    cap = inspect.signature(scoring._apply_weighted_impacts).parameters[
        "score_cap"
    ].default

    # Ceiling saturation: Agility's pre-clamp total exceeds the cap, and the
    # emitted subscore is pinned at exactly the cap.
    assert totals["agility"] > cap, (
        f"Expected Agility pre-clamp total to exceed the {cap} cap "
        f"(ceiling saturation); measured {totals['agility']}"
    )
    assert result["subscores"]["agility_signals"] == int(cap), (
        f"Expected Agility's emitted subscore to be pinned at the cap "
        f"({int(cap)}); got {result['subscores']['agility_signals']}"
    )

    # No category floors (pre-clamp total below 0.0) on this estate --
    # asserted per-category against pinned absolute values, not aggregate.
    for name, expected in _PINNED_PRE_CLAMP_TOTALS.items():
        measured = totals[name]
        assert measured >= 0.0, (
            f"{name} pre-clamp total {measured} is below the floor (0.0) on "
            f"the reference estate -- floor engagement was not expected."
        )
        assert abs(measured - expected) <= _TOLERANCE, (
            f"{name} pre-clamp total drifted: measured {measured}, pinned "
            f"oracle {expected} (tolerance {_TOLERANCE}). If this is a "
            f"genuine measurement change, update the pinned oracle and "
            f"record the drift as a finding -- do not silently widen the "
            f"tolerance."
        )

    # Hygiene and Modern TLS are NOT saturated at either clamp boundary --
    # the pinned oracle that keeps the 17-vs-18 divergence (Hygiene/Modern
    # TLS specifically) from later being misattributed to a clamp effect.
    for name in ("hygiene", "modern_tls"):
        measured = totals[name]
        assert 1.0 < measured < (cap - 1.0), (
            f"{name} pre-clamp total {measured} is within rounding distance "
            f"of a clamp boundary (0 or {cap}) -- this would make the clamp "
            f"a plausible explanation for the 17-vs-18 divergence, which "
            f"the discriminator in 211-CONTEXT.md rules out on other "
            f"grounds. Re-examine before trusting this oracle."
        )
