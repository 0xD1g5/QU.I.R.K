"""999.113 — readiness-score ratio denominator semantics.

Decision: ``.planning/decisions/999.113-denominator-semantics.md`` (D1-D5).
Todo: ``.planning/todos/pending/readiness-score-denominator-is-probe-count-not-assessable-endpoints.md``.

Pre-fix, every ``_ratio(...)`` call in ``compute_readiness_score()`` except
``agility_high_impact_ratio`` divided by ``totals.endpoints`` -- a PROBE
count (hosts x probed ports) that grows with how hard a scan looks, not with
how bad the infrastructure is. Two evidence dicts differing ONLY in
``totals.endpoints`` produced DIFFERENT scores under that code (documented:
89 vs 91 on identical infrastructure, ports_tls widened 2 -> 10 ports).

Post-fix, every ratio divides by the population its own numerator is drawn
from (certs_observed for certificate ratios, assessable_endpoint_count for
endpoint ratios, a non-INFO finding count for the high-impact-findings
ratio) -- none of which is ``totals.endpoints``. This test asserts the
DIRECT consequence: the score becomes INDEPENDENT of ``totals.endpoints``
when every other evidence field is held fixed.

Red-proofed per Phase 205-04's precedent: commit
``TEMPORARY(999.113): induce red-proof — REVERTED IN THE NEXT COMMIT``
reverted the denominator change, ran this test, captured the real failure
message, then reverted the revert. See ``999.113-SUMMARY.md`` (or the
executor's final report, if no SUMMARY exists yet) for the captured
transcript.
"""
from __future__ import annotations

import copy

from quirk.intelligence.scoring import compute_readiness_score


def _multihost_evidence() -> dict:
    """The recorded 31-host deliberately-vulnerable chaos-lab estate
    (999.113 decision doc / todo, measured 2026-09-13). Certificate and
    severity counts are the exact recorded values; endpoint-adjacent
    per-field counts (plaintext_http_count, http_on_tls_port_count,
    protocol_counts UNKNOWN, cert_key_type_counts) are reconstructed
    approximations since the raw evidence.json was not preserved -- the
    approximation does not affect what THIS test proves, which is
    denominator independence from totals.endpoints, not a specific pinned
    score.
    """
    return {
        "totals": {"endpoints": 370, "findings": 5 + 14 + 33 + 16 + 330},
        "protocol_counts": {
            "TLS": 40, "HTTP": 5, "SSH": 3, "UNKNOWN": 2,
            "POSTGRESQL": 1, "S3": 1, "KUBERNETES": 1, "VAULT": 1,
            "KERBEROS": 1, "SAML": 1, "DNSSEC": 1,
            "SMTP-STARTTLS": 1, "KAFKA-TLS": 1,
        },
        "assessable_endpoint_count": 38,
        "plaintext_http_count": 6,
        "http_on_tls_port_count": 3,
        "mtls_present_count": 0,
        "cert_key_type_counts": {"RSA": 0, "ECDSA": 0},
        "certificate_observations": {
            "certs_observed": 17,
            "expired_count": 5,
            "expiring_count": 1,
            "self_signed_count": 3,
        },
        "scan_error": {"count": 0, "rate": 0.0},
        "finding_severity_counts": {
            "CRITICAL": 5, "HIGH": 14, "MEDIUM": 33, "LOW": 16, "INFO": 330,
        },
    }


def test_score_is_independent_of_totals_endpoints_when_everything_else_is_fixed():
    """999.113 D1/D2 red-proof.

    Two evidence dicts, identical in every field EXCEPT ``totals.endpoints``
    (370 vs 1000 -- an arbitrarily larger probe count, simulating a deeper
    scan of the SAME infrastructure), must produce the IDENTICAL score and
    IDENTICAL subscores. `totals.endpoints` does not feed any `_ratio(...)`
    denominator anymore (assessable_endpoint_count / certs_observed / a
    non-INFO finding count do) -- widening it must be a pure no-op.

    Pre-999.113 this failed: `denom = totals.endpoints` fed 34 of the 35
    ratio sites directly, so widening it diluted every real weakness
    proportionally and raised the score.
    """
    small = _multihost_evidence()
    large = copy.deepcopy(small)
    large["totals"]["endpoints"] = 1000

    result_small = compute_readiness_score(small)
    result_large = compute_readiness_score(large)

    assert result_small["score"] == result_large["score"], (
        f"score moved from {result_small['score']} to {result_large['score']} "
        "when ONLY totals.endpoints changed -- a ratio denominator is still "
        "reading totals.endpoints somewhere."
    )
    assert result_small["subscores"] == result_large["subscores"], (
        f"subscores diverged: {result_small['subscores']} vs "
        f"{result_large['subscores']} when ONLY totals.endpoints changed."
    )


def test_multihost_estate_scores_materially_below_the_old_headline():
    """999.113 acceptance criterion 1 -- direction, on bad infrastructure.

    Pinned to the real fixture's post-fix numbers so a future regression
    (e.g. someone re-widening a denominator back to totals.endpoints) trips
    this test even if the independence test above is somehow satisfied by
    coincidence. Documented pre-fix headline for this estate: 91/100,
    Identity 25/25 (29% of certificates expired). Post-fix: score must drop
    materially below 91 and Identity must move off the 25/25 ceiling.
    """
    result = compute_readiness_score(_multihost_evidence())

    assert result["score"] < 91, (
        f"score {result['score']} did not move materially below the "
        "documented pre-fix headline of 91 on a 31-host deliberately "
        "vulnerable estate (5 CRITICAL / 14 HIGH / 33 MEDIUM findings, "
        "29% expired certificates)."
    )
    assert result["subscores"]["identity_trust"] < 25, (
        f"identity_trust subscore is still {result['subscores']['identity_trust']}"
        "/25 despite 5 of 17 (29%) certificates being expired -- the "
        "certificate-ratio denominator fix did not take effect."
    )


def test_high_impact_ratio_denominator_excludes_info_findings():
    """999.113 D1(d) -- found during implementation by arithmetic, not by
    inspection. `agility_high_impact_ratio` divided high-impact
    (HIGH+CRITICAL) findings by `totals.findings`, which INCLUDES INFO --
    scaling with scan depth the same way `totals.endpoints` did. Post-fix it
    divides by the non-INFO (CRITICAL+HIGH+MEDIUM+LOW) finding count.

    This is isolated from the certificate/endpoint fixes above by holding
    `totals.findings`'s actionable component fixed and only growing INFO.
    """
    few_info = _multihost_evidence()
    few_info["totals"]["findings"] = 5 + 14 + 33 + 16 + 5  # 5 INFO, not 330
    few_info["finding_severity_counts"]["INFO"] = 5

    many_info = _multihost_evidence()  # 330 INFO, as recorded

    result_few = compute_readiness_score(few_info)
    result_many = compute_readiness_score(many_info)

    assert result_few["subscores"]["agility_signals"] == result_many["subscores"]["agility_signals"], (
        f"agility_signals subscore moved ({result_few['subscores']['agility_signals']} vs "
        f"{result_many['subscores']['agility_signals']}) when ONLY the INFO finding count "
        "changed -- the high-impact-findings ratio is still dividing by a "
        "denominator that includes INFO findings."
    )
