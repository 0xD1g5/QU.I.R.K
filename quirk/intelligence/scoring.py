from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from quirk.severity_bands import (
    BAND_THRESHOLDS,
    band_for_score,
    cap_band_for_severity,
    cap_reason,
)

# Phase 188 SCORE-06 — scoring formula version marker. Bumped whenever the
# aggregation shape changes (exclude-and-rescale replaces the fixed / 1.5
# rollup). NO back-migration of stored historical scores (CONTEXT.md locked
# decision) — this marker lets every report surface disclose that scores from
# different scoring versions are not comparable to each other.
#
# 999.115 bumped this 2.0 -> 3.0, and the bump is not bookkeeping: it is the
# mechanism that makes the change honest. Six model changes landed together and
# every one of them moves the number on every estate the product has ever
# scored — the 31-host reference estate went 87 -> 18. The reference ladder
# moved R2 95 -> 78, R3 91 -> 46, R4 85 -> 24.
#
# It is also what discharges Phase 184.4 D-03's second argument for capping the
# band rather than the number. D-03 valued comparability across scans and was
# right to; 999.115 supersedes it by DISCLOSING the discontinuity rather than
# avoiding it forever, which is the honest form of the same concern. See
# .planning/decisions/999.115-severity-caps-the-number-supersedes-184.4-D-03.md
#
# Phase 234 (SCORE-09) bumped this 3.0 -> 4.0. Scoring 3.0 divided every
# weakness count by a population that grows with scan depth, so observing more
# HEALTHY endpoints raised the score while the absolute exposure stood still
# (P2b, 999.120). 4.0 makes three changes together:
#   - every ratio site is an absolute-count curve, `min(1, count / N_REF) **
#     0.5`, with N_REF = 40 as a CONTINUITY ANCHOR (the ladder skeleton
#     population, not a fitted value), so R1-R4 are unchanged at their own size
#     and only the dependence on estate size is removed. Small estates become
#     more lenient (O-3): 1 plaintext endpoint out of 1 scores hygiene 22, not 7;
#   - the scan-error terms read the scan-error COUNT, not its rate (D-03);
#   - classical certificate keys (RSA, ECDSA, EdDSA) are never a positive
#     signal: any of them costs a flat -8, and the single +8 PQC credit is
#     earned by a PQC/hybrid key exchange OR a PQC certificate key (D-04, O-2,
#     O-4).
# Kerberos placeholder rows also stop counting as identity evidence (D-11).
# The Phase 234 code review corrected three 4.0 rules before release (so the
# version stays 4.0; no 4.0 score has shipped): the mTLS bonus is a presence
# credit, not a count curve (D-28); the "key types undetermined" -8 applies
# whenever undetermined certificates exist, independent of PQC (D-29); and
# Kerberos rows carrying a scan error are not identity evidence (D-30).
# Decision record: .planning/decisions/234-p2b-fix-and-ladder-remeasurement.md
SCORING_VERSION = "4.0"
SCORING_VERSION_NOTE = "scoring v4 — not comparable with v3 or earlier scores"

# Phase 188 SCORE-06 / plan 188-03: the once-composed not-computed statement
# lives in quirk.reports.content_model, NOT here — html_renderer.py,
# docx_renderer.py, and technical.py are firewalled from ever importing this
# module (tests/test_cve_score_guard.py's ADVISORY-01 / T-156-04 / T-157-05 /
# T-160-04 / T-161-22 gates), so a constant those renderers must read cannot
# live in quirk.intelligence.scoring. See content_model.NOT_COMPUTED_STATEMENT.

# Phase 188 SCORE-06 RQ-1 — the email/broker data-in-motion protocol literals
# that quirk/intelligence/evidence.py's _PROTOCOL_KEYS was widened to count
# (same phase). This tuple is asserted to be a subset of evidence._PROTOCOL_KEYS
# by tests/test_score_coverage_disclosure.py so the two lists cannot drift
# apart silently.
_MOTION_PROTOCOL_KEYS: Tuple[str, ...] = (
    "SMTP-STARTTLS", "SMTPS", "IMAPS", "IMAP-STARTTLS", "POP3S", "POP3-STARTTLS",
    "KAFKA-PLAIN", "KAFKA-TLS", "AMQP-PLAIN", "AMQPS", "AMQPS/AZURE-SERVICEBUS",
    "HTTPS/AWS-SQS", "REDIS-PLAIN", "REDIS-TLS",
)

# Phase 188 SCORE-06 — the DAR protocol literals data_at_rest's assessed-predicate
# reads. All 7 were already present in _PROTOCOL_KEYS before this phase.
_DAR_PROTOCOL_KEYS: Tuple[str, ...] = (
    "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES", "VAULT",
)

# Phase 188 SCORE-06 — the non-certificate identity protocol literals identity_trust's
# assessed-predicate reads, in addition to certs_observed > 0.
# 188 review WR-01: SMIME and ADCS added — the identity subscore penalizes six
# smime_* and four adcs_* counters, and ADCS ESC/coverage-gap rows carry no
# cert_not_after (certs_observed stays 0), so an SMIME/ADCS-only scan was
# falsely marked unassessed and its computed penalties silently discarded.
_IDENTITY_PROTOCOL_KEYS: Tuple[str, ...] = ("KERBEROS", "SAML", "DNSSEC", "SMIME", "ADCS")

# SCORE_WEIGHTS invariant (D-04, WR-06 — Phase 73 documentation, NOT normalization)
# ----------------------------------------------------------------------------
# These values are ABSOLUTE per-ratio coefficients, NOT probabilities, NOT
# a normalized PMF. Their sum is 275.0 BY DESIGN (Phase 83 rebalance).
#
# Scoring contract (v4.10.1, Phase 86 D-01; rescale updated Phase 188 SCORE-06):
#   Each of the six categories is scored on a 0-25 scale via
#   `_apply_weighted_impacts(impacts, score_cap=25.0)`.  A category with no
#   evidence to assess (zero endpoints, zero DAR/motion protocol counts, zero
#   identity signals -- see the `_*_assessed()` predicates below) is EXCLUDED
#   from the headline rather than contributing a full 25/25. The overall
#   readiness score is then exclude-and-rescale:
#       total_score = int(round(sum(assessed 0-25 subscores) / (domains_assessed * 25) * 100))
#   with `domains_assessed` derived from the same evidence counters this
#   function already reads (never a hand-maintained flag). When
#   domains_assessed == 0, `total_score` is None ("not computed") rather than
#   a fabricated 0 or 100 -- see the zero-assessed branch below. `_rating()`
#   is only invoked on a non-None score.
#
# Any contributor adding, removing, or modifying a weight value MUST update
# `tests/test_score_weights_invariant.py` to match the new expected sum.
# CI will fail loudly otherwise.
SCORE_WEIGHTS: Dict[str, float] = {
    "hygiene_plaintext_http_ratio": 18.0,
    "hygiene_http_on_tls_ratio": 16.0,
    "hygiene_scan_error_rate": 6.0,
    "modern_tls_legacy_versions_ratio": 14.0,
    "modern_tls_unknown_ratio": 6.0,
    "modern_tls_scan_error_rate": 5.0,
    "identity_expired_ratio": 14.0,
    "identity_expiring_ratio": 7.0,
    "identity_self_signed_ratio": 9.0,
    "identity_mtls_ratio_bonus": 6.0,
    "identity_kerberos_weak_etype_ratio": 10.0,
    "identity_saml_weak_signing_ratio": 8.0,
    "identity_dnssec_weak_algo_ratio": 8.0,
    "identity_smime_weak_signing_count": 2.0,   # Phase 79 SMIME-04
    "identity_smime_expired_count":      2.0,   # Phase 79 SMIME-04
    "identity_smime_weak_key_count":     2.0,   # Phase 79 SMIME-04
    "identity_adcs_weak_template_count": 2.0,   # Phase 80 ADCS-04
    "identity_adcs_misconfig_count":     2.0,   # Phase 80 ADCS-04
    "identity_adcs_weak_signing_count":  2.0,   # Phase 80 ADCS-04
    "identity_adcs_coverage_gap_count":  2.0,   # Phase 80 D-80-R6 / CONTEXT D-Area-1
    "dar_db_plaintext_ratio": 12.0,
    "dar_db_weak_ssl_ratio": 6.0,
    "dar_storage_unencrypted_ratio": 12.0,   # Phase 28 D-10 — same weight as plaintext DB
    "dar_storage_aws_managed_ratio": 4.0,    # Phase 28 D-10 — compliance gap, not active weakness
    "dar_vault_weak_ratio": 8.0,            # Phase 30 D-12 -- HIGH-only count for PKI/auth findings
    "dar_k8s_unencrypted_ratio": 10.0,        # Phase 29 — etcd plaintext is high-impact but
                                              # narrower scope than DB-wide plaintext
    "dar_k8s_inaccessible_ratio": 4.0,        # Phase 29 — same weight as storage compliance gap
    "motion_email_plaintext_ratio": 12.0,    # Phase 34 D-03 — email plaintext + STARTTLS-missing fold (D-01/D-02)
    "motion_email_weak_cipher_ratio": 6.0,   # Phase 34 D-03 — HIGH-only cipher (A5)
    "motion_broker_plaintext_ratio": 14.0,   # Phase 34 D-03 — KAFKA-PLAIN / AMQP-PLAIN / REDIS-PLAIN
    "motion_broker_weak_tls_ratio": 8.0,     # Phase 34 D-03 — TLSv1.0/1.1/SSLv3 on broker
    "motion_broker_weak_cipher_ratio": 6.0,  # Phase 34 D-03 — HIGH-only cipher (A5)
    "agility_unknown_ratio": 6.0,
    "agility_rsa_only_penalty": 8.0,
    # 999.115 P8 — certificates observed but NO key type determined for any of
    # them. This value is DERIVED, not chosen: it must be >=
    # agility_rsa_only_penalty, or the model rewards not looking. If failing to
    # determine a key type cost less than determining it and finding RSA, a
    # scan that gave up would outscore one that succeeded, and the perverse
    # incentive the P8 fix exists to remove would survive the fix. Equal
    # severity is the weakest value that removes it — an undetermined property
    # is treated as the worst case it could be, which is what a security
    # assessment should assume. Raising it above 8.0 is defensible; lowering it
    # is not. See tests/test_score_properties.py::test_p8_*.
    "agility_unverified_key_type_penalty": 8.0,
    # "agility_has_ecdsa_bonus" (4.0) was REMOVED by Phase 234 D-04/O-2:
    # ECDSA and EdDSA keys are quantum-vulnerable, so a classical key type is
    # never a positive signal. Removing the key (not zeroing it) follows the
    # 999.115 C precedent; tests/test_score_weights_invariant.py records it.
    "agility_pqc_hybrid_bonus": 8.0,   # Phase 90 PQC-03 — X25519MLKEM768 ceiling anchor
    "agility_weak_jwt_alg_ratio": 6.0,      # Phase 94 SCORE-01 — alg:none / quantum-vulnerable alg in bearer token
    "agility_openapi_plaintext_ratio": 4.0, # Phase 94 SCORE-01 — OpenAPI spec declares http:// servers
    "agility_codesign_weak_algo_ratio": 6.0,  # Phase 95 SCORE-01 — code-signing cert weak algo (RSA<2048/EC<256/SHA-1)
    "agility_fuzz_crypto_posture_ratio": 4.0,  # Phase 96 SCORE-01 — active REST fuzz CRITICAL/HIGH crypto-posture findings
}

PROFILE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "strict":   {"agility_": 1.4, "identity_": 1.4, "dar_": 1.4, "motion_": 1.4},
    "balanced": {"agility_": 1.0, "identity_": 1.0, "dar_": 1.0, "motion_": 1.0},
    "lenient":  {"agility_": 0.7, "identity_": 0.7, "dar_": 0.7, "motion_": 0.7},
}


def _as_int(v: Any) -> int:
    try:
        return int(v)
    except Exception:
        return 0


def _as_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


# 999.115 candidate D — the prevalence response curve.
#
# `penalty = ratio x weight` is LINEAR, so it treats 30%-of-certificates-expired
# as exactly six times worse than 5%. No consultant reads it that way: 5% is
# hygiene drift, 30% is an organisation that has lost control of its PKI. Alarm
# is steeply non-linear in prevalence; the model drew a straight line through
# the origin.
#
# Applying `ratio ** PREVALENCE_CURVE_EXPONENT` bends that line so low
# prevalence registers proportionally harder. Measured contributions, on the
# calibration ladder:
#   - it reduces SATURATION (subscores pinned at 0 or 25), keeping per-domain
#     numbers informative rather than flat — this was D's expected benefit
#   - it narrows, though does not eliminate, the P2b dilution effect whereby
#     observing more healthy endpoints improves the score without any change in
#     absolute exposure
#
# What D does NOT do, measured rather than assumed: it never fixes ladder
# monotonicity at any exponent, and it never moves R2 (a hygienically spotless
# but quantum-blind estate has no prevalence to curve). D is a refinement. The
# consequence ceiling is the fix.
#
# The exponent is insensitive across 0.4-0.6; 0.5 is the midpoint of that
# measured-stable range, not a tuned value.
#
# Phase 234 (scoring 4.0) keeps this exponent and curve family but changes the
# curve's INPUT from a prevalence ratio to an absolute count saturating at
# N_REF (see `_count_curve` below): the "it narrows the P2b dilution" note
# above is historical; 4.0 removes the dilution rather than narrowing it.
PREVALENCE_CURVE_EXPONENT: float = 0.5


# Phase 234 D-01 (scoring 4.0) — the curve's input is an ABSOLUTE COUNT.
#
# Under 3.0 every site was `(count / population) ** exponent`, and every
# population it divided by (assessable endpoints, observed certificates) grows
# with scan depth: observing more healthy endpoints shrank every ratio and
# raised the score while the estate's absolute exposure stood still (P2b,
# 999.120). The denominator is gone. A weakness count saturates at N_REF.
#
# N_REF is a CONTINUITY ANCHOR, not a fitted value (operator decision O-3). It
# is the calibration ladder's skeleton population (40 assessable endpoints and
# 40 certificates), so R1-R4 score exactly what they did under 3.0 at their own
# size and only the dependence on estate size is removed. Every N_REF from 5 to
# 100 keeps the ladder in its bands, because the ceilings dominate the emitted
# scores; that is why it is an operator anchor rather than a measurement. One
# constant serves both the endpoint and the certificate families.
#
# The consequence is accepted, and disclosed: small estates are more lenient.
# One plaintext endpoint out of one scores hygiene 22 under 4.0 (7 under 3.0).
N_REF: int = 40


def _count_curve(count: int) -> float:
    """`min(1, count / N_REF) ** PREVALENCE_CURVE_EXPONENT`; 0.0 for count <= 0."""
    if count <= 0:
        return 0.0
    return min(1.0, count / N_REF) ** PREVALENCE_CURVE_EXPONENT


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def _rating(score: int) -> str:
    """Numeric-only band lookup (Phase 184.4 D-01/D-04).

    This is now the NUMERIC-ONLY band: it reflects the score alone and knows
    nothing about severity. Severity-based capping (a CRITICAL finding
    floors the emitted band at FAIR) happens one layer up, in
    `compute_readiness_score()`, via `quirk.severity_bands.cap_band_for_severity()`.
    If you are looking for "why doesn't a CRITICAL finding change what this
    function returns", it doesn't — read `compute_readiness_score()` instead.
    """
    return band_for_score(score)


# ---------------------------------------------------------------------------
# 999.115 candidate C — ABSOLUTE CONSEQUENCE CEILING.
#
# The model before this was purely PREVALENCE-based: every penalty was
# `ratio x weight`, so five CRITICAL findings in a 17-host estate and five in a
# 500-host estate were treated as differently severe. No consultant reads them
# that way — the attacker needs one. Measured consequence: a 31-host estate
# built to be as bad as this product can detect scored 87/100, and the entire
# calibration ladder from "pristine and quantum-ready" to "purpose-built
# catastrophe" collapsed into the single band EXCELLENT across 15 points.
#
# This is NOT a new mechanism. `cap_band_for_severity()` already applies
# exactly this reasoning — an open CRITICAL floors the emitted BAND at FAIR
# regardless of prevalence. That compensation is what produced the incoherent
# "87 — FAIR": the word said one thing while the digits said EXCELLENT. C
# extends the existing idea from the band to the number, so the two agree.
#
# THE VALUES ARE DERIVED, NOT CHOSEN — with one exception. "Cap at POOR" IS
# `FAIR - 1`; "cap at FAIR" IS `MODERATE - 1`. Reading them out of
# BAND_THRESHOLDS rather than restating them as 34/54/69 means a future band
# rebalance moves these with it, and collapses the free-parameter count from
# four to one. The exception is DEEP_CRITICAL_CEILING below.
#
# Calibration provenance: the ladder in tests/test_score_properties.py, whose
# target bands were set by the operator on 2026-09-14 and supplied BLIND —
# each estate described in infrastructure terms with no score shown. Evidence
# and the full candidate comparison:
# .planning/decisions/999.115-scoring-model-candidate-measurements.md
#
# STANDING CAVEAT, do not lose it: the ladder has five rungs, four of them
# synthetic. Fitting even one parameter to five observations is weak
# validation. What is well-evidenced is the SHAPE — that consequence must be
# absolute rather than proportional. The thresholds below should be re-derived
# against real-scan rungs before anyone treats them as settled.

# The single free parameter. Sourced from the operator's R5 rung: the 31-host
# multihost reference estate (5 CRITICAL / 14 HIGH / 29% of certificates
# expired) must score below 30. Not derivable from BAND_THRESHOLDS, because it
# expresses "deep inside POOR", which the bands do not subdivide.
DEEP_CRITICAL_CEILING: int = 25

# How many open CRITICAL findings constitute a catastrophic estate rather than
# a bad one. Also from the R5 rung, which carries 5.
DEEP_CRITICAL_COUNT: int = 5


def _top_of_band(band: str) -> int:
    """Highest score that still falls inside `band`.

    Derived from `BAND_THRESHOLDS` so the ceilings below cannot drift away from
    the published bands. POOR is the implicit floor and has no threshold entry
    of its own (see `quirk/severity_bands.py`), so its top is one below the
    lowest named threshold.
    """
    higher = [v for v in BAND_THRESHOLDS.values() if v > BAND_THRESHOLDS.get(band, -1)]
    if band not in BAND_THRESHOLDS:        # POOR
        return min(BAND_THRESHOLDS.values()) - 1
    return (min(higher) - 1) if higher else 100


def _scored_severity_counts(evidence: Mapping[str, Any]) -> Mapping[str, Any]:
    """Severity counts that feed the score (D-25).

    Prefers ``scored_finding_severity_counts`` (excludes score-neutral
    categories); falls back to ``finding_severity_counts`` for older
    evidence dicts that lack it.
    """
    scored = evidence.get("scored_finding_severity_counts")
    if isinstance(scored, Mapping):
        return scored
    legacy = evidence.get("finding_severity_counts", {})
    return legacy if isinstance(legacy, Mapping) else {}


def _consequence_ceiling(critical_count: int, high_count: int) -> Tuple[Optional[int], Optional[str]]:
    """999.115 C — the highest score an estate may hold given its ABSOLUTE
    count of high-consequence findings, irrespective of how small a proportion
    of the estate they represent.

    Returns `(ceiling, reason)`, or `(None, None)` when no ceiling applies.
    The reason string is client-facing: it must say what capped the score, so
    a capped number is never mistaken for a computed one.
    """
    if critical_count >= DEEP_CRITICAL_COUNT:
        return DEEP_CRITICAL_CEILING, (
            f"{critical_count} open CRITICAL findings"
        )
    if critical_count >= 1:
        return _top_of_band("POOR"), (
            f"{critical_count} open CRITICAL finding"
            f"{'s' if critical_count > 1 else ''}"
        )
    if high_count >= 3:
        return _top_of_band("FAIR"), f"{high_count} open HIGH findings"
    if high_count >= 1:
        return _top_of_band("MODERATE"), (
            f"{high_count} open HIGH finding{'s' if high_count > 1 else ''}"
        )
    return None, None


def _pqc_readiness_ceiling(pqc_hybrid_count: int) -> Tuple[Optional[int], Optional[str]]:
    """999.115 P7a — "no PQC, no 100". Operator decision, 2026-09-14.

    An estate with no observed hybrid post-quantum key exchange cannot reach
    the top of the scale on a *quantum* readiness assessment. Before this, a
    hygiene-perfect but quantum-blind estate scored 100 — as exposed to
    harvest-now-decrypt-later as it was before the engagement began, and told
    so by a perfect grade.

    Implemented as a CEILING and not as a larger bonus, and that is forced
    rather than preferred: `agility_pqc_hybrid_bonus` is already 8.0, the
    joint-largest bonus in SCORE_WEIGHTS, and measurement showed adopting PQC
    on every endpoint moved the score by exactly 0 points, because
    `_apply_weighted_impacts` clamps each domain at 25.0 and a clean estate is
    already there. Any bonus is absorbed the same way. A ceiling is the only
    shape that survives the clamp.

    The threshold is derived, not chosen: the top of GOOD. That is the
    operator's R2 rung — "well-run, no PQC" targets GOOD — expressed through
    `BAND_THRESHOLDS` rather than restated as a number.
    """
    if pqc_hybrid_count > 0:
        return None, None
    return _top_of_band("GOOD"), "no post-quantum key exchange observed"


def _apply_weighted_impacts(
    impacts: List[Tuple[str, float]],
    score_cap: float = 25.0,
) -> Tuple[int, List[Tuple[str, int]]]:
    total = score_cap + sum(v for _, v in impacts)
    clamped = _clamp(total, 0.0, score_cap)
    score = int(round(clamped))
    rounded_impacts = [(label, int(round(points))) for label, points in impacts if int(round(points)) != 0]
    return score, rounded_impacts


# Phase 188 SCORE-06 — per-category "was this domain assessed at all" predicates.
# Each reads ONLY mappings/values already destructured at the top of
# compute_readiness_score() -- no new evidence.py bookkeeping fields (per
# CONTEXT.md's locked "derived, not hand-maintained" decision). Do NOT use
# `denom == 0` as a predicate anywhere: `denom` is clamped to 1 below and can
# never be zero by construction (RESEARCH Anti-Patterns).


def _endpoints_assessed(endpoints: int) -> bool:
    """hygiene / modern_tls / agility_signals all read endpoint-wide counts
    (Phase 234: counts, no longer ratios) -- they were assessed iff any ASSESSABLE endpoint
    exists. Callers must pass the ADVISORY/CLOSED-excluded count
    (`assessable_endpoint_count`), not `totals.endpoints` — see the CR-02
    comment at the call site in compute_readiness_score()."""
    return endpoints > 0


def _identity_assessed(
    cert_obs: Mapping[str, Any],
    protocol_counts: Mapping[str, Any],
    placeholders: int = 0,
) -> bool:
    """identity_trust was assessed iff a certificate was observed or any
    identity protocol produced real evidence.

    Phase 234 D-11: Kerberos placeholder rows (the KDC answered but no etype
    data was obtained, e.g. `kerberos-etypes-unavailable-principal-unknown` or
    `kerberos-no-preauth`) are NOT identity evidence. `placeholders` is
    evidence's `kerberos_placeholder_count`; it is subtracted from the
    KERBEROS count only, floored at 0. `protocol_counts` itself is never
    edited, because reports, the CBOM and the dashboard read it.
    """
    if _as_int(cert_obs.get("certs_observed", 0)) > 0:
        return True
    total = 0
    for k in _IDENTITY_PROTOCOL_KEYS:
        value = max(0, _as_int(protocol_counts.get(k, 0)))
        if k == "KERBEROS":
            value = max(0, value - max(0, _as_int(placeholders)))
        total += value
    return total > 0


def _dar_assessed(protocol_counts: Mapping[str, Any]) -> bool:
    return sum(_as_int(protocol_counts.get(k, 0)) for k in _DAR_PROTOCOL_KEYS) > 0


def _motion_assessed(protocol_counts: Mapping[str, Any]) -> bool:
    return sum(_as_int(protocol_counts.get(k, 0)) for k in _MOTION_PROTOCOL_KEYS) > 0


def compute_readiness_score(
    evidence: Mapping[str, Any],
    *,
    profile: str | None = None,
    weights: Mapping[str, float] | None = None,
) -> Dict[str, Any]:
    w = dict(SCORE_WEIGHTS)
    prof = str(profile or "balanced").lower()
    if prof not in PROFILE_MULTIPLIERS:
        prof = "balanced"
    for prefix, factor in PROFILE_MULTIPLIERS[prof].items():
        for key in list(w):
            if key.startswith(prefix):
                w[key] = w[key] * factor
    if weights:
        for k, v in weights.items():
            w[k] = _as_float(v)

    totals = evidence.get("totals", {}) if isinstance(evidence.get("totals", {}), Mapping) else {}
    protocol_counts = evidence.get("protocol_counts", {}) if isinstance(evidence.get("protocol_counts", {}), Mapping) else {}
    cert_obs = evidence.get("certificate_observations", {}) if isinstance(evidence.get("certificate_observations", {}), Mapping) else {}
    cert_keys = evidence.get("cert_key_type_counts", {}) if isinstance(evidence.get("cert_key_type_counts", {}), Mapping) else {}
    scan_error = evidence.get("scan_error", {}) if isinstance(evidence.get("scan_error", {}), Mapping) else {}
    sev = _scored_severity_counts(evidence)

    endpoints = max(0, _as_int(totals.get("endpoints", 0)))

    # Phase 234 D-01 (scoring 4.0): NO term divides by a population any more.
    # Every weakness term is `_count_curve(count) * weight`; see N_REF above.
    # The 999.113 denominators (certificate population, assessable endpoints,
    # and the approximate domain/connector population) are gone, which also
    # makes 999.113's "domain denominator is approximate" follow-up moot.
    #
    # Two of those populations survive as GATES only, never as divisors:
    #   - `cert_denom` (certificates observed) gates the "certificate key types
    #     undetermined" penalty below and the identity assessed predicate;
    #   - `endpoint_denom` (ADVISORY/CLOSED-excluded assessable endpoints) is
    #     the `_endpoints_assessed` boolean gate (212 section 6: keep the gate,
    #     drop the division). Pre-184.1 evidence dicts that lack
    #     `assessable_endpoint_count` fall back to `endpoints`.
    cert_denom = max(0, _as_int(cert_obs.get("certs_observed", 0)))
    endpoint_denom = max(0, _as_int(evidence.get("assessable_endpoint_count", endpoints)))
    #
    # 999.115 -- `actionable_denom` and `agility_high_impact_ratio` are GONE.
    # 999.113 D1(d) corrected this ratio's denominator from `totals.findings`
    # (which includes INFO, and so scaled with scan depth) to the actionable
    # finding count. That was right, and insufficient: ANY ratio here carries
    # the same defect, because a finding count is not a population that badness
    # is proportional to. As a prevalence measure it diluted whenever the
    # denominator grew, which made discovering MEDIUM and LOW findings RAISE
    # the score -- the sole remaining cause of P1
    # (tests/test_score_properties.py::test_p1_*).
    #
    # It is removed rather than re-denominated because
    # `_consequence_ceiling()` now carries the high-impact signal ABSOLUTELY,
    # in the currency that signal actually has: how many CRITICAL and HIGH
    # findings exist, not what fraction of the finding list they represent.
    # Measured: removing the term closes P1 with the calibration ladder intact,
    # and removing it WITHOUT the ceiling closes nothing -- the two changes only
    # work together. See
    # .planning/decisions/999.115-scoring-model-candidate-measurements.md.
    plaintext_http_count = max(0, _as_int(evidence.get("plaintext_http_count", 0)))
    http_on_tls_count = max(0, _as_int(evidence.get("http_on_tls_port_count", 0)))
    mtls_present_count = max(0, _as_int(evidence.get("mtls_present_count", 0)))
    # Phase 234 D-03: the scan-error terms read the scan-error COUNT through
    # the same curve. The rate (count / total endpoints) diluted exactly like
    # the ratio sites. There is deliberately no fallback to the rate.
    scan_error_count = max(0, _as_int(scan_error.get("count", 0)))
    scan_error_penalty = _count_curve(scan_error_count)

    unknown_count = max(0, _as_int(protocol_counts.get("UNKNOWN", 0)))
    # Phase 211-03 (DENOM-04 residual / 17-vs-18 divergence leg 2): read the
    # endpoint-derived `legacy_tls_count` key evidence.py now always emits.
    # The old `sev.get("LOW", 0)` severity-count proxy survives ONLY as a
    # fallback for hand-built legacy evidence dicts in older tests -- both
    # live pipelines always supply the key (asserted by
    # tests/test_evidence_finding_vocabulary_parity.py's
    # TestLegacyTlsCountCrossVocabularyParity suite). A silent fallback of
    # this exact shape has bitten this project before:
    # `assessable_endpoint_count`'s identical `evidence.get(key, fallback)`
    # fallback at :412 had to be positively proven not to be firing during
    # this phase's own research (211-CONTEXT.md D-07/H2).
    legacy_tls_count = max(0, _as_int(evidence.get("legacy_tls_count", sev.get("LOW", 0))))
    # 999.115: `high_impact` is gone with the ratio it fed. CRITICAL and HIGH
    # counts now reach the score through `_consequence_ceiling()`, which reads
    # `sev` directly at the cap site below. Phase 184.4 D-03's "do NOT remove
    # CRITICAL from high_impact to avoid overlap" warning is retired with it:
    # there is no longer a second path for it to overlap WITH.

    expired_count = max(0, _as_int(cert_obs.get("expired_count", 0)))
    expiring_count = max(0, _as_int(cert_obs.get("expiring_count", 0)))
    self_signed_count = max(0, _as_int(cert_obs.get("self_signed_count", 0)))

    rsa_count = max(0, _as_int(cert_keys.get("RSA", 0)))
    ecdsa_count = max(0, _as_int(cert_keys.get("ECDSA", 0)))
    # Phase 234 O-4: ML-DSA / SLH-DSA / composite certificate keys.
    pqc_cert_count = max(0, _as_int(cert_keys.get("PQC", 0)))

    kerberos_weak_count = max(0, _as_int(evidence.get("identity_weak_etype_count", 0)))
    saml_weak_count = max(0, _as_int(evidence.get("saml_weak_signing_count", 0)))
    dnssec_weak_count = max(0, _as_int(evidence.get("dnssec_weak_algo_count", 0)))
    smime_weak_signing_count = max(0, _as_int(evidence.get("smime_weak_signing_count", 0)))
    smime_expired_count      = max(0, _as_int(evidence.get("smime_expired_count", 0)))
    smime_weak_key_count     = max(0, _as_int(evidence.get("smime_weak_key_count", 0)))
    adcs_weak_template_count = max(0, _as_int(evidence.get("adcs_weak_template_count", 0)))
    adcs_misconfig_count     = max(0, _as_int(evidence.get("adcs_misconfig_count", 0)))
    adcs_weak_signing_count  = max(0, _as_int(evidence.get("adcs_weak_signing_count", 0)))
    adcs_coverage_gap_count  = max(0, _as_int(evidence.get("adcs_coverage_gap_count", 0)))
    dar_db_plaintext = max(0, _as_int(evidence.get("dar_db_plaintext_count", 0)))
    dar_db_weak_ssl = max(0, _as_int(evidence.get("dar_db_weak_ssl_count", 0)))
    dar_storage_unencrypted = max(0, _as_int(evidence.get("dar_storage_unencrypted_count", 0)))
    dar_storage_aws_managed = max(0, _as_int(evidence.get("dar_storage_aws_managed_count", 0)))
    dar_k8s_unencrypted = max(0, _as_int(evidence.get("dar_k8s_unencrypted_count", 0)))
    dar_k8s_inaccessible = max(0, _as_int(evidence.get("dar_k8s_inaccessible_count", 0)))
    dar_vault_weak = max(0, _as_int(evidence.get("dar_vault_weak_count", 0)))

    hygiene_impacts: List[Tuple[str, float]] = [
        ("Plaintext HTTP exposure", -_count_curve(plaintext_http_count) * w["hygiene_plaintext_http_ratio"]),
        ("HTTP on TLS-designated ports", -_count_curve(http_on_tls_count) * w["hygiene_http_on_tls_ratio"]),
        ("Scan error rate", -scan_error_penalty * w["hygiene_scan_error_rate"]),
    ]
    hygiene_score, hygiene_drivers = _apply_weighted_impacts(hygiene_impacts)

    modern_tls_impacts: List[Tuple[str, float]] = [
        ("Legacy TLS versions present", -_count_curve(legacy_tls_count) * w["modern_tls_legacy_versions_ratio"]),
        ("Unknown open services", -_count_curve(unknown_count) * w["modern_tls_unknown_ratio"]),
        ("Assessment visibility blockers", -scan_error_penalty * w["modern_tls_scan_error_rate"]),
    ]
    modern_tls_score, modern_tls_drivers = _apply_weighted_impacts(modern_tls_impacts)

    identity_trust_impacts: List[Tuple[str, float]] = [
        ("Expired certificates", -_count_curve(expired_count) * w["identity_expired_ratio"]),
        ("Expiring certificates", -_count_curve(expiring_count) * w["identity_expiring_ratio"]),
        ("Self-signed certificates", -_count_curve(self_signed_count) * w["identity_self_signed_ratio"]),
        # Phase 234 review D-28: a PRESENCE credit, +6 once when any mTLS
        # endpoint is observed. D-02 had made it a count curve, so every
        # further mTLS-enforcing endpoint raised identity_trust up to N_REF:
        # observing more healthy endpoints raised the score, which SCORE-09
        # forbids. Same single-step shape as the PQC credit (D-04). The weight
        # key keeps its `_ratio_bonus` name because calibration_overrides
        # address weights by name.
        ("mTLS enforcement signals", (w["identity_mtls_ratio_bonus"] if mtls_present_count > 0 else 0.0)),
        ("RC4/DES Kerberos etypes detected", -_count_curve(kerberos_weak_count) * w["identity_kerberos_weak_etype_ratio"]),
        ("Weak SAML signing key", -_count_curve(saml_weak_count) * w["identity_saml_weak_signing_ratio"]),
        ("Weak DNSSEC signing algorithm", -_count_curve(dnssec_weak_count) * w["identity_dnssec_weak_algo_ratio"]),
        ("Weak S/MIME signing", -_count_curve(smime_weak_signing_count) * w["identity_smime_weak_signing_count"]),
        ("Expired S/MIME cert", -_count_curve(smime_expired_count) * w["identity_smime_expired_count"]),
        ("Weak S/MIME key",     -_count_curve(smime_weak_key_count) * w["identity_smime_weak_key_count"]),
        ("Weak AD CS template",         -_count_curve(adcs_weak_template_count) * w["identity_adcs_weak_template_count"]),
        ("AD CS template misconfig",    -_count_curve(adcs_misconfig_count)     * w["identity_adcs_misconfig_count"]),
        ("Weak AD CS signing algo",     -_count_curve(adcs_weak_signing_count)  * w["identity_adcs_weak_signing_count"]),
        ("AD CS coverage gap (ESC4/5/7/8)", -_count_curve(adcs_coverage_gap_count) * w["identity_adcs_coverage_gap_count"]),
    ]
    identity_trust_score, identity_trust_drivers = _apply_weighted_impacts(identity_trust_impacts)

    pqc_hybrid_count = max(0, _as_int(evidence.get("pqc_hybrid_endpoint_count", 0)))

    agility_impacts: List[Tuple[str, float]] = [
        ("Unknown service inventory", -_count_curve(unknown_count) * w["agility_unknown_ratio"]),
    ]
    # Phase 234 D-04 / O-2: classical certificate keys (RSA, ECDSA, EdDSA; the
    # evidence builder counts EdDSA under ECDSA) are all quantum-vulnerable, so
    # any of them costs a flat -8. It is not count-based: the key TYPE is the
    # signal, and one quantum-vulnerable certificate needs replacing just as
    # surely as forty. The 3.0 ECDSA +4 bonus is gone, so observing more
    # classical endpoints can never raise the score.
    if rsa_count + ecdsa_count > 0:
        agility_impacts.append(
            ("Quantum-vulnerable certificate keys (RSA/ECDSA/EdDSA)", -w["agility_rsa_only_penalty"])
        )
    elif cert_denom > 0 and pqc_cert_count == 0:
        # 999.115 P8 — certificates WERE observed but no key type was
        # determined for any of them. Before this branch existed, such a scan
        # took no key-type penalty and scored strictly better than one that
        # honestly reported RSA. See tests/test_score_properties.py::test_p8_*.
        # The penalty equals the classical one, so not looking never pays.
        #
        # Guarded on `cert_denom > 0` so a scan that observed NO certificates
        # at all is untouched — that is genuine absence of the subject, which
        # `_identity_assessed` already handles, not a failure to determine a
        # property of certificates that are right there. Phase 234: also
        # guarded on `pqc_cert_count == 0`, because an estate whose only
        # reported key type is PQC did report a key type.
        agility_impacts.append(
            ("Certificate key types undetermined", -w["agility_unverified_key_type_penalty"])
        )
    # Phase 234 D-04 / O-4: ONE +8 credit for observing post-quantum crypto,
    # whether a PQC/hybrid key exchange or a PQC certificate key. Never +16:
    # the two observations share the credit. The step a single PQC observation
    # produces is deliberate, sanctioned credit under O-2, not dilution. The
    # 84 "no PQC, no 100" ceiling below stays keyed on key exchange only.
    if pqc_hybrid_count > 0 or pqc_cert_count > 0:
        agility_impacts.append(
            ("Post-quantum key exchange or certificate key", w["agility_pqc_hybrid_bonus"])
        )

    # Phase 94 SCORE-01: bearer-token weak alg and OpenAPI plaintext signals
    bearer_weak_jwt_alg = max(0, _as_int(evidence.get("bearer_token_weak_alg_count", 0)))
    openapi_plaintext = max(0, _as_int(evidence.get("openapi_plaintext_server_count", 0)))
    agility_impacts.extend([
        ("Bearer token weak algorithm",
         -_count_curve(bearer_weak_jwt_alg) * w["agility_weak_jwt_alg_ratio"]),
        ("OpenAPI plaintext servers (http://)",
         -_count_curve(openapi_plaintext) * w["agility_openapi_plaintext_ratio"]),
    ])

    # Phase 95 SCORE-01: code-signing cert weak algorithm agility signal
    codesign_weak = max(0, _as_int(evidence.get("codesign_weak_algo_count", 0)))
    agility_impacts.append(
        ("Code-signing cert weak algorithm",
         -_count_curve(codesign_weak) * w["agility_codesign_weak_algo_ratio"])
    )

    # Phase 96 SCORE-01: active REST fuzz CRITICAL/HIGH crypto-posture findings agility signal
    fuzz_findings = max(0, _as_int(evidence.get("fuzz_finding_count", 0)))
    agility_impacts.append(
        ("Active REST fuzz crypto-posture findings",
         -_count_curve(fuzz_findings) * w["agility_fuzz_crypto_posture_ratio"])
    )

    agility_score, agility_drivers = _apply_weighted_impacts(agility_impacts)

    dar_impacts: List[Tuple[str, float]] = [
        ("Database plaintext connections", -_count_curve(dar_db_plaintext) * w["dar_db_plaintext_ratio"]),
        ("Database weak SSL configuration", -_count_curve(dar_db_weak_ssl) * w["dar_db_weak_ssl_ratio"]),
        ("Object storage unencrypted", -_count_curve(dar_storage_unencrypted) * w["dar_storage_unencrypted_ratio"]),
        ("Object storage platform-managed keys", -_count_curve(dar_storage_aws_managed) * w["dar_storage_aws_managed_ratio"]),
        ("Kubernetes etcd unencrypted", -_count_curve(dar_k8s_unencrypted) * w["dar_k8s_unencrypted_ratio"]),
        ("Kubernetes etcd encryption inaccessible", -_count_curve(dar_k8s_inaccessible) * w["dar_k8s_inaccessible_ratio"]),
        ("Vault weak crypto posture", -_count_curve(dar_vault_weak) * w["dar_vault_weak_ratio"]),
    ]
    dar_score, dar_drivers = _apply_weighted_impacts(dar_impacts)

    # Motion (Phase 34) — mirrors dar_impacts shape; D-02 folds STARTTLS-missing into plaintext numerator
    motion_email_plaintext_num = (
        _as_int(evidence.get("motion_email_plaintext_count", 0))
        + _as_int(evidence.get("motion_email_starttls_missing_count", 0))
    )
    motion_email_weak_cipher = max(0, _as_int(evidence.get("motion_email_weak_cipher_count", 0)))
    motion_broker_plaintext = max(0, _as_int(evidence.get("motion_broker_plaintext_count", 0)))
    motion_broker_weak_tls = max(0, _as_int(evidence.get("motion_broker_weak_tls_count", 0)))
    motion_broker_weak_cipher = max(0, _as_int(evidence.get("motion_broker_weak_cipher_count", 0)))

    motion_impacts: List[Tuple[str, float]] = [
        ("Email plaintext or missing STARTTLS",
         -_count_curve(motion_email_plaintext_num) * w["motion_email_plaintext_ratio"]),
        ("Weak cipher on email TLS",
         -_count_curve(motion_email_weak_cipher) * w["motion_email_weak_cipher_ratio"]),
        ("Plaintext broker listeners",
         -_count_curve(motion_broker_plaintext) * w["motion_broker_plaintext_ratio"]),
        ("Weak TLS on brokers",
         -_count_curve(motion_broker_weak_tls) * w["motion_broker_weak_tls_ratio"]),
        ("Weak cipher on broker TLS",
         -_count_curve(motion_broker_weak_cipher) * w["motion_broker_weak_cipher_ratio"]),
    ]
    motion_score, motion_drivers = _apply_weighted_impacts(motion_impacts)

    # Phase 188 SCORE-06 — exclude-and-rescale. A category with no assessable
    # evidence contributes neither 25 nor 0; the headline divides only by the
    # domains that were actually assessed. `domains_total`/`domains_assessed`
    # are ALWAYS derived from `len(category_table)`, never a hardcoded 6, so a
    # future 7th category cannot silently break this math.
    # 188 review CR-02: the endpoint-wide predicate must read the
    # non-asset-excluded counter, not totals.endpoints — build_evidence_summary
    # counts ADVISORY (scanner self-reports) and CLOSED (TIMEOUT/REFUSED/
    # UNREACHABLE probes) rows into totals.endpoints, so a scan that reached
    # NOTHING (all rows CLOSED) would otherwise mark hygiene/modern_tls/
    # agility_signals "assessed" with zero real evidence and fabricate a
    # 100/100 EXCELLENT headline. assessable_endpoint_count (Phase 184.1,
    # excludes ADVISORY/CLOSED) is the honest signal; `endpoints` remains the
    # fallback for hand-built pre-184.1 evidence dicts that lack the key.
    # Same computation as `endpoint_denom` above (999.113) -- reused here rather
    # than recomputed. Since Phase 234 it is ONLY this boolean gate; no term
    # divides by it.
    assessable_endpoints = endpoint_denom
    endpoints_assessed = _endpoints_assessed(assessable_endpoints)
    identity_assessed = _identity_assessed(
        cert_obs,
        protocol_counts,
        placeholders=max(0, _as_int(evidence.get("kerberos_placeholder_count", 0))),
    )
    dar_assessed = _dar_assessed(protocol_counts)
    motion_assessed = _motion_assessed(protocol_counts)

    # 999.115 P5c — each domain's DRIVERS travel in this same table, alongside
    # its score and its assessed flag. They used to be assembled separately, a
    # few lines below, by concatenating every `*_drivers` list unconditionally;
    # nothing consulted the assessed flags, so a domain excluded from the
    # headline (subscore None, absent from the rescale denominator) could still
    # supply the single largest driver in the client-facing explanation. The
    # score disowned the domain while the narrative cited it.
    #
    # Carrying all three together is the fix rather than filtering afterwards:
    # a future seventh domain gets consistent treatment by construction, and
    # the subscore and the driver list cannot disagree about what was assessed
    # because they now read the same tuple.
    category_table: Dict[str, Tuple[int, bool, List[Tuple[str, int]]]] = {
        "hygiene": (hygiene_score, endpoints_assessed, hygiene_drivers),
        "modern_tls": (modern_tls_score, endpoints_assessed, modern_tls_drivers),
        "identity_trust": (identity_trust_score, identity_assessed, identity_trust_drivers),
        "agility_signals": (agility_score, endpoints_assessed, agility_drivers),
        "data_at_rest": (dar_score, dar_assessed, dar_drivers),
        "data_in_motion": (motion_score, motion_assessed, motion_drivers),
    }
    domains_total = len(category_table)
    assessed_scores = {name: score for name, (score, ok, _) in category_table.items() if ok}
    domains_assessed = len(assessed_scores)

    total_score: Optional[int]
    score_divisor: Optional[float]
    rating_cap_reason: Optional[str]

    if domains_assessed == 0:
        # Phase 181 honest-absence precedent: never fabricate a 0/100 headline
        # for a scan that assessed nothing. No term divides by a population
        # (Phase 234 D-01), so nothing above can raise ZeroDivisionError; this
        # branch exists because it also skips
        # `band_for_score`/`cap_band_for_severity` entirely
        # (the latter raises ValueError for a band outside BAND_ORDER).
        total_score = None
        score_divisor = None
        rating = "NOT_ASSESSED"
        rating_cap_reason = None
    else:
        score_divisor = domains_assessed * 25 / 100
        total_score = int(round(sum(assessed_scores.values()) / (domains_assessed * 25) * 100))

        # 999.115 C — apply the absolute consequence ceiling BEFORE the band is
        # derived, so the number and the label agree. Ordering matters: capping
        # after `_rating()` would reproduce exactly the incoherence this change
        # exists to remove (a score of 87 wearing the word FAIR).
        _high_count = max(0, _as_int(sev.get("HIGH", 0)))
        _candidate_ceilings = [
            _consequence_ceiling(
                max(0, _as_int(sev.get("CRITICAL", 0))), _high_count
            ),
            _pqc_readiness_ceiling(pqc_hybrid_count),
        ]
        # Lowest ceiling binds, and its reason is the one disclosed. Collecting
        # them in a list rather than nesting conditionals means a future third
        # ceiling is one entry, and cannot silently take precedence over an
        # existing one by being written earlier in an if/elif chain.
        _applicable = [(c, r) for c, r in _candidate_ceilings if c is not None]
        _ceiling, _ceiling_reason = min(_applicable, default=(None, None))
        # COMPRESS into [0, ceiling] rather than clamp to it. This distinction
        # is load-bearing and was found by measurement, not by design: a hard
        # `min(score, ceiling)` destroys every gradient below the ceiling, so on
        # exactly the estates that most need remediation the score becomes
        # INERT. Measured on the 31-host reference estate under a hard clamp:
        # renewing every expired certificate moved the score +0, eliminating all
        # plaintext HTTP moved it +0, and the strict/balanced/lenient
        # calibration profiles collapsed to a single identical number. The
        # product's remediation roadmap would have shown "+0 points" against
        # every recommendation it makes.
        #
        # Compression bounds the maximum just as firmly — a 5-CRITICAL estate
        # still cannot exceed DEEP_CRITICAL_CEILING — while preserving ordering,
        # remediation lift, and profile sensitivity within the permitted range.
        # The guard is `is not None` and NOT `total_score > _ceiling`. Compressing
        # only ABOVE the ceiling reintroduces the clamp's defect in a subtler form:
        # it puts a cliff exactly AT the ceiling, because the mapping is
        # discontinuous there. Measured with ceiling 84: a computed 84 emitted 84,
        # a computed 85 emitted 71, and nothing in the whole computed range
        # [85, 100] ever emitted more than 84 — so every well-run estate scored
        # BELOW a mediocre one. Found 2026-09-14 by
        # test_identity_surface::test_weak_kerberos_lowers_score, which caught a
        # live P1 violation the property suite's own fixtures do not cover: adding
        # three weak-Kerberos findings moved that estate 77 -> 84.
        #
        # Compression is a linear map of [0, 100] onto [0, ceiling]. That map is
        # only order-preserving if it is applied across the WHOLE range; applying
        # it piecewise makes it non-monotonic, which is the one property the
        # ceiling exists to protect.
        consequence_capped_from: Optional[int] = None
        if _ceiling is not None:
            consequence_capped_from = total_score
            total_score = int(round(_ceiling * total_score / 100))

        numeric_band = _rating(total_score)

        # Phase 184.4 D-01/D-02/D-06/D-09, as amended by 999.115. The band cap
        # below is now usually a NO-OP: the consequence ceiling has already
        # moved the number into the band this would otherwise have forced. It
        # is kept as defence in depth — a second, independent guarantee that a
        # CRITICAL-bearing estate cannot be labelled EXCELLENT — and removing it
        # would discard that for no benefit.
        #
        # D-03's "this must not double-count `agility_high_impact_ratio`"
        # rationale no longer applies: that term was removed by 999.115 (see the
        # note where `high_impact` is derived), so there is no other path by
        # which consequence reaches the number.
        critical_count = max(0, _as_int(sev.get("CRITICAL", 0)))
        rating = cap_band_for_severity(numeric_band, critical_count)
        rating_cap_reason = cap_reason(numeric_band, rating, critical_count, total_score)

        # 999.115 C — a capped NUMBER must disclose that it was capped, or a
        # client reads it as computed. `rating_cap_reason` is the existing
        # channel for exactly this (report surfaces already render it as
        # "Score capped: {reason}" — Phase 194-03), so the consequence cap
        # reuses it rather than adding a key no surface reads yet.
        #
        # It takes precedence over the band-cap reason when both apply: after C,
        # the band cap will usually NOT fire, because the number has already
        # fallen into the band that cap would have forced. Where it does fire,
        # the consequence cap is the more specific and more actionable
        # explanation — it names the finding count that set the ceiling.
        if consequence_capped_from is not None:
            rating_cap_reason = (
                f"{_ceiling_reason} — score limited to {total_score} "
                f"(computed {consequence_capped_from})"
            )

    coverage_disclosure = f"{domains_assessed} of {domains_total} domains assessed"

    # 999.115 P5c — drivers come from ASSESSED domains only, read out of the
    # same `category_table` that produces `subscores` below. An unassessed
    # domain contributes no driver, because the headline makes no claim about
    # it: citing it in the explanation would be the narrative asserting what
    # the number explicitly declined to.
    all_drivers: List[Tuple[str, int]] = [
        driver
        for _, (_, ok, drivers) in category_table.items()
        if ok
        for driver in drivers
    ]
    all_drivers_sorted = sorted(all_drivers, key=lambda x: (-abs(x[1]), x[0]))
    top_drivers = [{"reason": reason, "points": points} for reason, points in all_drivers_sorted[:5]]

    # Unassessed categories carry None (not their raw 0-25 number). NOTE for
    # renderers (188 review CR-01): `subscores.get(key, "—")` does NOT render an
    # em dash for these — the key is always PRESENT with value None, and
    # dict.get only returns its default for a MISSING key. Every subscore-table
    # surface must branch explicitly on `value is None` and substitute "—"
    # itself (see executive.py/writer.py/docx_renderer.py/report.html.j2).
    subscores: Dict[str, Optional[int]] = {
        name: (score if ok else None) for name, (score, ok, _) in category_table.items()
    }

    return {
        "score": total_score,
        "rating": rating,
        "rating_cap_reason": rating_cap_reason,
        "subscores": subscores,
        "drivers": top_drivers,
        "domains_assessed": domains_assessed,
        "domains_total": domains_total,
        "score_divisor": score_divisor,
        "coverage_disclosure": coverage_disclosure,
        "scoring_version": SCORING_VERSION,
        "scoring_version_note": SCORING_VERSION_NOTE,
    }
