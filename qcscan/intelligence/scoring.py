from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

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
    "agility_high_impact_ratio": 14.0,
    "agility_unknown_ratio": 6.0,
    "agility_rsa_only_penalty": 8.0,
    "agility_has_ecdsa_bonus": 4.0,
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
    weights: Mapping[str, float] | None = None,
) -> Dict[str, Any]:
    w = dict(SCORE_WEIGHTS)
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

    total_score = int(hygiene_score + modern_tls_score + identity_trust_score + agility_score)
    rating = _rating(total_score)

    all_drivers: List[Tuple[str, int]] = (
        hygiene_drivers + modern_tls_drivers + identity_trust_drivers + agility_drivers
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
        },
        "drivers": top_drivers,
    }
