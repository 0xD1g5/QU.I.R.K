from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

# SCORE_WEIGHTS invariant (D-04, WR-06 — Phase 73 documentation, NOT normalization)
# ----------------------------------------------------------------------------
# These values are ABSOLUTE per-ratio coefficients, NOT probabilities, NOT
# a normalized PMF. Their sum is 261.0 BY DESIGN.
#
# The total_score arithmetic below already clamps to [0, 100] (closed by
# Phase 60 SCORE-01) and `_apply_weighted_impacts` shares score caps across
# these weights — see Phase 60 SCORE-04 / CR-06 closure for the cap-sharing
# rationale that this docstring deliberately preserves.
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
    if score >= 85:
        return "EXCELLENT"
    if score >= 70:
        return "GOOD"
    if score >= 55:
        return "MODERATE"
    if score >= 35:
        return "FAIR"
    return "POOR"


def _apply_weighted_impacts(
    impacts: List[Tuple[str, float]],
    score_cap: float = 25.0,
) -> Tuple[int, List[Tuple[str, int]]]:
    total = score_cap + sum(v for _, v in impacts)
    clamped = _clamp(total, 0.0, score_cap)
    score = int(round(clamped))
    rounded_impacts = [(label, int(round(points))) for label, points in impacts if int(round(points)) != 0]
    return score, rounded_impacts


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
    ]
    identity_trust_score, identity_trust_drivers = _apply_weighted_impacts(identity_trust_impacts)

    agility_impacts: List[Tuple[str, float]] = [
        ("High-impact findings", -_ratio(high_impact, max(findings, 1)) * w["agility_high_impact_ratio"]),
        ("Unknown service inventory", -_ratio(unknown_count, denom) * w["agility_unknown_ratio"]),
    ]
    if rsa_count > 0 and ecdsa_count == 0:
        agility_impacts.append(("RSA-only certificate posture", -w["agility_rsa_only_penalty"]))
    elif ecdsa_count > 0:
        agility_impacts.append(("ECDSA adoption signal", w["agility_has_ecdsa_bonus"]))

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

    total_score = int(_clamp(
        hygiene_score + modern_tls_score + identity_trust_score +
        agility_score + dar_score + motion_score,
        0, 100,
    ))
    rating = _rating(total_score)

    all_drivers: List[Tuple[str, int]] = (
        hygiene_drivers + modern_tls_drivers + identity_trust_drivers + agility_drivers + dar_drivers + motion_drivers
    )
    all_drivers_sorted = sorted(all_drivers, key=lambda x: (-abs(x[1]), x[0]))
    top_drivers = [{"reason": reason, "points": points} for reason, points in all_drivers_sorted[:5]]

    return {
        "score": total_score,
        "rating": rating,
        "subscores": {
            "hygiene": hygiene_score,
            "modern_tls": modern_tls_score,
            "identity_trust": identity_trust_score,
            "agility_signals": agility_score,
            "data_at_rest": dar_score,
            "data_in_motion": motion_score,
        },
        "drivers": top_drivers,
    }
