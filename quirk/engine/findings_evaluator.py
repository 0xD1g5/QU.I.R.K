"""Post-scan findings evaluator — NOT the score engine.

Quantum-readiness scoring lives in `quirk/intelligence/`. This module
handles per-finding evaluation and deduplication only.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from quirk.compliance import COMPLIANCE_MAP, TITLE_PREFIX_ALIASES
from quirk.reports.content_model import (
    ALGO_IMPACT_MAP,
    FALLBACK_QUANTUM_RISK,
    REMEDIATION_CATALOG,
    _classify_finding,
)


# Phase 72 D-04 / D-04a: module-private severity rank used by _dedupe_findings sort
# key. Lower rank = higher severity; CRITICAL sorts first so high-severity findings
# cluster at the top of dedup output. Also used by the dedup tie-break — when two
# findings collide on the dedup key, the lower-rank (higher-severity) finding wins.
_SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

# Phase 49 D-02 + Pitfall 1: canonical-key lookup for COMPLIANCE_MAP.
# COMPLIANCE_MAP keys are the LITERAL emitted titles (parens preserved).
# The 7 f-string titles whose runtime form contains an interpolated value
# are mapped via TITLE_PREFIX_ALIASES (longest-prefix-first). Any title
# not matching a known prefix is returned verbatim — fixed-string titles
# (incl. those with parens like "Legacy TLS versions allowed (TLS 1.0/1.1)"
# and "Plaintext Redis listener (no auth)") look up directly.
#
# Cache the prefixes sorted longest-first at module load. The prefix list
# is small (currently 7 entries) so this is O(n) per lookup with n = 7.
_COMPLIANCE_PREFIXES_LONGEST_FIRST = sorted(
    TITLE_PREFIX_ALIASES, key=len, reverse=True
)


def _normalize_for_compliance(title: str) -> str:
    """Phase 49 D-02: canonicalize finding titles for COMPLIANCE_MAP lookup."""
    for prefix in _COMPLIANCE_PREFIXES_LONGEST_FIRST:
        if title.startswith(prefix):
            return TITLE_PREFIX_ALIASES[prefix]
    return title

# (version_prefix, severity, eol_label)
_OPENSSL_EOL: List[Tuple[str, str, str]] = [
    ("0.", "CRITICAL", "OpenSSL 0.x"),
    ("1.0.", "CRITICAL", "OpenSSL 1.0.x (EOL Dec 2019)"),
    ("1.1.", "HIGH", "OpenSSL 1.1.x (EOL Sep 2023)"),
    ("3.0.", "HIGH", "OpenSSL 3.0.x (EOL Apr 2026)"),
    ("3.1.", "HIGH", "OpenSSL 3.1.x (EOL Mar 2025)"),
]

_OPENSSL_NAMES = frozenset({"openssl", "libssl", "libssl1.0", "libssl1.0.0", "libssl1.1", "libssl3", "libcrypto", "libcrypto3"})

# Phase 48 D-06: canonical NIST IR 8547 deprecation phrase. The single
# authoritative anchor for the v4.6 quantum-vulnerable recommendation suffix
# and for Phase 49 (Compliance Mapping). Per-finding drift is structurally
# impossible because every quantum-vulnerable finding receives this exact
# constant via _build_finding(quantum_vulnerable=True).
NIST_IR_8547_DEPRECATION = (
    "Per NIST IR 8547, RSA and ECC are deprecated after 2030 and "
    "disallowed after 2035."
)


def _build_finding(
    *,
    severity: str,
    host: str,
    port: int,
    title: str,
    description: str,
    recommendation: str,
    quantum_vulnerable: bool = False,
    check_id: str = "",
) -> Dict[str, Any]:
    """Single chokepoint for finding construction (Phase 48 D-02).

    Enforces non-empty ``description`` and ``recommendation``. Appends
    :data:`NIST_IR_8547_DEPRECATION` to ``recommendation`` (separated by a
    single space) when ``quantum_vulnerable`` is ``True`` AND no catalog entry
    exists for the detected crypto class (D-05 / Phase 99). Raises
    ``ValueError`` if either description or recommendation is empty or
    whitespace-only.

    Phase 99 (D-02/D-04/D-05):
    - ``check_id``: optional crypto-class key hint for ``_classify_finding``
      (used by codesign expiry findings whose titles contain no RSA/SHA keyword).
    - ``quantum_risk``: populated from ``ALGO_IMPACT_MAP[crypto_class][2]``
      when a crypto class is matched, else from ``FALLBACK_QUANTUM_RISK``.
    - Catalog-matched findings (``REMEDIATION_CATALOG``) have their
      recommendation replaced with the catalog-specific string (D-04).
    - ``NIST_IR_8547_DEPRECATION`` is appended ONLY when ``quantum_vulnerable``
      is ``True`` AND the crypto class has no catalog entry (D-05).

    The recommendation is deterministic so ``_dedupe_findings`` correctness
    is preserved (see NOTE at line ~189).
    """
    if not description or not description.strip():
        raise ValueError("_build_finding requires a non-empty description")
    if not recommendation or not recommendation.strip():
        raise ValueError("_build_finding requires a non-empty recommendation")
    rec = recommendation.strip()

    # Phase 99 D-02/D-04/D-05: build intermediate finding dict for _classify_finding
    proto_finding: Dict[str, Any] = {
        "severity": severity,
        "title": title,
        "description": description.strip(),
        "check_id": check_id,
    }
    crypto_class = _classify_finding(proto_finding)

    # D-04: catalog-matched findings use catalog recommendation (overrides caller-supplied)
    if crypto_class and crypto_class in REMEDIATION_CATALOG:
        rec = REMEDIATION_CATALOG[crypto_class]
    elif quantum_vulnerable:
        # D-05: no catalog match + quantum_vulnerable → append NIST boilerplate
        rec = f"{rec} {NIST_IR_8547_DEPRECATION}"

    # D-02: attach quantum_risk sentence
    if crypto_class and crypto_class in ALGO_IMPACT_MAP:
        quantum_risk = ALGO_IMPACT_MAP[crypto_class][2]
    else:
        quantum_risk = FALLBACK_QUANTUM_RISK

    return {
        "severity": severity,
        "host": host,
        "port": port,
        "title": title,
        "description": description.strip(),
        "recommendation": rec,
        "check_id": check_id,
        "quantum_risk": quantum_risk,
        # Phase 49 D-02: eager compliance attachment via the chokepoint.
        "compliance": COMPLIANCE_MAP.get(_normalize_for_compliance(title), []),
    }


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
                return _build_finding(
                    severity=sev,
                    host=host,
                    port=port,
                    title=f"End-of-life {label} in container image",
                    description=(
                        "The container image bundles an end-of-life OpenSSL release "
                        "that no longer receives upstream security patches. Newly "
                        "disclosed CVEs will not be fixed in this image."
                    ),
                    recommendation=(
                        f"{label} has reached end-of-life and no longer receives security patches. "
                        "Update the base image to a supported distribution with a current OpenSSL version."
                    ),
                )
        return _build_finding(
            severity="LOW",
            host=host,
            port=port,
            title=f"Container image uses quantum-vulnerable crypto library ({name}@{version})",
            description=(
                "The container image bundles a classical cryptographic library "
                "(RSA/ECDSA-based) vulnerable to a sufficiently large quantum "
                "computer. Long-lived data encrypted by services in this image "
                "faces 'harvest now, decrypt later' risk."
            ),
            recommendation=(
                "Plan migration to ML-KEM (FIPS 203) for key exchange and "
                "ML-DSA (FIPS 204) or SLH-DSA (FIPS 205) for signatures once "
                "upstream library support is available."
            ),
            quantum_vulnerable=True,
        )

    if name == "cryptography":
        major = _pkg_major(version)
        if major is not None and major < 3:
            return _build_finding(
                severity="HIGH",
                host=host,
                port=port,
                title=f"Severely outdated Python cryptography package ({version}) in container image",
                description=(
                    "The container image ships a years-old release of the Python "
                    "'cryptography' package with multiple known CVEs. Vulnerabilities "
                    "in TLS, X.509 parsing, and key handling are not patched."
                ),
                recommendation=(
                    f"cryptography {version} is over 4 years old with multiple known CVEs. "
                    "Update to the latest version and rebuild the container image."
                ),
            )
        if major is not None and major < 41:
            return _build_finding(
                severity="MEDIUM",
                host=host,
                port=port,
                title=f"Outdated Python cryptography package ({version}) in container image",
                description=(
                    "The container image ships an outdated release of the Python "
                    "'cryptography' package that may have unpatched vulnerabilities."
                ),
                recommendation=(
                    f"cryptography {version} may have unpatched vulnerabilities. "
                    "Update to the latest version and rebuild the container image."
                ),
            )

    if name == "pyopenssl":
        major = _pkg_major(version)
        if major is not None and major < 20:
            return _build_finding(
                severity="MEDIUM",
                host=host,
                port=port,
                title=f"Outdated pyOpenSSL package ({version}) in container image",
                description=(
                    "The container image ships an outdated pyOpenSSL release that "
                    "may have known vulnerabilities in TLS or certificate handling."
                ),
                recommendation=(
                    f"pyOpenSSL {version} may have known vulnerabilities. "
                    "Update to the latest version."
                ),
            )

    if name in {"libgcrypt20", "libgcrypt"}:
        if version.startswith("1.8."):
            return _build_finding(
                severity="MEDIUM",
                host=host,
                port=port,
                title=f"Outdated libgcrypt ({version}) in container image",
                description=(
                    "The container image bundles libgcrypt 1.8.x, an outdated "
                    "branch that no longer receives current security fixes."
                ),
                recommendation="libgcrypt 1.8.x is outdated. Update the base image.",
            )

    return _build_finding(
        severity="LOW",
        host=host,
        port=port,
        title=f"Container image contains crypto library ({name}@{version})",
        description=(
            "The container image inventory includes a cryptographic library "
            "that should be tracked for lifecycle and CVE exposure."
        ),
        recommendation="Review cryptographic library inventory and plan lifecycle management.",
    )


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


_SENTINEL = object()


def _chain_verified(ep: Any) -> Optional[bool]:
    """Return tri-state chain-verification result for ``ep``.

    Phase 46 (TLS-FIND-06): prefer the direct ``chain_verified`` column
    (now declared on CryptoEndpoint as Boolean nullable). Fall back to
    the legacy ``tls_capabilities_json`` blob for backward compatibility
    with rows written before the column existed. Returns ``None`` when
    no signal is available — callers MUST treat ``None`` as indeterminate
    (D-04: untrusted-CA branch fires only on explicit ``False``).
    """
    cv_direct = getattr(ep, "chain_verified", _SENTINEL)
    if cv_direct is not _SENTINEL and cv_direct is not None:
        return bool(cv_direct)
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
    # NOTE (Phase 48 D-02/D-06): _build_finding appends NIST_IR_8547_DEPRECATION
    # to recommendation deterministically for quantum_vulnerable=True findings.
    # Same input recommendation -> same output recommendation -> two findings
    # that previously deduped on (host, port, title, recommendation) continue
    # to dedup. T-48-03 mitigation.
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
        # Phase 72 D-04: rank inverted (CRITICAL=0..INFO=4); lower rank = higher severity.
        cur_rank = _SEVERITY_RANK.get(str(f.get("severity", "INFO")).upper(), 4)
        prev_rank = _SEVERITY_RANK.get(str(prior.get("severity", "INFO")).upper(), 4)
        if cur_rank < prev_rank:
            deduped[key] = f

    # Phase 72 D-04 / WR-24: stable sort key — severity_rank first so high-severity
    # findings cluster. 'recommendation' dropped from key: remediation-text edits no
    # longer reshuffle golden output. C-4 adjudication: "finding_id" in D-04 maps to
    # `title` (no finding_id column exists in the dedup tuple).
    return [
        deduped[k]
        for k in sorted(
            deduped.keys(),
            key=lambda x: (
                _SEVERITY_RANK.get(str(deduped[x].get("severity", "INFO")).upper(), 4),
                x[2],  # title — per Phase 72 C-4 mapping for D-04's "finding_id"
                x[0],  # host
                x[1],  # port
            ),
        )
    ]


def _postprocess_findings(cfg, endpoints, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Post-processing for findings:
      - If protocol classifier labels HTTP on ports we *expect* to be TLS, treat as MISCONFIG.
      - If TLS is blocked due to MTLS_REQUIRED, avoid calling it plaintext.
    """
    tls_ports = set(getattr(cfg.scan, "ports_tls", []) or [])

    # Map endpoint protocol/detail for quick context
    ep_map: Dict[Tuple[str, int], Any] = {}
    for e in endpoints:
        ep_map[(getattr(e, "host", ""), int(getattr(e, "port", 0)))] = e

    # Phase 72 D-24 / WR-23: defensive snapshot iteration. Body currently mutates
    # fields of existing finding dicts in-place; the snapshot protects against
    # future maintainers adding append/remove without re-checking iteration safety.
    for f in tuple(findings):
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

        # Phase 45 / D-04, D-05: ADVISORY rows produced by quirk.util.optional_extra
        # become coverage_gap findings. INFO severity, zero score impact (D-07
        # — see quirk/intelligence/evidence.py for the score-exclusion path).
        # The `continue` is critical: it prevents the row from also being
        # processed by the generic scan_err handler below (which would emit a
        # duplicate "Informational protocol observation" finding).
        if proto == "ADVISORY" and getattr(e, "scan_error_category", "") == "missing_extra":
            scan_err_msg = getattr(e, "scan_error", "") or ""
            adv = _build_finding(
                severity="INFO",
                host=host,
                port=port,
                title="Scanner skipped — optional extra not installed",
                description=(
                    "A QUIRK scanner was skipped because its optional Python extra is "
                    "not installed in this environment. Coverage for this protocol is "
                    "incomplete until the extra is installed; the gap is reported "
                    "informationally and does not impact the quantum-readiness score."
                ),
                recommendation=(
                    scan_err_msg or
                    "Install the missing optional extra (pip install 'quirk[<extra>]') "
                    "and re-run the scan to obtain coverage for this protocol."
                ),
            )
            adv["category"] = "coverage_gap"
            findings.append(adv)
            continue

        # Scan errors are normalized into blocker/advisory findings.
        scan_err = getattr(e, "scan_error", None)
        if scan_err:
            err_cat = _error_category(scan_err)
            if proto == "TLS" and err_cat in {"TLS_HANDSHAKE_FAILED", "TIMEOUT"}:
                f = _build_finding(
                    severity="MEDIUM",
                    host=host,
                    port=port,
                    title="TLS handshake blocked assessment",
                    description=(
                        "The TLS handshake failed or timed out, so QUIRK could not "
                        "evaluate the negotiated protocol version, cipher suite, or "
                        "certificate. The endpoint's cryptographic posture is unknown "
                        "and may hide misconfigurations."
                    ),
                    recommendation="TLS handshake failure is blocking accurate cryptographic assessment. Validate handshake policy and endpoint expectations.",
                )
                f["detail"] = scan_err
                findings.append(f)
                continue
            if proto == "TLS" and err_cat == "MTLS_REQUIRED":
                f = _build_finding(
                    severity="INFO",
                    host=host,
                    port=port,
                    title="mTLS required",
                    description=(
                        "The endpoint requires client certificate authentication "
                        "(mTLS) before completing the TLS handshake. QUIRK was unable "
                        "to authenticate; the trust chain and onboarding flow should "
                        "be validated out-of-band."
                    ),
                    recommendation="Confirm client certificate requirements and document trust chain and onboarding process.",
                )
                f["detail"] = scan_err
                findings.append(f)
                continue
            f = _build_finding(
                severity="INFO",
                host=host,
                port=port,
                title="Informational protocol observation",
                description=(
                    "QUIRK observed a non-fatal protocol behavior or availability "
                    "issue while probing this endpoint. The observation is recorded "
                    "for inventory purposes but does not by itself indicate a defect."
                ),
                recommendation="Review protocol behavior and endpoint availability details.",
            )
            f["detail"] = scan_err
            findings.append(f)
            continue

        if proto == "HTTP":
            findings.append(_build_finding(
                severity="HIGH",
                host=host,
                port=port,
                title="Plaintext HTTP service detected",
                description=(
                    "This service responds to plaintext HTTP. Credentials, session "
                    "tokens, and application payloads transit unencrypted and are "
                    "trivially intercepted by anyone on the network path."
                ),
                recommendation="Migrate management/application endpoints to HTTPS/TLS where feasible.",
            ))

        if proto == "TLS":
            if _has_legacy_tls_versions(e):
                findings.append(_build_finding(
                    severity="LOW",
                    host=host,
                    port=port,
                    title="Legacy TLS versions allowed (TLS 1.0/1.1)",
                    description=(
                        "This service accepts TLS 1.0 or TLS 1.1, protocols deprecated "
                        "by the IETF (RFC 8996) and prohibited by PCI-DSS, FedRAMP, and "
                        "most enterprise security baselines. Attackers can downgrade "
                        "connections and exploit known cipher weaknesses."
                    ),
                    recommendation="Disable TLS 1.0/1.1 and standardize on TLS 1.2+ (prefer TLS 1.3).",
                ))

            # BUG-01: Legacy cipher suites (non-AEAD, non-PFS)
            if getattr(e, "tls_legacy_suites_present", False):
                findings.append(_build_finding(
                    severity="LOW",
                    host=host,
                    port=port,
                    title="Legacy TLS cipher suites accepted",
                    description=(
                        "The endpoint negotiates legacy non-AEAD cipher suites (CBC-mode "
                        "with HMAC-SHA1) that lack forward secrecy or use weak MACs. "
                        "These suites are vulnerable to padding-oracle and downgrade "
                        "attacks and do not meet modern enterprise baselines."
                    ),
                    recommendation=(
                        "Disable legacy cipher suites (e.g. AES128-SHA, AES256-SHA) and require "
                        "AEAD suites with forward secrecy (AES-GCM, ChaCha20-Poly1305)."
                    ),
                ))

            # BUG-02: Certificate expiry
            cert_not_after = getattr(e, "cert_not_after", None)
            if isinstance(cert_not_after, datetime):
                now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
                # cert_not_after is stored as naive UTC (tzinfo stripped at scan time)
                na = cert_not_after if cert_not_after.tzinfo is None else cert_not_after.astimezone(timezone.utc).replace(tzinfo=None)
                if na < now_naive:
                    findings.append(_build_finding(
                        severity="CRITICAL",
                        host=host,
                        port=port,
                        title="TLS certificate expired",
                        description=(
                            "This certificate has passed its notAfter date. Clients "
                            "receive trust warnings and may refuse to connect, breaking "
                            "automated integrations and exposing users to phishing-style "
                            "click-through normalization."
                        ),
                        recommendation=(
                            f"Certificate expired {na.date()}. Renew immediately — expired certs "
                            "cause trust failures and may block legitimate clients."
                        ),
                    ))
                elif na < now_naive + timedelta(days=30):
                    findings.append(_build_finding(
                        severity="MEDIUM",
                        host=host,
                        port=port,
                        title="TLS certificate expiring within 30 days",
                        description=(
                            "This certificate is approaching its notAfter date. Renew "
                            "before expiry to avoid service interruption and trust "
                            "warnings on dependent clients."
                        ),
                        recommendation=(
                            f"Certificate expires {na.date()}. Schedule renewal before expiry "
                            "to avoid service disruption."
                        ),
                    ))

            # TLS-FIND-02 / TLS-FIND-03: Self-signed vs untrusted-CA — mutually
            # exclusive per D-04. A self-signed cert (issuer == subject) is a
            # strict subset of "chain didn't verify"; emitting both would be
            # redundant noise. Both branches are independent of expired/RSA/EC
            # branches per D-02 (one finding per defect class, no rollup).
            cert_issuer = (getattr(e, "cert_issuer", "") or "").strip()
            cert_subject = (getattr(e, "cert_subject", "") or "").strip()
            cv = _chain_verified(e)
            is_self_signed = bool(cert_issuer and cert_subject and cert_issuer == cert_subject)
            if is_self_signed:
                findings.append(_build_finding(
                    severity="HIGH",
                    host=host,
                    port=port,
                    title="TLS certificate is self-signed",
                    description=(
                        "This certificate is self-signed and is not issued by a trusted "
                        "certificate authority. Clients cannot verify the server's "
                        "identity and are exposed to man-in-the-middle interception."
                    ),
                    recommendation=(
                        "The certificate's issuer is identical to its subject — the "
                        "certificate is self-signed and is not anchored to a trusted "
                        "certificate authority. Replace with a certificate issued by a "
                        "trusted CA (public or internal PKI)."
                    ),
                ))
            elif cert_issuer and cert_subject and cert_issuer != cert_subject and cv is False:
                findings.append(_build_finding(
                    severity="MEDIUM",
                    host=host,
                    port=port,
                    title="TLS certificate issued by untrusted CA",
                    description=(
                        "This certificate chains to a certificate authority not in the "
                        "system trust store. Clients cannot verify the server's identity, "
                        "and connection establishment depends on out-of-band trust."
                    ),
                    recommendation=(
                        "Chain verification against the system trust store failed. The "
                        "certificate is issued by a CA that is not present in the trust "
                        "store. Replace with a certificate from a publicly trusted CA, "
                        "or add the issuing CA to the system trust store if it is an "
                        "internal PKI."
                    ),
                ))

            # BUG-04: Quantum-vulnerable TLS certificate key algorithm
            cert_pubkey_alg = (getattr(e, "cert_pubkey_alg", "") or "").strip().upper()
            cert_pubkey_size = getattr(e, "cert_pubkey_size", None)
            if cert_pubkey_alg == "RSA":
                if cert_pubkey_size is not None and cert_pubkey_size < 2048:
                    findings.append(_build_finding(
                        severity="HIGH",
                        host=host,
                        port=port,
                        title="TLS certificate uses undersized RSA key",
                        description=(
                            "This certificate uses an RSA key below the classical 2048-bit "
                            "minimum, which is breakable by today's classical attackers and "
                            "is also vulnerable to a sufficiently large quantum computer. "
                            "Captured ciphertext today can be decrypted retroactively under "
                            "a 'harvest now, decrypt later' threat model."
                        ),
                        recommendation=(
                            f"RSA-{cert_pubkey_size} is below the 2048-bit classical minimum. "
                            "Migrate to RSA-2048+ or ECDSA P-256 immediately, and plan "
                            "migration to ML-KEM (FIPS 203) for key exchange and ML-DSA "
                            "(FIPS 204) or SLH-DSA (FIPS 205) for signatures."
                        ),
                        quantum_vulnerable=True,
                    ))
                else:
                    findings.append(_build_finding(
                        severity="MEDIUM",
                        host=host,
                        port=port,
                        title="TLS certificate uses quantum-vulnerable RSA key",
                        description=(
                            "This certificate uses RSA, an algorithm vulnerable to attack "
                            "by a sufficiently large quantum computer via Shor's algorithm. "
                            "Captured ciphertext today can be decrypted retroactively once "
                            "such a computer exists ('harvest now, decrypt later')."
                        ),
                        recommendation=(
                            "Plan migration to ML-KEM (FIPS 203) for key exchange and "
                            "ML-DSA (FIPS 204) or SLH-DSA (FIPS 205) for signatures."
                        ),
                        quantum_vulnerable=True,
                    ))
            elif cert_pubkey_alg == "ECDSA":
                if cert_pubkey_size is not None and cert_pubkey_size < 256:
                    findings.append(_build_finding(
                        severity="HIGH",
                        host=host,
                        port=port,
                        title="TLS certificate uses undersized ECDSA key",
                        description=(
                            "This certificate uses an ECDSA key below the P-256 classical "
                            "minimum and is vulnerable both to classical attack at this "
                            "key size and to a sufficiently large quantum computer."
                        ),
                        recommendation=(
                            f"ECDSA-{cert_pubkey_size} is below the P-256 classical minimum. "
                            "Migrate to P-256+ immediately and plan migration to ML-DSA "
                            "(FIPS 204) or SLH-DSA (FIPS 205) for signatures and ML-KEM "
                            "(FIPS 203) for key exchange."
                        ),
                        quantum_vulnerable=True,
                    ))
                else:
                    findings.append(_build_finding(
                        severity="MEDIUM",
                        host=host,
                        port=port,
                        title="TLS certificate uses quantum-vulnerable ECDSA key",
                        description=(
                            "This certificate uses ECDSA, an algorithm vulnerable to attack "
                            "by a sufficiently large quantum computer. Signatures are "
                            "forgeable and key-exchange material is recoverable in a "
                            "post-quantum threat model."
                        ),
                        recommendation=(
                            "Plan migration to ML-DSA (FIPS 204) or SLH-DSA (FIPS 205) "
                            "for signatures and ML-KEM (FIPS 203) for key exchange."
                        ),
                        quantum_vulnerable=True,
                    ))

        if proto == "SSH":
            findings.append(_build_finding(
                severity="INFO",
                host=host,
                port=port,
                title="SSH quantum planning advisory",
                description=(
                    "This SSH host key or key-exchange algorithm relies on RSA or "
                    "classical ECDH, both vulnerable to a sufficiently large quantum "
                    "computer. Long-lived SSH credentials face 'harvest now, decrypt "
                    "later' risk."
                ),
                recommendation=(
                    "Inventory SSH host keys and KEX algorithms; plan migration to "
                    "post-quantum SSH using ML-KEM (FIPS 203) for key exchange when "
                    "OpenSSH support lands."
                ),
                quantum_vulnerable=True,
            ))

        if proto == "CONTAINER":
            pkg_name = (getattr(e, "cipher_suite", "") or "").strip()
            pkg_version = (getattr(e, "tls_version", "") or "").strip()
            finding = _evaluate_container_package(host, port, pkg_name, pkg_version)
            if finding:
                findings.append(finding)

        if proto == "UNKNOWN":
            findings.append(_build_finding(
                severity="MEDIUM",
                host=host,
                port=port,
                title="Unknown open service",
                description=(
                    "An open TCP port responded but QUIRK could not classify the "
                    "running service. Unmapped services may carry undiscovered "
                    "cryptographic risk and should be inventoried."
                ),
                recommendation="Fingerprint with a deeper probe or validate service ownership and purpose.",
            ))

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
            findings.append(_build_finding(
                severity="MEDIUM",
                host=host,
                port=port,
                title="STARTTLS downgrade risk on SMTP",
                description=(
                    "This SMTP service negotiates TLS opportunistically via STARTTLS. "
                    "An in-path attacker can strip the STARTTLS capability "
                    "advertisement, forcing plaintext mail delivery. The downgrade "
                    "is invisible to agentless scanners and to the connecting MTA."
                ),
                recommendation=(
                    "STARTTLS (opportunistic TLS) is susceptible to stripping attacks that "
                    "cannot be detected by an agentless scanner. An attacker in-path can "
                    "suppress the STARTTLS capability advertisement, forcing plaintext delivery. "
                    "Enforce MTA-STS (RFC 8461) or DANE (RFC 7672) to prevent stripping."
                ),
            ))

        # EMAIL-09: Weak RSA key exchange / 3DES / RC4 = HIGH
        is_rsa_kex = (
            cipher.startswith("TLS_RSA_WITH_")
            or "AES128-SHA" in cipher
            or "AES256-SHA" in cipher
            or "3DES" in cipher
            or "RC4" in cipher
        ) and "ECDHE" not in cipher and "DHE-" not in cipher

        if is_rsa_kex and tls_version:
            findings.append(_build_finding(
                severity="HIGH",
                host=host,
                port=port,
                title="Weak cipher suite on email TLS endpoint",
                description=(
                    "This email TLS endpoint negotiates a non-PFS RSA key-exchange "
                    "or legacy 3DES/RC4 cipher suite. Sessions lack forward secrecy "
                    "and the underlying RSA key exchange is quantum-vulnerable: "
                    "captured traffic can be decrypted retroactively."
                ),
                recommendation=(
                    "TLS_RSA_WITH_* suites use RSA key exchange (no forward secrecy) and are "
                    "quantum-vulnerable. Disable non-PFS suites and require ECDHE or TLS 1.3 "
                    "cipher suites across all email protocol ports. Plan migration to "
                    "ML-KEM (FIPS 203) for key exchange."
                ),
                quantum_vulnerable=True,
            ))
        elif pfs is False and tls_version and tls_version != "TLSv1.3":
            # EMAIL-09 MEDIUM: Non-PFS ECDHE without TLS 1.3 (D-13)
            findings.append(_build_finding(
                severity="MEDIUM",
                host=host,
                port=port,
                title="Non-PFS cipher suite on email TLS endpoint",
                description=(
                    "This email TLS endpoint advertises ECDHE but operates below "
                    "TLS 1.3, leaving the key exchange vulnerable to Shor's algorithm "
                    "on a sufficiently large quantum computer."
                ),
                recommendation=(
                    "ECDHE without TLS 1.3 provides forward secrecy but remains quantum-vulnerable "
                    "via Shor's algorithm. Prefer TLS 1.3 AEAD suites (AES-GCM, ChaCha20-Poly1305) "
                    "and plan migration to ML-KEM (FIPS 203) for key encapsulation."
                ),
                quantum_vulnerable=True,
            ))

    return findings


def evaluate_broker_endpoints(endpoints) -> List[Dict[str, Any]]:
    """Phase 33: emit broker-specific findings.

    Plaintext findings (HIGH):
      - kafka-plaintext-listener  (ep.protocol == "KAFKA-PLAIN")
      - amqp-plaintext-listener   (ep.protocol == "AMQP-PLAIN")
      - redis-plaintext-no-auth   (ep.protocol == "REDIS-PLAIN")

    Weak-cipher findings (HIGH) for TLS_RSA_WITH_*, 3DES, RC4, or non-AEAD *-SHA on
    any broker TLS protocol (KAFKA-TLS, AMQPS, AMQPS/Azure-ServiceBus, HTTPS/AWS-SQS, REDIS-TLS).
    """
    findings: List[Dict[str, Any]] = []
    for e in endpoints:
        host = getattr(e, "host", "")
        port = int(getattr(e, "port", 0) or 0)
        protocol = getattr(e, "protocol", "") or ""
        cipher = (getattr(e, "cipher_suite", "") or "").upper()
        tls_version = getattr(e, "tls_version", "") or ""

        if protocol == "KAFKA-PLAIN":
            findings.append(_build_finding(
                severity="HIGH", host=host, port=port,
                title="Plaintext Kafka listener detected",
                description=(
                    "This Kafka broker exposes a PLAINTEXT listener. Topic data, "
                    "consumer offsets, and SASL credentials transit unencrypted "
                    "and are interceptable by anyone on the network path."
                ),
                recommendation="Disable PLAINTEXT listener or restrict access; enforce SSL/SASL_SSL on broker port 9092.",
            ))
            continue
        if protocol == "AMQP-PLAIN":
            findings.append(_build_finding(
                severity="HIGH", host=host, port=port,
                title="Plaintext AMQP listener detected",
                description=(
                    "This AMQP broker accepts plaintext connections on port 5672. "
                    "Message bodies, routing keys, and authentication credentials "
                    "are exposed to any in-path attacker."
                ),
                recommendation="Disable plaintext AMQP on port 5672; require AMQPS (port 5671) for all clients.",
            ))
            continue
        if protocol == "REDIS-PLAIN":
            findings.append(_build_finding(
                severity="HIGH", host=host, port=port,
                title="Plaintext Redis listener (no auth)",
                description=(
                    "This Redis instance accepts plaintext connections without "
                    "authentication. Cached session data, application secrets, and "
                    "queued jobs are readable and writable by any network reachable "
                    "client."
                ),
                recommendation="Enable TLS on port 6380 and require AUTH; bind plaintext port to localhost only or disable.",
            ))
            continue

        # Weak-cipher detection on any broker TLS protocol
        broker_tls = protocol in {"KAFKA-TLS", "AMQPS", "AMQPS/Azure-ServiceBus", "HTTPS/AWS-SQS", "REDIS-TLS"}
        if broker_tls and tls_version:
            is_rsa_kex = (
                cipher.startswith("TLS_RSA_WITH_")
                or any(s in cipher for s in ("AES128-SHA", "AES256-SHA", "3DES", "RC4", "DES-CBC"))
            ) and "ECDHE" not in cipher and "DHE" not in cipher
            if is_rsa_kex:
                findings.append(_build_finding(
                    severity="HIGH", host=host, port=port,
                    title="Weak cipher suite on broker TLS endpoint",
                    description=(
                        "This broker TLS endpoint negotiates a non-PFS RSA key-exchange "
                        "or legacy 3DES/RC4/weak-CBC cipher suite. Sessions lack forward "
                        "secrecy and the underlying RSA key exchange is quantum-vulnerable."
                    ),
                    recommendation=(
                        "Broker is negotiating non-PFS RSA / 3DES / RC4 / weak-CBC suites. "
                        "Disable TLS_RSA_WITH_* and legacy ciphers; require TLS 1.2+ AEAD or "
                        "TLS 1.3. Plan migration to ML-KEM (FIPS 203) for key exchange."
                    ),
                    quantum_vulnerable=True,
                ))
    return findings


def evaluate_codesign_endpoints(endpoints) -> List[Dict[str, Any]]:
    """Phase 99 CTX-03: emit code-signing expiry / weak-algorithm findings.

    Analogue of evaluate_email_endpoints / evaluate_broker_endpoints for
    CODE_SIGNING CryptoEndpoints.  Three branches per endpoint:

    1. ``"expired"`` in reasons → HIGH finding with check_id="CODESIGN_EXPIRY"
       (catalog-wins D-04: _build_finding replaces recommendation with
       REMEDIATION_CATALOG["CODESIGN_EXPIRY"]).
    2. ``"approaching-expiry"`` in reasons → MEDIUM finding with
       check_id="CODESIGN_APPROACHING_EXPIRY".
    3. Any other weak-crypto reason → HIGH quantum-vulnerable finding.

    T-99-04 mitigated: malformed ``smime_scan_json`` defaults to ``reasons=[]``
    (no crash; no finding emitted for that endpoint).

    All findings are constructed through ``_build_finding`` so they carry
    ``quantum_risk`` automatically (D-06).
    """
    findings: List[Dict[str, Any]] = []

    for e in endpoints:
        host = getattr(e, "host", "") or ""
        port = int(getattr(e, "port", 0) or 0)
        cert_subject = getattr(e, "cert_subject", None) or "unknown"
        cert_not_after = getattr(e, "cert_not_after", None)

        # Compute not_after_date string and days_remaining for description interpolation
        if cert_not_after is not None:
            if cert_not_after.tzinfo is None:
                not_after_utc = cert_not_after.replace(tzinfo=timezone.utc)
            else:
                not_after_utc = cert_not_after.astimezone(timezone.utc)
            not_after_date = not_after_utc.strftime("%Y-%m-%d")
            days_remaining = int((not_after_utc - datetime.now(timezone.utc)).total_seconds() / 86400)
        else:
            not_after_date = "unknown"
            days_remaining = 0

        # T-99-04: guard malformed smime_scan_json
        reasons: list = []
        try:
            raw = getattr(e, "smime_scan_json", None)
            if raw:
                parsed = json.loads(raw)
                reasons = parsed.get("reasons") or []
        except Exception:
            reasons = []

        if "expired" in reasons:
            findings.append(_build_finding(
                severity="HIGH",
                host=host,
                port=port,
                title=f"Code-signing certificate expired: {cert_subject}",
                description=(
                    f"The code-signing certificate for '{cert_subject}' expired on"
                    f" {not_after_date}. Software signed by this certificate can no longer"
                    " be verified as authentic, creating a supply-chain trust failure."
                ),
                # Fallback recommendation — _build_finding will replace this with
                # REMEDIATION_CATALOG["CODESIGN_EXPIRY"] via _classify_finding (D-04).
                recommendation=(
                    "Renew the expired code-signing certificate immediately and re-sign"
                    " all artifacts."
                ),
                check_id="CODESIGN_EXPIRY",
            ))
        elif "approaching-expiry" in reasons:
            findings.append(_build_finding(
                severity="MEDIUM",
                host=host,
                port=port,
                title=f"Code-signing certificate expiring within 90 days: {cert_subject}",
                description=(
                    f"The code-signing certificate for '{cert_subject}' expires on"
                    f" {not_after_date} ({days_remaining} days remaining). Failure to"
                    " renew before expiry will break software verification and block"
                    " deployments."
                ),
                recommendation=(
                    "Renew this code-signing certificate before the not_after date."
                ),
                check_id="CODESIGN_APPROACHING_EXPIRY",
            ))
        elif reasons:
            # Weak-crypto branch (non-expiry reasons such as weak-rsa-key, weak-ec-key,
            # weak-signing-alg).  Title follows research Open Question 2 resolution.
            # WR-02 fix: map the dominant reason to a check_id so _classify_finding
            # routes to the algorithm-specific ALGO_IMPACT_MAP entry and catalog
            # recommendation, rather than falling back to FALLBACK_QUANTUM_RISK.
            # "weak-ec-key" → "ECDSA" (ECC key → Shor's discrete-log sentence)
            # "weak-rsa-key" → "RSA"   (RSA key → Shor's factoring sentence)
            # "weak-signing-alg" → "SHA-1" (SHA-1 sig hash → Grover sentence)
            _reason_to_check_id = {
                "weak-ec-key": "ECDSA",
                "weak-rsa-key": "RSA",
                "weak-signing-alg": "SHA-1",
            }
            dominant_check_id = next(
                (_reason_to_check_id[r] for r in reasons if r in _reason_to_check_id),
                "",
            )
            reasons_str = ", ".join(reasons)
            findings.append(_build_finding(
                severity="HIGH",
                host=host,
                port=port,
                title=f"Code-signing certificate uses weak algorithm: {cert_subject}",
                description=(
                    f"The code-signing certificate for '{cert_subject}' uses weak"
                    f" cryptographic algorithm(s): {reasons_str}. This certificate is"
                    " quantum-vulnerable and should be replaced with a stronger algorithm."
                ),
                recommendation=(
                    "Replace this code-signing certificate with one using a modern"
                    " algorithm (RSA≥2048, ECDSA P-256 or stronger, SHA-256 or stronger)."
                    " Plan migration to ML-DSA (FIPS 204) for long-term quantum safety."
                ),
                quantum_vulnerable=True,
                check_id=dominant_check_id,
            ))

    return findings
