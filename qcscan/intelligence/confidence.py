from __future__ import annotations

from typing import Any, Dict, Mapping

CONFIDENCE_WEIGHTS: Dict[str, float] = {
    "coverage_ratio": 0.35,
    "scan_error_ratio": 0.30,
    "unknown_ratio": 0.15,
    "tls_enum_coverage_ratio": 0.20,
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


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def _rating(score: int) -> str:
    if score >= 85:
        return "HIGH"
    if score >= 65:
        return "MEDIUM"
    if score >= 40:
        return "LOW"
    return "VERY_LOW"


def compute_confidence(
    evidence: Mapping[str, Any],
    *,
    weights: Mapping[str, float] | None = None,
) -> Dict[str, Any]:
    w = dict(CONFIDENCE_WEIGHTS)
    if weights:
        for key, value in weights.items():
            w[key] = _as_float(value)

    totals = evidence.get("totals", {}) if isinstance(evidence.get("totals", {}), Mapping) else {}
    protocol_counts = evidence.get("protocol_counts", {}) if isinstance(evidence.get("protocol_counts", {}), Mapping) else {}
    scan_error = evidence.get("scan_error", {}) if isinstance(evidence.get("scan_error", {}), Mapping) else {}

    endpoints = max(0, _as_int(totals.get("endpoints", 0)))
    tls_count = max(0, _as_int(protocol_counts.get("TLS", 0)))
    ssh_count = max(0, _as_int(protocol_counts.get("SSH", 0)))
    unknown_count = max(0, _as_int(protocol_counts.get("UNKNOWN", 0)))

    scan_error_ratio = _clamp(_as_float(scan_error.get("rate", 0.0)), 0.0, 1.0)

    if endpoints == 0:
        return {
            "confidence_score": 0,
            "confidence_rating": "NO_DATA",
            "factor_breakdown": {
                "coverage_ratio": {"value": 0.0, "weight": w["coverage_ratio"], "points": 0.0},
                "scan_error_ratio": {"value": 0.0, "weight": w["scan_error_ratio"], "points": 0.0},
                "unknown_ratio": {"value": 0.0, "weight": w["unknown_ratio"], "points": 0.0},
                "tls_enum_coverage_ratio": {"value": 0.0, "weight": w["tls_enum_coverage_ratio"], "points": 0.0},
            },
        }

    coverage_ratio = _clamp((tls_count + ssh_count) / endpoints, 0.0, 1.0)
    unknown_ratio = _clamp(unknown_count / endpoints, 0.0, 1.0)

    tls_enum_coverage_ratio = _as_float(evidence.get("tls_enum_coverage_ratio", -1.0))
    if tls_enum_coverage_ratio < 0.0:
        tls_enum_coverage_pct = _as_float(evidence.get("tls_enum_coverage_pct", -1.0))
        if tls_enum_coverage_pct >= 0.0:
            tls_enum_coverage_ratio = tls_enum_coverage_pct / 100.0
    if tls_enum_coverage_ratio < 0.0:
        tls_enum_coverage_ratio = 1.0 if tls_count == 0 else 0.0
    tls_enum_coverage_ratio = _clamp(tls_enum_coverage_ratio, 0.0, 1.0)

    points_coverage = 100.0 * w["coverage_ratio"] * coverage_ratio
    points_scan_error = 100.0 * w["scan_error_ratio"] * (1.0 - scan_error_ratio)
    points_unknown = 100.0 * w["unknown_ratio"] * (1.0 - unknown_ratio)
    points_tls_enum = 100.0 * w["tls_enum_coverage_ratio"] * tls_enum_coverage_ratio

    score = int(round(_clamp(points_coverage + points_scan_error + points_unknown + points_tls_enum, 0.0, 100.0)))
    rating = _rating(score)

    return {
        "confidence_score": score,
        "confidence_rating": rating,
        "factor_breakdown": {
            "coverage_ratio": {
                "value": round(coverage_ratio, 4),
                "weight": round(w["coverage_ratio"], 4),
                "points": round(points_coverage, 2),
            },
            "scan_error_ratio": {
                "value": round(scan_error_ratio, 4),
                "weight": round(w["scan_error_ratio"], 4),
                "points": round(points_scan_error, 2),
            },
            "unknown_ratio": {
                "value": round(unknown_ratio, 4),
                "weight": round(w["unknown_ratio"], 4),
                "points": round(points_unknown, 2),
            },
            "tls_enum_coverage_ratio": {
                "value": round(tls_enum_coverage_ratio, 4),
                "weight": round(w["tls_enum_coverage_ratio"], 4),
                "points": round(points_tls_enum, 2),
            },
        },
    }
