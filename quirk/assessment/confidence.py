from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def _error_category(desc: str) -> str:
    if not desc:
        return "UNKNOWN"
    if ":" in desc:
        return desc.split(":", 1)[0].strip()
    return "UNCLASSIFIED"


def compute_confidence(cfg, endpoints) -> Dict[str, Any]:
    """
    v3.7 Confidence Engine (simple, defensible):
      - Coverage (TLS+SSH successful / total targets)
      - Enumeration completeness (TLS endpoints with tls_supported_versions present)
      - Blockers (timeouts, filtered, NOT_TLS_ON_PORT)
    """
    total = len(endpoints)

    tls = [e for e in endpoints if getattr(e, "protocol", "") == "TLS"]
    ssh = [e for e in endpoints if getattr(e, "protocol", "") == "SSH"]

    tls_ok = [e for e in tls if not getattr(e, "scan_error", None)]
    ssh_ok = [e for e in ssh if not getattr(e, "scan_error", None)]

    ok_total = len(tls_ok) + len(ssh_ok)
    coverage_pct = 0 if total == 0 else round(100.0 * ok_total / total, 1)

    # TLS enum completeness
    tls_enum_present = [e for e in tls_ok if (getattr(e, "tls_supported_versions", None) or "").strip()]
    tls_enum_pct = 0 if len(tls_ok) == 0 else round(100.0 * len(tls_enum_present) / len(tls_ok), 1)

    # Errors
    err_counts = Counter(_error_category(getattr(e, "scan_error", "")) for e in endpoints if getattr(e, "scan_error", None))
    top_blockers = err_counts.most_common(5)

    # Score heuristic
    score = 70
    # coverage
    if coverage_pct >= 90:
        score += 15
    elif coverage_pct >= 75:
        score += 8
    elif coverage_pct >= 50:
        score += 0
    else:
        score -= 12

    # enum completeness
    if tls_enum_pct >= 90:
        score += 8
    elif tls_enum_pct >= 70:
        score += 3
    elif tls_ok:
        score -= 5

    # blockers
    timeout = err_counts.get("TIMEOUT", 0)
    not_tls = err_counts.get("NOT_TLS_ON_PORT", 0)
    if timeout > 0:
        score -= min(10, 1 + timeout // 25)
    if not_tls > 0:
        score -= min(8, 1 + not_tls // 25)

    score = max(0, min(100, int(score)))

    if score >= 85:
        rating = "HIGH"
    elif score >= 65:
        rating = "MEDIUM"
    else:
        rating = "LOW"

    return {
        "confidence_score": score,
        "confidence_rating": rating,
        "coverage_pct": coverage_pct,
        "tls_enum_coverage_pct": tls_enum_pct,
        "blockers_top": [{"category": c, "count": n} for c, n in top_blockers],
        "counts": {
            "endpoints_total": total,
            "tls_total": len(tls),
            "tls_success": len(tls_ok),
            "ssh_total": len(ssh),
            "ssh_success": len(ssh_ok),
        },
    }

