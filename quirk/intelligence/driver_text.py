from __future__ import annotations

from typing import Any, Dict, List


def polish_drivers(ev: Dict[str, Any], raw_drivers: List[str]) -> List[str]:
    """
    Convert raw driver lines into consulting-grade statements.
    Deterministic: same evidence -> same text.
    Caps at 5 lines.
    """
    ev = ev or {}
    polished: List[str] = []

    def add(s: str) -> None:
        if s and s not in polished:
            polished.append(s)

    ph = int(ev.get("plaintext_http_count", 0) or 0)
    if ph > 0:
        add(
            f"Plaintext HTTP services detected ({ph}) — increases exposure and weakens crypto assurance; "
            "prioritize HTTPS enforcement at these endpoints."
        )

    hotp = int(ev.get("http_on_tls_port_count", 0) or 0)
    if hotp > 0:
        add(
            f"HTTP responded on TLS-designated ports ({hotp}) — indicates misconfiguration or proxy behavior; "
            "validate service intent and correct port/TLS expectations."
        )

    exp = int(ev.get("expired_cert_count", 0) or 0)
    if exp > 0:
        add(
            f"Expired certificates present ({exp}) — breaks trust and increases outage/security risk; "
            "renew immediately and implement lifecycle automation."
        )

    exp30 = int(ev.get("expiring_cert_count", 0) or 0)
    if exp30 > 0:
        add(
            f"Certificates expiring within 30 days ({exp30}) — elevated outage risk; "
            "confirm owners and enforce renewal SLAs/automation."
        )

    ss = int(ev.get("self_signed_cert_count", 0) or 0)
    if ss > 0:
        add(
            f"Self-signed certificates detected ({ss}) — reduces trust assurance; "
            "replace with managed PKI or document approved exceptions."
        )

    ser = float(ev.get("scan_error_rate", 0.0) or 0.0)
    if ser > 0.0:
        pct = int(round(ser * 100))
        add(
            f"Scan errors reduced evidence coverage (~{pct}% of endpoints) — validate reachability/ACLs "
            "and re-run to improve confidence."
        )

    unk = float(ev.get("unknown_service_ratio", 0.0) or 0.0)
    if unk > 0.0:
        pct = int(round(unk * 100))
        add(
            f"Unknown services observed (~{pct}% of endpoints) — reduces inventory confidence; "
            "add fingerprinting/ownership mapping to improve scoring accuracy."
        )

    if len(polished) < 3:
        for d in raw_drivers or []:
            add(str(d).strip())

    return polished[:5]