from __future__ import annotations

from typing import Any, Dict, List, Tuple


_SEVERITY_RANK = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _error_category(desc: str) -> str:
    if not desc:
        return ""
    if ":" in desc:
        return desc.split(":", 1)[0].strip()
    return desc.strip()


def _has_legacy_tls_versions(ep: Any) -> bool:
    ver = (getattr(ep, "tls_version", "") or "").strip()
    if ver in {"TLSv1", "TLSv1.1"}:
        return True

    supported = (getattr(ep, "tls_supported_versions", "") or "").strip()
    if not supported:
        return False
    versions = {v.strip() for v in supported.split(",") if v.strip()}
    return bool({"TLSv1", "TLSv1.1"} & versions)


def _normalize_finding(f: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(f)
    title = (out.get("title") or "").strip()

    if title in {"Plaintext HTTP service detected", "HTTP on TLS-designated port"}:
        out["severity"] = "HIGH"
    elif title in {"Unknown open service", "TLS handshake blocked assessment"}:
        out["severity"] = "MEDIUM"
    elif title == "Legacy TLS versions allowed (TLS 1.0/1.1)":
        out["severity"] = "LOW"
    elif title in {"SSH quantum planning advisory", "mTLS required", "Informational protocol observation"}:
        out["severity"] = "INFO"

    return out


def _dedupe_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[Tuple[str, int, str, str], Dict[str, Any]] = {}

    for finding in findings:
        f = _normalize_finding(finding)
        key = (
            f.get("host", "") or "",
            int(f.get("port") or 0),
            f.get("title", "") or "",
            f.get("recommendation", "") or "",
        )
        prior = deduped.get(key)
        if prior is None:
            deduped[key] = f
            continue
        cur_rank = _SEVERITY_RANK.get(str(f.get("severity", "INFO")).upper(), 0)
        prev_rank = _SEVERITY_RANK.get(str(prior.get("severity", "INFO")).upper(), 0)
        if cur_rank > prev_rank:
            deduped[key] = f

    return [
        deduped[k]
        for k in sorted(
            deduped.keys(),
            key=lambda x: (x[0], x[1], x[2], x[3]),
        )
    ]


def _postprocess_findings(cfg, endpoints, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    v3.7.1 classifier patch companion:
      - If protocol classifier labels HTTP on ports we *expect* to be TLS, treat as MISCONFIG.
      - If TLS is blocked due to MTLS_REQUIRED, avoid calling it plaintext.
    """
    tls_ports = set(getattr(cfg.scan, "ports_tls", []) or [])

    # Map endpoint protocol/detail for quick context
    ep_map: Dict[Tuple[str, int], Any] = {}
    for e in endpoints:
        ep_map[(getattr(e, "host", ""), int(getattr(e, "port", 0)))] = e

    for f in findings:
        host = f.get("host", "")
        port = int(f.get("port") or 0)
        title = (f.get("title") or "").strip()

        ep = ep_map.get((host, port))
        proto = getattr(ep, "protocol", "") if ep else ""
        detail = ""
        if ep:
            detail = getattr(ep, "tls_blocker_reason", None) or getattr(ep, "tls_version", "")

        # Upgrade HTTP findings on TLS-designated ports
        if title == "Plaintext HTTP service detected" and port in tls_ports:
            # If classifier says TLS but blocked, don't label it as plaintext
            if proto == "TLS" and detail == "MTLS_REQUIRED":
                f["severity"] = "INFO"
                f["title"] = "mTLS required"
                f["recommendation"] = (
                    "Service appears to require client authentication for TLS handshake. "
                    "Validate client certificate requirements, trust chain, and onboarding flow."
                )
            elif proto == "TLS" and detail in {"TLS_HANDSHAKE_FAILED", "TIMEOUT"}:
                f["severity"] = "MEDIUM"
                f["title"] = "TLS handshake blocked assessment"
                f["recommendation"] = (
                    "TLS handshake failure is blocking accurate cryptographic assessment. "
                    "Validate endpoint handshake policy, SNI expectations, and network path."
                )
            else:
                f["severity"] = "HIGH"
                f["title"] = "HTTP on TLS-designated port"
                f["recommendation"] = (
                    "A plaintext HTTP service responded on a port expected to be TLS/HTTPS. "
                    "Correct service configuration (enable TLS) or update port policy/registry."
                )

    return _dedupe_findings(findings)


def evaluate_endpoints(cfg, endpoints) -> List[Dict[str, Any]]:
    """
    Baseline findings generator + postprocessing.

    If you have a richer ruleset, keep it and call _postprocess_findings() at the end.
    """
    findings: List[Dict[str, Any]] = []

    for e in endpoints:
        host = getattr(e, "host", "")
        port = int(getattr(e, "port", 0))
        proto = getattr(e, "protocol", "UNKNOWN")

        # Scan errors are normalized into blocker/advisory findings.
        scan_err = getattr(e, "scan_error", None)
        if scan_err:
            err_cat = _error_category(scan_err)
            if proto == "TLS" and err_cat in {"TLS_HANDSHAKE_FAILED", "TIMEOUT"}:
                findings.append({
                    "severity": "MEDIUM",
                    "host": host,
                    "port": port,
                    "title": "TLS handshake blocked assessment",
                    "recommendation": "TLS handshake failure is blocking accurate cryptographic assessment. Validate handshake policy and endpoint expectations.",
                    "detail": scan_err,
                })
                continue
            if proto == "TLS" and err_cat == "MTLS_REQUIRED":
                findings.append({
                    "severity": "INFO",
                    "host": host,
                    "port": port,
                    "title": "mTLS required",
                    "recommendation": "Confirm client certificate requirements and document trust chain and onboarding process.",
                    "detail": scan_err,
                })
                continue
            findings.append({
                "severity": "INFO",
                "host": host,
                "port": port,
                "title": "Informational protocol observation",
                "recommendation": "Review protocol behavior and endpoint availability details.",
                "detail": scan_err,
            })
            continue

        if proto == "HTTP":
            findings.append({
                "severity": "HIGH",
                "host": host,
                "port": port,
                "title": "Plaintext HTTP service detected",
                "recommendation": "Migrate management/application endpoints to HTTPS/TLS where feasible.",
            })

        if proto == "TLS":
            if _has_legacy_tls_versions(e):
                findings.append({
                    "severity": "LOW",
                    "host": host,
                    "port": port,
                    "title": "Legacy TLS versions allowed (TLS 1.0/1.1)",
                    "recommendation": "Disable TLS 1.0/1.1 and standardize on TLS 1.2+ (prefer TLS 1.3).",
                })

        if proto == "SSH":
            findings.append({
                "severity": "INFO",
                "host": host,
                "port": port,
                "title": "SSH quantum planning advisory",
                "recommendation": "Inventory SSH host keys and KEX algorithms; evaluate lifecycle and PQC readiness.",
            })

        if proto == "UNKNOWN":
            findings.append({
                "severity": "MEDIUM",
                "host": host,
                "port": port,
                "title": "Unknown open service",
                "recommendation": "Fingerprint with a deeper probe or validate service ownership and purpose.",
            })

    return _postprocess_findings(cfg, endpoints, findings)
