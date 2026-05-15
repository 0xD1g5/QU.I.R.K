from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

ROADMAP_VERSION = "1.0.0"

_PHASE_ORDER = {"NOW": 0, "NEXT": 1, "LATER": 2}
_TIMEFRAME_BY_PHASE = {"NOW": "0-30 days", "NEXT": "31-90 days", "LATER": "90+ days"}


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


def _driver_reasons(scoring: Mapping[str, Any]) -> List[str]:
    raw = scoring.get("drivers", [])
    if not isinstance(raw, Sequence):
        return []
    reasons: List[str] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        reason = str(item.get("reason", "")).strip()
        if reason:
            reasons.append(reason)
    return reasons


def _driver_hint(reasons: Sequence[str], keywords: Sequence[str]) -> str:
    keys = tuple(k.lower() for k in keywords)
    for reason in reasons:
        low = reason.lower()
        if any(k in low for k in keys):
            return reason
    return ""


def _why(base: str, hint: str) -> str:
    if hint:
        return f"{base} Driver: {hint.rstrip('.')}."
    return base


def _add_candidate(
    items: Dict[str, Dict[str, Any]],
    *,
    phase: str,
    title: str,
    why: str,
    owner_placeholder: str,
    dependencies: Sequence[str],
    priority: int,
) -> None:
    """Merge a candidate into the items dict by title (D-06 / WR-08 Phase 73).

    Merge rule (the previously-undocumented contract):
      - If `title` is not in `items`, the candidate is inserted as-is.
      - If `title` is already in `items`, the existing entry and the new
        candidate are compared via the tuple
        `(_PHASE_ORDER[phase], int(_priority), title)`.
      - The candidate with the LEXICOGRAPHICALLY-LOWER tuple wins and replaces
        the existing entry. Equal tuples preserve the original (strict `<`).

    This is intentional merge accumulator behavior — earlier-phase / higher-
    priority candidates take precedence regardless of insertion order, so
    callers can register candidates in any order without affecting the final
    roadmap shape. See `.planning/audit-2026-05-08/AUDIT-TASKS.md`
    cbom-intel-reports/WR-08 closure (Phase 73) for context.
    """
    existing = items.get(title)
    candidate = {
        "phase": phase,
        "title": title,
        "why": why,
        "owner_placeholder": owner_placeholder,
        "dependencies": list(dependencies),
        "timeframe": _TIMEFRAME_BY_PHASE[phase],
        "_priority": int(priority),
    }
    if existing is None:
        items[title] = candidate
        return
    old_key = (_PHASE_ORDER[existing["phase"]], int(existing["_priority"]), existing["title"])
    new_key = (_PHASE_ORDER[candidate["phase"]], int(candidate["_priority"]), candidate["title"])
    if new_key < old_key:
        items[title] = candidate


def build_phased_roadmap(
    evidence: Mapping[str, Any],
    scoring: Mapping[str, Any],
    *,
    min_items: int = 6,
    max_items: int = 12,
) -> Dict[str, Any]:
    min_items = max(1, int(min_items))
    max_items = max(min_items, int(max_items))

    totals = (
        evidence.get("totals", {})
        if isinstance(evidence.get("totals", {}), Mapping)
        else {}
    )
    protocol_counts = (
        evidence.get("protocol_counts", {})
        if isinstance(evidence.get("protocol_counts", {}), Mapping)
        else {}
    )
    cert_obs = (
        evidence.get("certificate_observations", {})
        if isinstance(evidence.get("certificate_observations", {}), Mapping)
        else {}
    )
    cert_keys = (
        evidence.get("cert_key_type_counts", {})
        if isinstance(evidence.get("cert_key_type_counts", {}), Mapping)
        else {}
    )
    scan_error = (
        evidence.get("scan_error", {})
        if isinstance(evidence.get("scan_error", {}), Mapping)
        else {}
    )
    sev = (
        evidence.get("finding_severity_counts", {})
        if isinstance(evidence.get("finding_severity_counts", {}), Mapping)
        else {}
    )

    endpoints = max(0, _as_int(totals.get("endpoints", 0)))
    unknown_count = max(0, _as_int(protocol_counts.get("UNKNOWN", 0)))
    plaintext_http_count = max(0, _as_int(evidence.get("plaintext_http_count", 0)))
    http_on_tls_count = max(0, _as_int(evidence.get("http_on_tls_port_count", 0)))
    mtls_present = max(0, _as_int(evidence.get("mtls_present_count", 0)))
    expired_count = max(0, _as_int(cert_obs.get("expired_count", 0)))
    expiring_count = max(0, _as_int(cert_obs.get("expiring_count", 0)))
    self_signed_count = max(0, _as_int(cert_obs.get("self_signed_count", 0)))
    high_impact = max(0, _as_int(sev.get("HIGH", 0)) + _as_int(sev.get("CRITICAL", 0)))
    legacy_tls_count = max(0, _as_int(sev.get("LOW", 0)))
    scan_error_rate = max(0.0, min(1.0, _as_float(scan_error.get("rate", 0.0))))
    tls_enum_cov = max(
        0.0,
        min(1.0, _as_float(evidence.get("tls_enum_coverage_ratio", 1.0))),
    )
    rsa_count = max(0, _as_int(cert_keys.get("RSA", 0)))
    ecdsa_count = max(0, _as_int(cert_keys.get("ECDSA", 0)))

    reasons = _driver_reasons(scoring)
    items: Dict[str, Dict[str, Any]] = {}

    if plaintext_http_count + http_on_tls_count > 0:
        _add_candidate(
            items,
            phase="NOW",
            title="Remove plaintext HTTP exposure",
            why=_why(
                (
                    "Plaintext HTTP signals were observed on "
                    f"{plaintext_http_count + http_on_tls_count} endpoint(s)."
                ),
                _driver_hint(reasons, ("plaintext", "http on tls")),
            ),
            owner_placeholder="[owner: platform-security]",
            dependencies=("Service inventory", "TLS termination standard"),
            priority=10,
        )

    if high_impact > 0:
        _add_candidate(
            items,
            phase="NOW",
            title="Triage high-impact findings",
            why=_why(
                (
                    f"There are {high_impact} high-impact finding(s) requiring "
                    "immediate remediation sequencing."
                ),
                _driver_hint(reasons, ("high-impact", "high severity")),
            ),
            owner_placeholder="[owner: security-operations]",
            dependencies=("Finding ownership map",),
            priority=20,
        )

    if expired_count > 0:
        _add_candidate(
            items,
            phase="NOW",
            title="Replace expired certificates",
            why=_why(
                f"{expired_count} certificate(s) are already expired.",
                _driver_hint(reasons, ("expired certificate",)),
            ),
            owner_placeholder="[owner: pki-team]",
            dependencies=("Certificate inventory", "CA issuance access"),
            priority=30,
        )

    if scan_error_rate >= 0.2:
        _add_candidate(
            items,
            phase="NOW",
            title="Stabilize scan reliability",
            why=_why(
                (
                    f"Scan error rate is {round(scan_error_rate * 100, 1)}%, "
                    "which weakens evidence quality."
                ),
                _driver_hint(reasons, ("scan error", "visibility blocker")),
            ),
            owner_placeholder="[owner: network-engineering]",
            dependencies=("Scanner connectivity baseline",),
            priority=40,
        )

    if unknown_count > 0:
        _add_candidate(
            items,
            phase="NEXT",
            title="Classify unknown open services",
            why=_why(
                (
                    f"{unknown_count} unknown open service(s) need protocol "
                    "and ownership classification."
                ),
                _driver_hint(reasons, ("unknown service", "unknown open")),
            ),
            owner_placeholder="[owner: asset-management]",
            dependencies=("Service inventory", "CMDB ownership data"),
            priority=50,
        )

    if expiring_count > 0:
        _add_candidate(
            items,
            phase="NEXT",
            title="Renew near-expiry certificates",
            why=_why(
                (
                    f"{expiring_count} certificate(s) are expiring within "
                    "the configured window."
                ),
                _driver_hint(reasons, ("expiring certificate",)),
            ),
            owner_placeholder="[owner: pki-operations]",
            dependencies=("Renewal runbook", "Certificate ownership"),
            priority=60,
        )

    if self_signed_count > 0:
        _add_candidate(
            items,
            phase="NEXT",
            title="Migrate self-signed certificates to managed PKI",
            why=_why(
                f"{self_signed_count} self-signed certificate(s) reduce trust consistency.",
                _driver_hint(reasons, ("self-signed",)),
            ),
            owner_placeholder="[owner: identity-security]",
            dependencies=("Managed PKI policy", "Service migration plan"),
            priority=70,
        )

    if legacy_tls_count > 0:
        _add_candidate(
            items,
            phase="NEXT",
            title="Disable legacy TLS versions",
            why=_why(
                "Legacy TLS usage was detected and should be phased out with exception tracking.",
                _driver_hint(reasons, ("legacy tls",)),
            ),
            owner_placeholder="[owner: platform-architecture]",
            dependencies=("Client compatibility matrix", "Change window approvals"),
            priority=80,
        )

    if tls_enum_cov < 0.85:
        _add_candidate(
            items,
            phase="NEXT",
            title="Increase TLS enumeration coverage",
            why=_why(
                (
                    f"TLS enum coverage is {round(tls_enum_cov * 100, 1)}%, "
                    "limiting modernization prioritization accuracy."
                ),
                _driver_hint(reasons, ("assessment visibility", "tls enum")),
            ),
            owner_placeholder="[owner: security-engineering]",
            dependencies=("Scanner profile tuning",),
            priority=90,
        )

    if rsa_count > 0 and ecdsa_count == 0:
        _add_candidate(
            items,
            phase="LATER",
            title="Plan ECDSA adoption",
            why=_why(
                (
                    "Certificate portfolio appears RSA-only; introduce ECDSA "
                    "rollout planning for agility."
                ),
                _driver_hint(reasons, ("rsa-only", "ecdsa adoption")),
            ),
            owner_placeholder="[owner: cryptography-architecture]",
            dependencies=("CA support validation", "Client support matrix"),
            priority=100,
        )

    if mtls_present > 0:
        _add_candidate(
            items,
            phase="LATER",
            title="Standardize mTLS lifecycle operations",
            why=_why(
                (
                    "mTLS signals are present; operationalize issuance, "
                    "rotation, and revocation controls consistently."
                ),
                _driver_hint(reasons, ("mtls",)),
            ),
            owner_placeholder="[owner: identity-platform]",
            dependencies=("Client cert lifecycle policy", "Secrets distribution channel"),
            priority=110,
        )

    # Deterministic baseline items to ensure 6-12 roadmap entries.
    baseline = [
        (
            "NOW",
            "Assign remediation owners and SLAs",
            "Define named owners and SLA targets for each open finding.",
            "[owner: security-program]",
            ("Finding register",),
            900,
        ),
        (
            "NEXT",
            "Automate evidence refresh cadence",
            "Run periodic evidence collection and scoring for trend visibility.",
            "[owner: secops-automation]",
            ("Scheduler setup",),
            910,
        ),
        (
            "LATER",
            "Establish crypto governance review",
            "Adopt recurring governance checkpoints for roadmap status "
            "and exceptions.",
            "[owner: security-leadership]",
            ("Quarterly reporting format",),
            920,
        ),
    ]
    for phase, title, why, owner, deps, priority in baseline:
        if len(items) >= min_items:
            break
        _add_candidate(
            items,
            phase=phase,
            title=title,
            why=why,
            owner_placeholder=owner,
            dependencies=deps,
            priority=priority,
        )

    sorted_items = sorted(
        items.values(),
        key=lambda x: (
            _PHASE_ORDER.get(x["phase"], 99),
            int(x["_priority"]),
            x["title"],
        ),
    )[:max_items]

    final_items = []
    phase_counts = {"NOW": 0, "NEXT": 0, "LATER": 0}
    for item in sorted_items:
        phase = item["phase"]
        phase_counts[phase] += 1
        final_items.append(
            {
                "phase": phase,
                "title": item["title"],
                "why": item["why"],
                "owner_placeholder": item["owner_placeholder"],
                "dependencies": list(item["dependencies"]),
                "timeframe": item["timeframe"],
            }
        )

    # If no evidence exists, keep deterministic minimum plan shape.
    if endpoints == 0 and len(final_items) < min_items:
        fallback = [
            {
                "phase": "NOW",
                "title": "Collect initial asset scope",
                "why": "No endpoints were observed; establish baseline scope before scoring.",
                "owner_placeholder": "[owner: asset-management]",
                "dependencies": ["Target inventory"],
                "timeframe": _TIMEFRAME_BY_PHASE["NOW"],
            },
            {
                "phase": "NEXT",
                "title": "Run baseline discovery and fingerprinting",
                "why": (
                    "Initial scan evidence is required to compute meaningful "
                    "intelligence outputs."
                ),
                "owner_placeholder": "[owner: security-engineering]",
                "dependencies": ["Collect initial asset scope"],
                "timeframe": _TIMEFRAME_BY_PHASE["NEXT"],
            },
            {
                "phase": "LATER",
                "title": "Establish recurring readiness reporting",
                "why": "Consistent trend reporting is needed once baseline evidence exists.",
                "owner_placeholder": "[owner: security-program]",
                "dependencies": ["Run baseline discovery and fingerprinting"],
                "timeframe": _TIMEFRAME_BY_PHASE["LATER"],
            },
        ]
        for item in fallback:
            if len(final_items) >= min_items:
                break
            if all(existing["title"] != item["title"] for existing in final_items):
                final_items.append(item)
                phase_counts[item["phase"]] += 1

    return {
        "roadmap_version": ROADMAP_VERSION,
        "item_count": len(final_items),
        "phase_counts": phase_counts,
        "items": final_items,
    }
