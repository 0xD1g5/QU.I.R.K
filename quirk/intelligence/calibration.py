from typing import Any, Dict


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic deep merge:
    - dict values merge recursively
    - non-dict values override
    """
    out: Dict[str, Any] = {}
    for k in base.keys():
        out[k] = base[k]

    for k, v in (overrides or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _profile_default() -> Dict[str, Any]:
    # Keep minimal and defensible; tune later in v3.9 tickets
    return {
        "scoring": {
            "subscore_max": 25,
            "weights": {
                "hygiene": 25,
                "modern_tls": 25,
                "identity_trust": 25,
                "agility_signals": 25,
            },
            "thresholds": {
                "tls13_good_coverage_pct": 70,
                "scan_error_rate_warn_pct": 15,
                "unknown_ratio_warn_pct": 10,
                "expiring_days": 30,
            },
        },
        "confidence": {
            "start": 100,
            "penalties": {
                "low_coverage": 25,
                "scan_errors": 20,
                "unknown_ratio": 15,
                "low_tls_enum_coverage": 15,
            },
            "thresholds": {
                "min_success_coverage_pct": 80,
                "max_scan_error_rate_pct": 10,
                "max_unknown_ratio_pct": 10,
                "min_tls_enum_coverage_pct": 40,
            },
        },
        "roadmap": {
            "max_items": 12,
            "thresholds": {
                "plaintext_http_trigger": 1,
                "unknown_services_trigger": 1,
                "expiring_trigger": 1,
                "tls13_low_coverage_pct": 50,
            },
        },
    }


def _profile_strict() -> Dict[str, Any]:
    # Stricter thresholds, larger penalties
    base = _profile_default()
    strict_overrides = {
        "confidence": {
            "penalties": {
                "low_coverage": 30,
                "scan_errors": 25,
                "unknown_ratio": 20,
                "low_tls_enum_coverage": 20,
            },
            "thresholds": {
                "min_success_coverage_pct": 90,
                "max_scan_error_rate_pct": 5,
                "max_unknown_ratio_pct": 5,
                "min_tls_enum_coverage_pct": 60,
            },
        },
        "scoring": {
            "thresholds": {
                "tls13_good_coverage_pct": 80,
                "expiring_days": 45,
            }
        },
    }
    return _deep_merge(base, strict_overrides)


def _profile_lenient() -> Dict[str, Any]:
    # More forgiving penalties/thresholds
    base = _profile_default()
    lenient_overrides = {
        "confidence": {
            "penalties": {
                "low_coverage": 15,
                "scan_errors": 12,
                "unknown_ratio": 8,
                "low_tls_enum_coverage": 8,
            },
            "thresholds": {
                "min_success_coverage_pct": 70,
                "max_scan_error_rate_pct": 20,
                "max_unknown_ratio_pct": 20,
                "min_tls_enum_coverage_pct": 25,
            },
        },
        "scoring": {
            "thresholds": {
                "tls13_good_coverage_pct": 60,
                "expiring_days": 14,
            }
        },
    }
    return _deep_merge(base, lenient_overrides)


def get_profile(name: str) -> Dict[str, Any]:
    n = (name or "default").strip().lower()
    if n == "strict":
        return _profile_strict()
    if n == "lenient":
        return _profile_lenient()
    return _profile_default()


def get_calibration(cfg) -> Dict[str, Any]:
    """
    Returns a resolved calibration dict:
    - profile baseline
    - overrides applied
    - includes intelligence_version + profile name for reporting
    """
    prof = getattr(getattr(cfg, "intelligence", None), "calibration_profile", "default") or "default"
    overrides = getattr(getattr(cfg, "intelligence", None), "calibration_overrides", {}) or {}
    intelligence_version = getattr(getattr(cfg, "intelligence", None), "intelligence_version", "3.9.0") or "3.9.0"

    base = get_profile(prof)
    resolved = _deep_merge(base, overrides)

    return {
        "intelligence_version": intelligence_version,
        "profile": prof,
        "resolved": resolved,
    }