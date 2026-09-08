from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from quirk.severity_bands import band_for_score, cap_band_for_severity, cap_reason

# Phase 188 SCORE-06 — scoring formula version marker. Bumped whenever the
# aggregation shape changes (exclude-and-rescale replaces the fixed / 1.5
# rollup). NO back-migration of stored historical scores (CONTEXT.md locked
# decision) — this marker lets every report surface disclose that pre-5.20
# scores are not comparable to post-5.20 scores.
SCORING_VERSION = "2.0"
SCORING_VERSION_NOTE = "scoring v2 — not comparable with pre-5.20 scores"

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
_IDENTITY_PROTOCOL_KEYS: Tuple[str, ...] = ("KERBEROS", "SAML", "DNSSEC")

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
    "agility_high_impact_ratio": 14.0,
    "agility_unknown_ratio": 6.0,
    "agility_rsa_only_penalty": 8.0,
    "agility_has_ecdsa_bonus": 4.0,
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


def _ratio(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return max(0.0, num / den)


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
    """hygiene / modern_tls / agility_signals all read endpoint-wide ratios
    against the same `denom` -- they were assessed iff any ASSESSABLE endpoint
    exists. Callers must pass the ADVISORY/CLOSED-excluded count
    (`assessable_endpoint_count`), not `totals.endpoints` — see the CR-02
    comment at the call site in compute_readiness_score()."""
    return endpoints > 0


def _identity_assessed(cert_obs: Mapping[str, Any], protocol_counts: Mapping[str, Any]) -> bool:
    if _as_int(cert_obs.get("certs_observed", 0)) > 0:
        return True
    return sum(_as_int(protocol_counts.get(k, 0)) for k in _IDENTITY_PROTOCOL_KEYS) > 0


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
    sev = evidence.get("finding_severity_counts", {}) if isinstance(evidence.get("finding_severity_counts", {}), Mapping) else {}

    endpoints = max(0, _as_int(totals.get("endpoints", 0)))
    findings = max(0, _as_int(totals.get("findings", 0)))
    denom = endpoints if endpoints > 0 else 1

    plaintext_http_count = max(0, _as_int(evidence.get("plaintext_http_count", 0)))
    http_on_tls_count = max(0, _as_int(evidence.get("http_on_tls_port_count", 0)))
    mtls_present_count = max(0, _as_int(evidence.get("mtls_present_count", 0)))
    scan_error_rate = _clamp(_as_float(scan_error.get("rate", 0.0)), 0.0, 1.0)

    unknown_count = max(0, _as_int(protocol_counts.get("UNKNOWN", 0)))
    legacy_tls_count = max(0, _as_int(sev.get("LOW", 0)))
    # Phase 184.4 D-03: this CRITICAL count also feeds the severity band cap
    # applied to `rating` below (near `total_score = ...`). That cap moves the
    # BAND; this ratio moves the NUMBER — they are orthogonal, not a double
    # count. Do NOT remove CRITICAL from `high_impact` to "avoid overlap".
    # See the cap site below and `quirk/severity_bands.py::cap_band_for_severity()`
    # for the full rationale.
    high_impact = max(0, _as_int(sev.get("HIGH", 0)) + _as_int(sev.get("CRITICAL", 0)))

    expired_count = max(0, _as_int(cert_obs.get("expired_count", 0)))
    expiring_count = max(0, _as_int(cert_obs.get("expiring_count", 0)))
    self_signed_count = max(0, _as_int(cert_obs.get("self_signed_count", 0)))

    rsa_count = max(0, _as_int(cert_keys.get("RSA", 0)))
    ecdsa_count = max(0, _as_int(cert_keys.get("ECDSA", 0)))

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
        ("Plaintext HTTP exposure", -_ratio(plaintext_http_count, denom) * w["hygiene_plaintext_http_ratio"]),
        ("HTTP on TLS-designated ports", -_ratio(http_on_tls_count, denom) * w["hygiene_http_on_tls_ratio"]),
        ("Scan error rate", -scan_error_rate * w["hygiene_scan_error_rate"]),
    ]
    hygiene_score, hygiene_drivers = _apply_weighted_impacts(hygiene_impacts)

    modern_tls_impacts: List[Tuple[str, float]] = [
        ("Legacy TLS versions present", -_ratio(legacy_tls_count, denom) * w["modern_tls_legacy_versions_ratio"]),
        ("Unknown open services", -_ratio(unknown_count, denom) * w["modern_tls_unknown_ratio"]),
        ("Assessment visibility blockers", -scan_error_rate * w["modern_tls_scan_error_rate"]),
    ]
    modern_tls_score, modern_tls_drivers = _apply_weighted_impacts(modern_tls_impacts)

    identity_trust_impacts: List[Tuple[str, float]] = [
        ("Expired certificates", -_ratio(expired_count, denom) * w["identity_expired_ratio"]),
        ("Expiring certificates", -_ratio(expiring_count, denom) * w["identity_expiring_ratio"]),
        ("Self-signed certificates", -_ratio(self_signed_count, denom) * w["identity_self_signed_ratio"]),
        ("mTLS enforcement signals", _ratio(mtls_present_count, denom) * w["identity_mtls_ratio_bonus"]),
        ("RC4/DES Kerberos etypes detected", -_ratio(kerberos_weak_count, denom) * w["identity_kerberos_weak_etype_ratio"]),
        ("Weak SAML signing key", -_ratio(saml_weak_count, denom) * w["identity_saml_weak_signing_ratio"]),
        ("Weak DNSSEC signing algorithm", -_ratio(dnssec_weak_count, denom) * w["identity_dnssec_weak_algo_ratio"]),
        ("Weak S/MIME signing", -_ratio(smime_weak_signing_count, denom) * w["identity_smime_weak_signing_count"]),
        ("Expired S/MIME cert", -_ratio(smime_expired_count, denom) * w["identity_smime_expired_count"]),
        ("Weak S/MIME key",     -_ratio(smime_weak_key_count, denom) * w["identity_smime_weak_key_count"]),
        ("Weak AD CS template",         -_ratio(adcs_weak_template_count, denom) * w["identity_adcs_weak_template_count"]),
        ("AD CS template misconfig",    -_ratio(adcs_misconfig_count, denom)     * w["identity_adcs_misconfig_count"]),
        ("Weak AD CS signing algo",     -_ratio(adcs_weak_signing_count, denom)  * w["identity_adcs_weak_signing_count"]),
        ("AD CS coverage gap (ESC4/5/7/8)", -_ratio(adcs_coverage_gap_count, denom) * w["identity_adcs_coverage_gap_count"]),
    ]
    identity_trust_score, identity_trust_drivers = _apply_weighted_impacts(identity_trust_impacts)

    pqc_hybrid_count = max(0, _as_int(evidence.get("pqc_hybrid_endpoint_count", 0)))

    agility_impacts: List[Tuple[str, float]] = [
        ("High-impact findings", -_ratio(high_impact, max(findings, 1)) * w["agility_high_impact_ratio"]),
        ("Unknown service inventory", -_ratio(unknown_count, denom) * w["agility_unknown_ratio"]),
    ]
    if rsa_count > 0 and ecdsa_count == 0:
        agility_impacts.append(("RSA-only certificate posture", -w["agility_rsa_only_penalty"]))
    elif ecdsa_count > 0:
        agility_impacts.append(("ECDSA adoption signal", w["agility_has_ecdsa_bonus"]))
    if pqc_hybrid_count > 0:
        agility_impacts.append(("PQC-hybrid key exchange (X25519MLKEM768)", w["agility_pqc_hybrid_bonus"]))

    # Phase 94 SCORE-01: bearer-token weak alg and OpenAPI plaintext signals
    bearer_weak_jwt_alg = max(0, _as_int(evidence.get("bearer_token_weak_alg_count", 0)))
    openapi_plaintext = max(0, _as_int(evidence.get("openapi_plaintext_server_count", 0)))
    agility_impacts.extend([
        ("Bearer token weak algorithm",
         -_ratio(bearer_weak_jwt_alg, denom) * w["agility_weak_jwt_alg_ratio"]),
        ("OpenAPI plaintext servers (http://)",
         -_ratio(openapi_plaintext, denom) * w["agility_openapi_plaintext_ratio"]),
    ])

    # Phase 95 SCORE-01: code-signing cert weak algorithm agility signal
    codesign_weak = max(0, _as_int(evidence.get("codesign_weak_algo_count", 0)))
    agility_impacts.append(
        ("Code-signing cert weak algorithm",
         -_ratio(codesign_weak, denom) * w["agility_codesign_weak_algo_ratio"])
    )

    # Phase 96 SCORE-01: active REST fuzz CRITICAL/HIGH crypto-posture findings agility signal
    fuzz_findings = max(0, _as_int(evidence.get("fuzz_finding_count", 0)))
    agility_impacts.append(
        ("Active REST fuzz crypto-posture findings",
         -_ratio(fuzz_findings, denom) * w["agility_fuzz_crypto_posture_ratio"])
    )

    agility_score, agility_drivers = _apply_weighted_impacts(agility_impacts)

    dar_impacts: List[Tuple[str, float]] = [
        ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
        ("Database weak SSL configuration", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
        ("Object storage unencrypted", -_ratio(dar_storage_unencrypted, denom) * w["dar_storage_unencrypted_ratio"]),
        ("Object storage platform-managed keys", -_ratio(dar_storage_aws_managed, denom) * w["dar_storage_aws_managed_ratio"]),
        ("Kubernetes etcd unencrypted", -_ratio(dar_k8s_unencrypted, denom) * w["dar_k8s_unencrypted_ratio"]),
        ("Kubernetes etcd encryption inaccessible", -_ratio(dar_k8s_inaccessible, denom) * w["dar_k8s_inaccessible_ratio"]),
        ("Vault weak crypto posture", -_ratio(dar_vault_weak, denom) * w["dar_vault_weak_ratio"]),
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
         -_ratio(motion_email_plaintext_num, denom) * w["motion_email_plaintext_ratio"]),
        ("Weak cipher on email TLS",
         -_ratio(motion_email_weak_cipher, denom) * w["motion_email_weak_cipher_ratio"]),
        ("Plaintext broker listeners",
         -_ratio(motion_broker_plaintext, denom) * w["motion_broker_plaintext_ratio"]),
        ("Weak TLS on brokers",
         -_ratio(motion_broker_weak_tls, denom) * w["motion_broker_weak_tls_ratio"]),
        ("Weak cipher on broker TLS",
         -_ratio(motion_broker_weak_cipher, denom) * w["motion_broker_weak_cipher_ratio"]),
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
    assessable_endpoints = max(
        0, _as_int(evidence.get("assessable_endpoint_count", endpoints))
    )
    endpoints_assessed = _endpoints_assessed(assessable_endpoints)
    identity_assessed = _identity_assessed(cert_obs, protocol_counts)
    dar_assessed = _dar_assessed(protocol_counts)
    motion_assessed = _motion_assessed(protocol_counts)

    category_table: Dict[str, Tuple[int, bool]] = {
        "hygiene": (hygiene_score, endpoints_assessed),
        "modern_tls": (modern_tls_score, endpoints_assessed),
        "identity_trust": (identity_trust_score, identity_assessed),
        "agility_signals": (agility_score, endpoints_assessed),
        "data_at_rest": (dar_score, dar_assessed),
        "data_in_motion": (motion_score, motion_assessed),
    }
    domains_total = len(category_table)
    assessed_scores = {name: score for name, (score, ok) in category_table.items() if ok}
    domains_assessed = len(assessed_scores)

    total_score: Optional[int]
    score_divisor: Optional[float]
    rating_cap_reason: Optional[str]

    if domains_assessed == 0:
        # Phase 181 honest-absence precedent: never fabricate a 0/100 headline
        # for a scan that assessed nothing. `denom` above is clamped to 1 and
        # therefore can never trigger a ZeroDivisionError here anyway, but this
        # branch also skips `band_for_score`/`cap_band_for_severity` entirely
        # (the latter raises ValueError for a band outside BAND_ORDER).
        total_score = None
        score_divisor = None
        rating = "NOT_ASSESSED"
        rating_cap_reason = None
    else:
        score_divisor = domains_assessed * 25 / 100
        total_score = int(round(sum(assessed_scores.values()) / (domains_assessed * 25) * 100))
        numeric_band = _rating(total_score)

        # Phase 184.4 D-01/D-02/D-03/D-06/D-09: severity floor on the BAND only.
        # The number (`total_score`) never moves here. Any open CRITICAL finding
        # caps the emitted band at FAIR (never a graduated ladder — see
        # `cap_band_for_severity()`). This is orthogonal to, and does NOT
        # double-count, the `high_impact`/`agility_high_impact_ratio` contribution
        # above (D-03): that path already moved `total_score` down; this path
        # only changes the label attached to it. `critical_count` is read from
        # the `sev` mapping already in scope above (D-06) — no new parameter.
        critical_count = max(0, _as_int(sev.get("CRITICAL", 0)))
        rating = cap_band_for_severity(numeric_band, critical_count)
        rating_cap_reason = cap_reason(numeric_band, rating, critical_count, total_score)

    coverage_disclosure = f"{domains_assessed} of {domains_total} domains assessed"

    all_drivers: List[Tuple[str, int]] = (
        hygiene_drivers + modern_tls_drivers + identity_trust_drivers + agility_drivers + dar_drivers + motion_drivers
    )
    all_drivers_sorted = sorted(all_drivers, key=lambda x: (-abs(x[1]), x[0]))
    top_drivers = [{"reason": reason, "points": points} for reason, points in all_drivers_sorted[:5]]

    # Unassessed categories carry None (not their raw 0-25 number). NOTE for
    # renderers (188 review CR-01): `subscores.get(key, "—")` does NOT render an
    # em dash for these — the key is always PRESENT with value None, and
    # dict.get only returns its default for a MISSING key. Every subscore-table
    # surface must branch explicitly on `value is None` and substitute "—"
    # itself (see executive.py/writer.py/docx_renderer.py/report.html.j2).
    subscores: Dict[str, Optional[int]] = {
        name: (score if ok else None) for name, (score, ok) in category_table.items()
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
