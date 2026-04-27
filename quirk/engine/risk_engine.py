from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


_SEVERITY_RANK = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

# (version_prefix, severity, eol_label)
_OPENSSL_EOL: List[Tuple[str, str, str]] = [
    ("0.", "CRITICAL", "OpenSSL 0.x"),
    ("1.0.", "CRITICAL", "OpenSSL 1.0.x (EOL Dec 2019)"),
    ("1.1.", "HIGH", "OpenSSL 1.1.x (EOL Sep 2023)"),
    ("3.0.", "HIGH", "OpenSSL 3.0.x (EOL Apr 2026)"),
    ("3.1.", "HIGH", "OpenSSL 3.1.x (EOL Mar 2025)"),
]

_OPENSSL_NAMES = frozenset({"openssl", "libssl", "libssl1.0", "libssl1.0.0", "libssl1.1", "libssl3", "libcrypto", "libcrypto3"})


def _pkg_major(version: str) -> Optional[int]:
    try:
        return int(version.split(".")[0])
    except (ValueError, IndexError, AttributeError):
        return None


def _evaluate_container_package(
    host: str, port: int, pkg_name: str, pkg_version: str
) -> Optional[Dict[str, Any]]:
    name = pkg_name.lower()
    version = pkg_version or ""

    if name in _OPENSSL_NAMES:
        for prefix, sev, label in _OPENSSL_EOL:
            if version.startswith(prefix):
                return {
                    "severity": sev,
                    "host": host,
                    "port": port,
                    "title": f"End-of-life {label} in container image",
                    "recommendation": (
                        f"{label} has reached end-of-life and no longer receives security patches. "
                        "Update the base image to a supported distribution with a current OpenSSL version."
                    ),
                }
        return {
            "severity": "LOW",
            "host": host,
            "port": port,
            "title": f"Container image uses quantum-vulnerable crypto library ({name}@{version})",
            "recommendation": (
                "Plan migration to post-quantum cryptography when NIST PQC standards are adopted upstream."
            ),
        }

    if name == "cryptography":
        major = _pkg_major(version)
        if major is not None and major < 3:
            return {
                "severity": "HIGH",
                "host": host,
                "port": port,
                "title": f"Severely outdated Python cryptography package ({version}) in container image",
                "recommendation": (
                    f"cryptography {version} is over 4 years old with multiple known CVEs. "
                    "Update to the latest version and rebuild the container image."
                ),
            }
        if major is not None and major < 41:
            return {
                "severity": "MEDIUM",
                "host": host,
                "port": port,
                "title": f"Outdated Python cryptography package ({version}) in container image",
                "recommendation": (
                    f"cryptography {version} may have unpatched vulnerabilities. "
                    "Update to the latest version and rebuild the container image."
                ),
            }

    if name == "pyopenssl":
        major = _pkg_major(version)
        if major is not None and major < 20:
            return {
                "severity": "MEDIUM",
                "host": host,
                "port": port,
                "title": f"Outdated pyOpenSSL package ({version}) in container image",
                "recommendation": (
                    f"pyOpenSSL {version} may have known vulnerabilities. "
                    "Update to the latest version."
                ),
            }

    if name in {"libgcrypt20", "libgcrypt"}:
        if version.startswith("1.8."):
            return {
                "severity": "MEDIUM",
                "host": host,
                "port": port,
                "title": f"Outdated libgcrypt ({version}) in container image",
                "recommendation": "libgcrypt 1.8.x is outdated. Update the base image.",
            }

    return {
        "severity": "LOW",
        "host": host,
        "port": port,
        "title": f"Container image contains crypto library ({name}@{version})",
        "recommendation": "Review cryptographic library inventory and plan lifecycle management.",
    }


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


def _chain_verified(ep: Any) -> Optional[bool]:
    """Parse chain_verified from tls_capabilities_json blob; returns None if absent."""
    caps_raw = getattr(ep, "tls_capabilities_json", None)
    if not caps_raw:
        return None
    try:
        caps = json.loads(caps_raw)
        val = caps.get("chain_verified")
        return bool(val) if val is not None else None
    except Exception:
        return None


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

            # BUG-01: Legacy cipher suites (non-AEAD, non-PFS)
            if getattr(e, "tls_legacy_suites_present", False):
                findings.append({
                    "severity": "LOW",
                    "host": host,
                    "port": port,
                    "title": "Legacy TLS cipher suites accepted",
                    "recommendation": (
                        "Disable legacy cipher suites (e.g. AES128-SHA, AES256-SHA) and require "
                        "AEAD suites with forward secrecy (AES-GCM, ChaCha20-Poly1305)."
                    ),
                })

            # BUG-02: Certificate expiry
            cert_not_after = getattr(e, "cert_not_after", None)
            if isinstance(cert_not_after, datetime):
                now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
                # cert_not_after is stored as naive UTC (tzinfo stripped at scan time)
                na = cert_not_after if cert_not_after.tzinfo is None else cert_not_after.astimezone(timezone.utc).replace(tzinfo=None)
                if na < now_naive:
                    findings.append({
                        "severity": "HIGH",
                        "host": host,
                        "port": port,
                        "title": "TLS certificate expired",
                        "recommendation": (
                            f"Certificate expired {na.date()}. Renew immediately — expired certs "
                            "cause trust failures and may block legitimate clients."
                        ),
                    })
                elif na < now_naive + timedelta(days=30):
                    findings.append({
                        "severity": "MEDIUM",
                        "host": host,
                        "port": port,
                        "title": "TLS certificate expiring within 30 days",
                        "recommendation": (
                            f"Certificate expires {na.date()}. Schedule renewal before expiry "
                            "to avoid service disruption."
                        ),
                    })

            # BUG-03: Self-signed or chain-unverified certificate
            cert_issuer = (getattr(e, "cert_issuer", "") or "").strip()
            cert_subject = (getattr(e, "cert_subject", "") or "").strip()
            cv = _chain_verified(e)
            if (cert_issuer and cert_subject and cert_issuer == cert_subject) or cv is False:
                findings.append({
                    "severity": "MEDIUM",
                    "host": host,
                    "port": port,
                    "title": "Self-signed or untrusted TLS certificate",
                    "recommendation": (
                        "Replace with a certificate issued by a trusted CA. Self-signed certs "
                        "cannot establish a verifiable chain of trust for external clients."
                    ),
                })

            # BUG-04: Quantum-vulnerable TLS certificate key algorithm
            cert_pubkey_alg = (getattr(e, "cert_pubkey_alg", "") or "").strip().upper()
            cert_pubkey_size = getattr(e, "cert_pubkey_size", None)
            if cert_pubkey_alg == "RSA":
                if cert_pubkey_size is not None and cert_pubkey_size < 2048:
                    findings.append({
                        "severity": "HIGH",
                        "host": host,
                        "port": port,
                        "title": "TLS certificate uses undersized RSA key",
                        "recommendation": (
                            f"RSA-{cert_pubkey_size} is below the 2048-bit classical minimum and "
                            "is quantum-vulnerable. Migrate to RSA-2048+ or ECDSA P-256, then "
                            "plan post-quantum migration to NIST PQC algorithms."
                        ),
                    })
                else:
                    findings.append({
                        "severity": "MEDIUM",
                        "host": host,
                        "port": port,
                        "title": "TLS certificate uses quantum-vulnerable RSA key",
                        "recommendation": (
                            "RSA is broken by Shor's algorithm on a cryptographically relevant "
                            "quantum computer. Plan migration to NIST-approved PQC algorithms "
                            "(ML-KEM / CRYSTALS-Kyber for key exchange, ML-DSA / Dilithium for signatures)."
                        ),
                    })
            elif cert_pubkey_alg == "ECDSA":
                if cert_pubkey_size is not None and cert_pubkey_size < 256:
                    findings.append({
                        "severity": "HIGH",
                        "host": host,
                        "port": port,
                        "title": "TLS certificate uses undersized ECDSA key",
                        "recommendation": (
                            f"ECDSA-{cert_pubkey_size} is below the P-256 classical minimum and "
                            "is quantum-vulnerable. Migrate to P-256+ and plan post-quantum migration."
                        ),
                    })
                else:
                    findings.append({
                        "severity": "MEDIUM",
                        "host": host,
                        "port": port,
                        "title": "TLS certificate uses quantum-vulnerable ECDSA key",
                        "recommendation": (
                            "ECDSA is broken by Shor's algorithm on a cryptographically relevant "
                            "quantum computer. Plan migration to NIST-approved PQC algorithms."
                        ),
                    })

        if proto == "SSH":
            findings.append({
                "severity": "INFO",
                "host": host,
                "port": port,
                "title": "SSH quantum planning advisory",
                "recommendation": "Inventory SSH host keys and KEX algorithms; evaluate lifecycle and PQC readiness.",
            })

        if proto == "CONTAINER":
            pkg_name = (getattr(e, "cipher_suite", "") or "").strip()
            pkg_version = (getattr(e, "tls_version", "") or "").strip()
            finding = _evaluate_container_package(host, port, pkg_name, pkg_version)
            if finding:
                findings.append(finding)

        if proto == "UNKNOWN":
            findings.append({
                "severity": "MEDIUM",
                "host": host,
                "port": port,
                "title": "Unknown open service",
                "recommendation": "Fingerprint with a deeper probe or validate service ownership and purpose.",
            })

    return _postprocess_findings(cfg, endpoints, findings)


def evaluate_email_endpoints(endpoints) -> List[Dict[str, Any]]:
    """Emit email-specific findings (EMAIL-08, EMAIL-09) for email scanner endpoints.

    Phase 32. Called from run_scan.py after scan_email_targets() completes.
    These findings are merged into the main findings list before _dedupe_findings()
    runs in evaluate_endpoints(); layered findings (D-11) survive because titles differ.
    """
    findings: List[Dict[str, Any]] = []

    for e in endpoints:
        host = getattr(e, "host", "")
        port = int(getattr(e, "port", 0) or 0)
        protocol = getattr(e, "protocol", "") or ""
        cipher = (getattr(e, "cipher_suite", "") or "").upper()
        tls_version = getattr(e, "tls_version", "") or ""
        pfs = getattr(e, "tls_pfs_supported", None)

        # EMAIL-08: STARTTLS downgrade risk — port 25 ONLY, only when TLS actually negotiated
        if port == 25 and protocol == "SMTP-STARTTLS" and tls_version:
            findings.append({
                "severity": "MEDIUM",
                "host": host,
                "port": port,
                "title": "STARTTLS downgrade risk on SMTP",
                "recommendation": (
                    "STARTTLS (opportunistic TLS) is susceptible to stripping attacks that "
                    "cannot be detected by an agentless scanner. An attacker in-path can "
                    "suppress the STARTTLS capability advertisement, forcing plaintext delivery. "
                    "Enforce MTA-STS (RFC 8461) or DANE (RFC 7672) to prevent stripping."
                ),
            })

        # EMAIL-09: Weak RSA key exchange / 3DES / RC4 = HIGH
        is_rsa_kex = (
            cipher.startswith("TLS_RSA_WITH_")
            or "AES128-SHA" in cipher
            or "AES256-SHA" in cipher
            or "3DES" in cipher
            or "RC4" in cipher
        ) and "ECDHE" not in cipher and "DHE-" not in cipher

        if is_rsa_kex and tls_version:
            findings.append({
                "severity": "HIGH",
                "host": host,
                "port": port,
                "title": "Weak cipher suite on email TLS endpoint",
                "recommendation": (
                    "TLS_RSA_WITH_* suites use RSA key exchange (no forward secrecy) and are "
                    "quantum-vulnerable. Disable non-PFS suites and require ECDHE or TLS 1.3 "
                    "cipher suites across all email protocol ports."
                ),
            })
        elif pfs is False and tls_version and tls_version != "TLSv1.3":
            # EMAIL-09 MEDIUM: Non-PFS ECDHE without TLS 1.3 (D-13)
            findings.append({
                "severity": "MEDIUM",
                "host": host,
                "port": port,
                "title": "Non-PFS cipher suite on email TLS endpoint",
                "recommendation": (
                    "ECDHE without TLS 1.3 provides forward secrecy but remains quantum-vulnerable "
                    "via Shor's algorithm. Prefer TLS 1.3 AEAD suites (AES-GCM, ChaCha20-Poly1305) "
                    "and plan migration to post-quantum key encapsulation."
                ),
            })

    return findings
