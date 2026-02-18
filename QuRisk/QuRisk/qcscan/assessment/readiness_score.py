from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import Counter
from typing import Any, Dict, List, Tuple

from qcscan.assessment.operator_context import get_context


@dataclass
class ScoreBreakdown:
    crypto_strength: int
    protocol_modernity: int
    exposure_surface: int
    hygiene: int
    agility_indicators: int
    drivers: List[Tuple[str, int]]
    coverage: Dict[str, Any]
    context: Dict[str, Any]


@dataclass
class ReadinessScore:
    score: int
    rating: str
    breakdown: ScoreBreakdown

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clamp(v: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, v))


def _rating(score: int) -> str:
    if score >= 85:
        return "STRONG"
    if score >= 70:
        return "GOOD"
    if score >= 55:
        return "MODERATE"
    if score >= 40:
        return "WEAK"
    return "CRITICAL"


def _count_by_protocol(endpoints) -> Counter:
    return Counter([(getattr(e, "protocol", "UNKNOWN") or "UNKNOWN") for e in endpoints])


def _extract_error_categories(endpoints) -> Counter:
    cats = Counter()
    for e in endpoints:
        err = getattr(e, "scan_error", None)
        if not err:
            continue
        if ":" in err:
            cats[err.split(":", 1)[0].strip()] += 1
        else:
            cats["UNCLASSIFIED"] += 1
    return cats


def _context_risk_multiplier(ctx: Dict[str, Any]) -> Tuple[int, List[Tuple[str, int]]]:
    drivers: List[Tuple[str, int]] = []
    penalty = 0

    data_types = [str(x).upper() for x in (ctx.get("data_types") or [])]
    longevity = int(ctx.get("data_longevity_years") or 7)
    exposure = (ctx.get("exposure") or "mixed").lower()

    if any(x in data_types for x in ["PCI", "PHI"]):
        penalty += 5
        drivers.append(("Sensitive regulated data present (PCI/PHI)", 5))
    if "FINANCIAL" in data_types:
        penalty += 3
        drivers.append(("Financial data present", 3))
    if "TRADE" in data_types or "TRADE SECRETS" in data_types:
        penalty += 3
        drivers.append(("Trade secret/IP data present", 3))

    if longevity >= 10:
        penalty += 5
        drivers.append(("Long-lived confidentiality requirement (10+ years)", 5))
    elif longevity >= 7:
        penalty += 3
        drivers.append(("Moderate-long confidentiality requirement (7+ years)", 3))
    elif longevity >= 3:
        penalty += 1
        drivers.append(("Confidentiality requirement (3+ years)", 1))

    if exposure == "internet":
        penalty += 5
        drivers.append(("High internet exposure", 5))
    elif exposure == "mixed":
        penalty += 2
        drivers.append(("Mixed exposure (internal + internet-facing)", 2))

    return penalty, drivers


def compute_readiness_score(cfg, endpoints, findings) -> ReadinessScore:
    ctx = get_context(cfg)
    drivers: List[Tuple[str, int]] = []

    proto_counts = _count_by_protocol(endpoints)
    err_cats = _extract_error_categories(endpoints)

    tls_ok = [e for e in endpoints if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)]
    ssh_ok = [e for e in endpoints if getattr(e, "protocol", "") == "SSH" and not getattr(e, "scan_error", None)]
    http_plain = [e for e in endpoints if getattr(e, "protocol", "") == "HTTP"]
    unknown_open = [e for e in endpoints if getattr(e, "protocol", "") == "UNKNOWN"]

    crypto_strength = 25
    protocol_modernity = 20
    exposure_surface = 20
    hygiene = 20
    agility_indicators = 15

    # --- Crypto Strength ---
    for e in tls_ok:
        alg = getattr(e, "cert_pubkey_alg", None)
        size = getattr(e, "cert_pubkey_size", None)

        if alg == "RSA":
            if size is not None and size < 2048:
                crypto_strength -= 10
                drivers.append(("RSA key < 2048 detected", 10))
            elif size is not None and size < 3072:
                crypto_strength -= 2
                drivers.append(("RSA-2048 widespread (quantum transition needed)", 2))
        elif alg in ("ECDSA", "Ed25519", "Ed448"):
            pass
        elif alg in (None, "", "Unknown"):
            crypto_strength -= 3
            drivers.append(("Unknown certificate public key algorithm", 3))

    crypto_strength = _clamp(crypto_strength, 0, 25)

    # --- Protocol Modernity (v3.6: use supported versions) ---
    for e in tls_ok:
        supported = (getattr(e, "tls_supported_versions", "") or "").split(",") if getattr(e, "tls_supported_versions", None) else []
        ver = getattr(e, "tls_version", None)

        # Penalize if legacy versions are enabled even if negotiated isn't legacy
        if "TLSv1" in supported or "TLSv1.1" in supported:
            protocol_modernity -= 8
            drivers.append(("Legacy TLS versions enabled (TLS 1.0/1.1)", 8))
        elif ver == "TLSv1.2":
            protocol_modernity -= 2
            drivers.append(("TLS 1.2 present (TLS 1.3 recommended)", 2))

        # Penalize weak cipher allowance
        if bool(getattr(e, "tls_weak_ciphers_present", False)):
            protocol_modernity -= 4
            drivers.append(("Weak/legacy cipher suites enabled", 4))

    protocol_modernity = _clamp(protocol_modernity, 0, 20)

    # --- Exposure Surface ---
    if len(tls_ok) + len(ssh_ok) == 0:
        exposure_surface -= 10
        drivers.append(("No successful TLS/SSH deep scans (visibility gap)", 10))
    if len(http_plain) > 0:
        penalty = min(8, 1 + len(http_plain) // 3)
        exposure_surface -= penalty
        drivers.append(("Plaintext HTTP services detected", penalty))
    if len(unknown_open) > 0:
        penalty = min(6, 1 + len(unknown_open) // 5)
        exposure_surface -= penalty
        drivers.append(("Unknown open services detected", penalty))

    exposure_surface = _clamp(exposure_surface, 0, 20)

    # --- Hygiene ---
    sev_counts = Counter([f.get("severity", "UNKNOWN") for f in findings])
    hygiene -= min(12, sev_counts.get("CRITICAL", 0) * 6)
    hygiene -= min(8, sev_counts.get("HIGH", 0) * 2)
    if sev_counts.get("CRITICAL", 0) > 0:
        drivers.append(("Critical hygiene issues present", min(12, sev_counts.get("CRITICAL", 0) * 6)))
    if sev_counts.get("HIGH", 0) > 0:
        drivers.append(("High severity items present", min(8, sev_counts.get("HIGH", 0) * 2)))
    hygiene = _clamp(hygiene, 0, 20)

    # --- Agility Indicators ---
    not_tls = err_cats.get("NOT_TLS_ON_PORT", 0)
    timeout = err_cats.get("TIMEOUT", 0)
    if not_tls > 0:
        penalty = min(6, 1 + not_tls // 25)
        agility_indicators -= penalty
        drivers.append(("Non-TLS services on TLS-like ports (standardization gap)", penalty))
    if timeout > 0:
        penalty = min(6, 1 + timeout // 50)
        agility_indicators -= penalty
        drivers.append(("Filtered/segmented scan visibility (coverage gap)", penalty))
    agility_indicators = _clamp(agility_indicators, 0, 15)

    total = crypto_strength + protocol_modernity + exposure_surface + hygiene + agility_indicators
    total = _clamp(total, 0, 100)

    # Context weighting
    ctx_penalty, ctx_drivers = _context_risk_multiplier(ctx)
    if ctx_penalty:
        total = _clamp(total - ctx_penalty, 0, 100)
        drivers.extend(ctx_drivers)

    # Crown jewels bump
    cj = set([x.strip() for x in (ctx.get("crown_jewels") or []) if x.strip()])
    if cj:
        touched = 0
        for f in findings:
            h = str(f.get("host") or "").strip()
            if h in cj:
                touched += 1
        if touched > 0:
            bump = min(5, 1 + touched // 3)
            total = _clamp(total - bump, 0, 100)
            drivers.append(("Findings impact crown jewels (critical systems)", bump))

    merged = {}
    for label, pts in drivers:
        merged[label] = max(merged.get(label, 0), pts)
    top_drivers = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:10]

    breakdown = ScoreBreakdown(
        crypto_strength=crypto_strength * 4,
        protocol_modernity=protocol_modernity * 5,
        exposure_surface=exposure_surface * 5,
        hygiene=hygiene * 5,
        agility_indicators=agility_indicators * 6 + (agility_indicators // 3),
        drivers=top_drivers,
        coverage={
            "protocol_counts": dict(proto_counts),
            "error_categories": dict(err_cats),
            "tls_success": len(tls_ok),
            "ssh_success": len(ssh_ok),
            "http_plain": len(http_plain),
            "unknown_open": len(unknown_open),
            "endpoints_total": len(endpoints),
        },
        context=ctx,
    )

    return ReadinessScore(score=total, rating=_rating(total), breakdown=breakdown)
