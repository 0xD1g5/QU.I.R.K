"""FastAPI-free dashboard finding derivation (Phase 236 D-10).

The derivation block that used to live in ``routes/scan.py``.  It must stay
FastAPI-free: ``quirk.notify.dispatcher`` and the CLI scheduler import it
without the ``[dashboard]`` extra installed.  Never import fastapi, starlette,
``quirk.dashboard.api.deps`` or ``middleware.auth`` here.  ``routes/scan.py``
re-exports every public name for backward compatibility.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

# RVW-002: share the report engine's tri-state chain-verification logic rather
# than reimplementing it here. Two implementations of 'did the chain verify?'
# is how the two surfaces drifted apart in the first place.
from quirk.engine.findings_evaluator import (
    _chain_verified,
    evaluate_container_endpoints,
    evaluate_identity_endpoints,
    evaluate_protocol_service_endpoints,
    runs_tls_certificate_checks,
)
from quirk.dashboard.api.schemas import FindingItem, IdentityFinding
from quirk.models import CryptoEndpoint
from quirk.util.weak_crypto import (
    has_legacy_tls_versions_signal,
    is_max_legacy_tls,
    is_undersized_rsa,
    is_weak_signature_hash,
)
from quirk.scanner.jwt_scanner import ADVISORY_JWKS_VERIFY_DISABLED

_QS_DISPLAY = {
    "quantum-safe": "Safe",
    "quantum-vulnerable": "Vulnerable",
    "hybrid": "At Risk",
    "unknown": "Unknown",
}


def findings_for_endpoint(ep: CryptoEndpoint) -> list[FindingItem]:
    """Every FindingItem one endpoint row yields.

    The single-endpoint slice of `_derive_findings` (Phase 202 / 202-03,
    D-06). Extracted so the storyline route's per-(id, title) lookup and the
    findings-list route share exactly one implementation of "what findings
    does this endpoint yield" — a second copy would drift exactly the way the
    dashboard and CLI finding vocabularies already have (see
    `quirk/dashboard/api/finding_title_bridge.py`, 202-01).

    Deliberately excludes the KERBEROS/SAML/DNSSEC identity-protocol skip and
    the cross-endpoint severity sort: both are loop-level concerns over the
    full endpoint list, not properties of a single endpoint, and both remain
    in `_derive_findings` below. `findings_for_endpoint` must be importable
    without importing the router.
    """
    now = datetime.now(tz=timezone.utc)
    findings: list[FindingItem] = []

    # JWKS fetched with verification disabled (225.1 SECH-05, score-neutral)
    if (ep.protocol or "").upper() == "ADVISORY" and (
        ep.service_detail == ADVISORY_JWKS_VERIFY_DISABLED
    ):
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="HIGH",
            title="JWKS fetched with TLS certificate verification disabled",
            protocol="ADVISORY",
            description=(
                "The JWKS was fetched with TLS certificate verification "
                "disabled (allow_insecure_jwks), so the keys could have been "
                "supplied by a network attacker."
            ),
            remediation=(
                "Install a certificate the scanner trusts on the JWKS "
                "endpoint and remove the allow_insecure_jwks setting."
            ),
            quantum_risk=None,
            category="config_advisory",
            source="jwt",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))

    # Phase 236 gap closure (XSURF-09, review WR-02): mirrors
    # evaluate_endpoints, which sends every row with a scan error to its
    # scan-error branch before the HTTP and TLS checks, so an errored row
    # raises no HIGH/CRITICAL there. JWKS stays above this guard because the
    # report evaluates the JWKS advisory before the scan-error branch too.
    if getattr(ep, "scan_error", None):
        return findings

    # Unencrypted HTTP
    if ep.protocol and ep.protocol.upper() == "HTTP":
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="HIGH",
            title="Unencrypted HTTP service",
            protocol="HTTP",
            description="Service is accessible over plaintext HTTP without TLS.",
            remediation="Enable TLS and redirect HTTP to HTTPS.",
            quantum_risk=None,
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))

    # Phase 228 D-05: the report gates its whole TLS block on the same
    # predicate. JWKS advisory and HTTP stay above the gate on purpose.
    if not runs_tls_certificate_checks(ep):
        return findings

    # Legacy TLS, two tiers (Phase 236 D-01/D-20). Both tiers use the shared
    # predicates in quirk.util.weak_crypto, the same ones the report calls, so
    # the surfaces cannot drift. The tiers are mutually exclusive.
    _tls_ver = ep.tls_version
    _tls_sup = getattr(ep, "tls_supported_versions", None)
    if is_max_legacy_tls(_tls_ver, _tls_sup):
        # D-05: title kept (today's ticket fingerprint); bridged to the report's
        # "Only legacy TLS versions offered (no TLS 1.2+)".
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="HIGH",
            title=f"Legacy TLS version: {ep.tls_version}",
            protocol="TLS",
            description=f"Server accepts {ep.tls_version} which is deprecated and insecure.",
            remediation="Disable TLSv1.0 and TLSv1.1. Enforce TLS 1.2 minimum, prefer TLS 1.3.",
            quantum_risk=None,
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))
    elif has_legacy_tls_versions_signal(_tls_ver, _tls_sup):
        # Bridged to the report's "Legacy TLS versions allowed (TLS 1.0/1.1)" (LOW).
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="LOW",
            title="Legacy TLS versions offered alongside TLS 1.2+",
            protocol="TLS",
            description="Server still offers TLS 1.0/1.1 alongside TLS 1.2+, which are deprecated.",
            remediation="Disable TLS 1.0 and TLS 1.1; keep TLS 1.2+ (prefer TLS 1.3).",
            quantum_risk=None,
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))

    # Weak cipher suites
    if ep.tls_weak_ciphers_present:
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="HIGH",
            title="Weak cipher suites enabled",
            protocol="TLS",
            description="Server accepts cipher suites with known weaknesses (RC4, DES, NULL, EXPORT, etc.).",
            remediation="Restrict cipher suites to ECDHE/DHE forward-secret suites with AES-GCM or ChaCha20.",
            quantum_risk=None,
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))

    # Expired certificate
    if ep.cert_not_after:
        cert_expiry = ep.cert_not_after
        if cert_expiry.tzinfo is None:
            cert_expiry = cert_expiry.replace(tzinfo=timezone.utc)
        days_to_expiry = (cert_expiry - now).days
        if days_to_expiry < 0:
            findings.append(FindingItem(
                id=ep.id,
                host=ep.host,
                port=ep.port,
                severity="CRITICAL",
                title="Certificate expired",
                protocol="TLS",
                description=f"Certificate expired {abs(days_to_expiry)} day(s) ago.",
                remediation="Renew the certificate immediately.",
                quantum_risk=None,
                source="tls",
                sensor_id=ep.sensor_id,
                segment=ep.segment,
            ))
        elif days_to_expiry < 30:
            findings.append(FindingItem(
                id=ep.id,
                host=ep.host,
                port=ep.port,
                severity="MEDIUM",  # Phase 228 D-01: matches the report
                title=f"Certificate expiring in {days_to_expiry} day(s)",
                protocol="TLS",
                description="Certificate expires within 30 days.",
                remediation="Renew certificate before expiry to avoid service interruption.",
                quantum_risk=None,
                source="tls",
                sensor_id=ep.sensor_id,
                segment=ep.segment,
            ))

    # RVW-002: title and severity are the report engine's, verbatim.
    # This used to read "Weak RSA key: N bits" at CRITICAL while
    # findings_evaluator called the same condition "TLS certificate uses
    # undersized RSA key" at HIGH — the operator console and the client
    # deliverable disagreeing about the same endpoint. Parity is asserted by
    # tests/test_finding_engine_parity.py. Phase 238 D-20: the condition is
    # the shared quirk.util.weak_crypto.is_undersized_rsa predicate (RSA /
    # RSA-PSS, 0 < size < 2048), so the two surfaces cannot drift again.
    if is_undersized_rsa(ep.cert_pubkey_alg, ep.cert_pubkey_size):
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="HIGH",
            title="TLS certificate uses undersized RSA key",
            protocol="TLS",
            description=(
                f"Certificate uses a {ep.cert_pubkey_size}-bit RSA key, below the "
                f"classical 2048-bit minimum."
            ),
            remediation=(
                f"RSA-{ep.cert_pubkey_size} is below the 2048-bit classical minimum. "
                f"Migrate to RSA-2048+ or ECDSA P-256 immediately."
            ),
            quantum_risk="Vulnerable",
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))

    # RVW-002 / TLS-FIND-02 / TLS-FIND-03: self-signed and untrusted-CA.
    # The dashboard had neither detection, so an operator triaging in the
    # console never saw a finding the client's report did carry. Mutually
    # exclusive per D-04 — a self-signed cert is a strict subset of "chain
    # didn't verify", and emitting both is redundant noise. The untrusted-CA
    # branch fires only on an explicit False, never on an indeterminate None.
    _issuer = (ep.cert_issuer or "").strip()
    _subject = (ep.cert_subject or "").strip()
    if _issuer and _subject and _issuer == _subject:
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="HIGH",
            title="TLS certificate is self-signed",
            protocol="TLS",
            description=(
                "This certificate is self-signed and is not issued by a trusted "
                "certificate authority. Clients cannot verify the server's identity "
                "and are exposed to man-in-the-middle interception."
            ),
            remediation=(
                "Replace with a certificate issued by a trusted CA (public or "
                "internal PKI)."
            ),
            quantum_risk=None,
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))
    elif _issuer and _subject and _chain_verified(ep) is False:
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="MEDIUM",
            title="TLS certificate issued by untrusted CA",
            protocol="TLS",
            description=(
                "This certificate chains to a certificate authority not in the "
                "system trust store. Clients cannot verify the server's identity."
            ),
            remediation=(
                "Replace with a certificate from a publicly trusted CA, or add the "
                "issuing CA to the system trust store if it is an internal PKI."
            ),
            quantum_risk=None,
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))

    # DETECT-07 (Phase 238 D-17..D-19, D-28): weak leaf signature hash, as in
    # the report. HIGH for a CA-issued leaf, LOW for a self-signed leaf (its
    # trust problem already carries the HIGH above). Leaf only (D-19).
    _self_signed = bool(_issuer and _subject and _issuer == _subject)
    if is_weak_signature_hash(ep.cert_sig_alg) and not _self_signed:
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="HIGH",
            title="TLS certificate uses a weak signature hash",
            protocol="TLS",
            description=(
                f"Certificate is signed with {ep.cert_sig_alg.strip().upper()}, a hash "
                f"with practical collision attacks."
            ),
            remediation="Reissue the certificate with a SHA-256 or stronger signature.",
            quantum_risk=None,
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))
    elif is_weak_signature_hash(ep.cert_sig_alg):
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="LOW",
            title="TLS certificate uses a weak signature hash",
            protocol="TLS",
            description=(
                f"Self-signed certificate is signed with "
                f"{ep.cert_sig_alg.strip().upper()}; clients do not rely on a "
                f"self-signed signature for trust."
            ),
            remediation="Reissue the certificate with a SHA-256 or stronger signature.",
            quantum_risk=None,
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))

    # Phase 236 D-04 (XSURF-11): an ECDSA key under 256 bits is HIGH, as in the
    # report (findings_evaluator ECDSA branch, same threshold); that row then
    # skips the MEDIUM Quantum- finding so there is one ECDSA finding per row.
    _undersized_ecdsa = (
        (ep.cert_pubkey_alg or "").strip().upper() == "ECDSA"
        and ep.cert_pubkey_size is not None
        and ep.cert_pubkey_size < 256
    )
    if _undersized_ecdsa:
        findings.append(FindingItem(
            id=ep.id,
            host=ep.host,
            port=ep.port,
            severity="HIGH",
            title="TLS certificate uses undersized ECDSA key",
            protocol="TLS",
            description=(
                f"Certificate uses a {ep.cert_pubkey_size}-bit ECDSA key, below the "
                f"P-256 classical minimum."
            ),
            remediation=(
                f"ECDSA-{ep.cert_pubkey_size} is below the P-256 classical minimum. "
                "Migrate to P-256+ immediately and plan migration to ML-DSA "
                "(FIPS 204) or SLH-DSA (FIPS 205)."
            ),
            quantum_risk="Vulnerable",
            source="tls",
            sensor_id=ep.sensor_id,
            segment=ep.segment,
        ))

    # Quantum-vulnerable algorithm (non-RSA)
    if not _undersized_ecdsa and ep.cert_pubkey_alg and not ep.cert_pubkey_alg.upper().startswith("RSA"):
        try:
            from quirk.cbom.classifier import classify_algorithm, quantum_safety_label
            _, nist_level, _ = classify_algorithm(ep.cert_pubkey_alg)
            qs = _QS_DISPLAY.get(quantum_safety_label(nist_level), "Unknown")
            if qs in ("Vulnerable", "At Risk"):
                findings.append(FindingItem(
                    id=ep.id,
                    host=ep.host,
                    port=ep.port,
                    severity="MEDIUM",
                    title=f"Quantum-{qs.lower()} algorithm: {ep.cert_pubkey_alg}",
                    protocol=ep.protocol,
                    description=f"{ep.cert_pubkey_alg} is classified as quantum-{qs.lower()} under NIST PQC evaluation.",
                    remediation="Plan migration to a post-quantum algorithm per the NIST PQC roadmap.",
                    quantum_risk=qs,
                    source="tls",
                    sensor_id=ep.sensor_id,
                    segment=ep.segment,
                ))
        except Exception:
            pass

    return findings


def _derive_findings(endpoints: list[CryptoEndpoint]) -> list[FindingItem]:
    """Synthesize findings from CryptoEndpoint rows.

    Findings are not stored in a separate table — they are derived at query time
    from the state of each endpoint. Delegates the per-endpoint branch logic to
    `findings_for_endpoint` (Phase 202 / 202-03, D-06) so there is exactly one
    implementation; this function retains only the two loop-level concerns
    that are properties of the endpoint LIST, not of any single endpoint:
    the KERBEROS/SAML/DNSSEC/JWT identity-protocol skip (a cross-endpoint filter
    decision, handled exclusively by `_derive_identity_findings`) and the
    final severity sort (a property of the assembled list, not any one
    endpoint's findings).
    """
    findings: list[FindingItem] = []

    for ep in endpoints:
        # D-03: skip identity protocol endpoints — handled exclusively by
        # _derive_identity_findings(); none of the TLS checks apply to them.
        proto = (ep.protocol or "").upper()
        if proto in {"KERBEROS", "SAML", "DNSSEC", "JWT"}:
            continue

        findings.extend(findings_for_endpoint(ep))

    # Sort: CRITICAL > HIGH > MEDIUM > LOW > INFO
    _severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    findings.sort(key=lambda f: _severity_order.get(f.severity, 99))
    return findings


def derive_dashboard_finding_items(endpoints) -> list[FindingItem]:
    """The ONE finding recipe behind every dashboard score (Phase 228 D-08).

    Order: dashboard TLS findings, identity findings (D-23: /compare gets them
    too), then the report's email/broker/code-signing findings (D-20: the report
    evaluators are adopted, not new detection; same adapter shape as the Phase 210
    SAML precedent, with the report's ``recommendation`` key mapped to
    ``remediation``), then container crypto-library findings (Phase 236 D-06,
    the report's own container evaluator). Router-free: no FastAPI or DB use.
    """
    eps = list(endpoints)
    findings = _derive_findings(eps)
    for idf in _derive_identity_findings(eps):
        findings.append(FindingItem(
            host=idf.host,
            port=idf.port,
            severity=idf.severity,
            title=idf.title,
            protocol=idf.protocol,
            description=idf.description,
            remediation=idf.remediation,
            quantum_risk=idf.quantum_risk,
            source=idf.source,
        ))
    for d in evaluate_protocol_service_endpoints(eps):
        findings.append(FindingItem(
            host=d["host"],
            port=d["port"],
            severity=d["severity"],
            title=d["title"],
            protocol=d.get("protocol"),
            description=d.get("description"),
            remediation=d.get("recommendation"),
            quantum_risk=d.get("quantum_risk"),
            source=d.get("source"),
        ))
    for d in evaluate_container_endpoints(eps):
        findings.append(FindingItem(
            host=d["host"],
            port=d["port"],
            severity=d["severity"],
            title=d["title"],
            protocol="CONTAINER",
            description=d.get("description"),
            remediation=d.get("recommendation"),
            quantum_risk=d.get("quantum_risk"),
            source=d.get("source"),
        ))
    return findings


def derive_dashboard_scoring_findings(endpoints) -> list[dict]:
    """``derive_dashboard_finding_items`` as plain dicts (the ``findings_deriver``
    callable for trends/merge, Phase 228 D-08)."""
    return [f.model_dump() for f in derive_dashboard_finding_items(endpoints)]


def finding_by_id_and_title(
    db: Session, endpoint_id: int, title: str
) -> tuple[Optional[CryptoEndpoint], Optional[FindingItem]]:
    """Resolve the ONE finding identified by (CryptoEndpoint.id, title).

    Phase 202 / 202-03 (D-06): `FindingItem.id` IS `CryptoEndpoint.id` —
    `findings_for_endpoint` yields multiple findings per endpoint, all
    sharing that id, so `title` is the disambiguator. Exact string match
    against the titles `findings_for_endpoint` produces for this endpoint —
    not prefix or fuzzy — because the client sends back the exact title it
    rendered from a prior `GET /api/scan/latest` response.

    Returns:
        (endpoint, finding) — the resolved pair, when both exist.
        (endpoint, None) — the endpoint exists but no finding on it matches
            `title` (lets the caller distinguish this from "no such endpoint").
        (None, None) — no endpoint with this id exists at all.
    """
    ep = db.query(CryptoEndpoint).filter(CryptoEndpoint.id == endpoint_id).one_or_none()
    if ep is None:
        return None, None

    for finding in findings_for_endpoint(ep):
        if finding.title == title:
            return ep, finding

    return ep, None


def _derive_identity_findings(endpoints: list[CryptoEndpoint]) -> list[IdentityFinding]:
    """Synthesize identity protocol findings from KERBEROS/SAML/DNSSEC/JWT endpoints.

    SAML and JWT (JWKS key, Phase 238 IDENT-05/IDENT-06 D-01) rows are
    delegated to the shared ``evaluate_identity_endpoints``.

    Per D-06: single derivation function returns IdentityFinding list.
    Per D-07: results are exposed as identity_findings AND converted to FindingItem
    for the main findings list.
    """
    results: list[IdentityFinding] = []

    # Phase 210 (XSURF-01/XSURF-02, D-06): SAML synthesis — including the
    # (host, port, cert serial) dedupe — is delegated to the shared evaluator
    # so the CLI and dashboard pipelines share one implementation instead of
    # two. This block is a thin dict -> IdentityFinding adapter; it does not
    # own any SAML finding-synthesis logic itself.
    # Phase 238 D-01: JWT (JWKS key) rows go through the same evaluator. They
    # match no branch in the per-endpoint loop below on purpose (there is no
    # fallthrough else), so they are evaluated exactly once.
    identity_eval_endpoints = [
        ep for ep in endpoints if (ep.protocol or "").upper() in ("SAML", "JWT")
    ]
    for d in evaluate_identity_endpoints(identity_eval_endpoints):
        results.append(IdentityFinding(
            host=d["host"],
            port=d["port"],
            severity=d["severity"],
            title=d["title"],
            protocol=d.get("protocol"),
            description=d.get("description"),
            remediation=d.get("recommendation"),  # key name differs at the boundary
            quantum_risk=d.get("quantum_risk"),
            source=d.get("source"),
            algorithm=d.get("algorithm") or "",  # required field, no default
        ))

    for ep in endpoints:
        proto = (ep.protocol or "").upper()

        if proto == "KERBEROS":
            sd = ep.service_detail or ""
            # service_detail format: "etype:{id}:{name}:{severity}"
            parts = sd.split(":")
            if len(parts) >= 4 and parts[0] == "etype":
                etype_id = parts[1]
                name = parts[2]
                severity = parts[3]
                if severity in ("CRITICAL", "HIGH"):
                    results.append(IdentityFinding(
                        host=ep.host,
                        port=ep.port,
                        severity=severity,
                        title=f"Kerberos weak etype: {name}",
                        protocol="KERBEROS",
                        description=(
                            f"KDC accepts etype {etype_id} ({name}) which is classified as {severity}. "
                            f"RC4 and DES etypes are cryptographically weak and quantum-vulnerable."
                        ),
                        remediation=(
                            "Disable RC4-HMAC and DES etypes in KDC configuration. "
                            "Enforce AES-256 (etype 18/20) as minimum."
                        ),
                        quantum_risk="Vulnerable",
                        source="kerberos",
                        algorithm=name,
                    ))

        elif proto == "SAML":
            # Phase 210 D-06: handled above, once, via evaluate_identity_endpoints —
            # this branch intentionally does nothing so proto=="SAML" rows are not
            # ALSO routed to the fallthrough/unknown-protocol path below.
            pass

        elif proto == "DNSSEC":
            alg = (ep.cert_pubkey_alg or "").upper()
            sd = ep.service_detail or ""

            _DNSSEC_WEAK_MAP = {
                "RSASHA1": ("CRITICAL", "RSASHA1 (algorithm 5) uses SHA-1 which is collision-vulnerable"),
                "RSASHA1-NSEC3-SHA1": ("CRITICAL", "RSASHA1-NSEC3-SHA1 (algorithm 7) uses SHA-1"),
                "RSAMD5": ("CRITICAL", "RSAMD5 (algorithm 1) uses MD5 which is broken"),
                "DSA": ("CRITICAL", "DSA (algorithm 3) is deprecated by NIST"),
                "DSA-NSEC3-SHA1": ("CRITICAL", "DSA-NSEC3-SHA1 (algorithm 6) is deprecated"),
                "NONE": ("HIGH", "Zone has no DNSSEC signing — DNS responses are unauthenticated"),
                "SHA1-DS": ("HIGH", "DS record uses SHA-1 digest — vulnerable to collision attacks"),
                "DS-MISMATCH": ("HIGH", "DS record key tag does not match any DNSKEY — broken chain of trust"),
                "NSEC": ("MEDIUM", "Zone uses NSEC records — enables zone enumeration by walking"),
            }

            if alg in _DNSSEC_WEAK_MAP:
                severity, desc = _DNSSEC_WEAK_MAP[alg]
                if alg == "NONE":
                    remediation = "Deploy DNSSEC signing with a strong algorithm."
                elif alg == "SHA1-DS":
                    remediation = "Replace SHA-1 DS digest with SHA-256 (digest type 2)."
                elif alg == "DS-MISMATCH":
                    remediation = "Verify DS records match published DNSKEYs."
                elif severity == "CRITICAL":
                    remediation = "Migrate to ECDSAP256SHA256 (algorithm 13) or Ed25519 (algorithm 15) per RFC 8624."
                else:
                    remediation = "Consider using NSEC3 with opt-out to prevent zone walking."
                results.append(IdentityFinding(
                    host=ep.host,
                    port=ep.port,
                    severity=severity,
                    title=f"DNSSEC: {alg.replace('-', ' ').replace('_', ' ')}",
                    protocol="DNSSEC",
                    description=desc,
                    remediation=remediation,
                    quantum_risk="Vulnerable" if severity == "CRITICAL" else None,
                    source="dnssec",
                    algorithm=ep.cert_pubkey_alg or alg,  # preserve original case
                ))

    # Sort by severity
    _severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    results.sort(key=lambda f: _severity_order.get(f.severity, 99))
    return results

