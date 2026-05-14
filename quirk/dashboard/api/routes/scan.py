"""GET /api/scan/latest — returns the most recent scan session's full results."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from quirk.errors import format_error
from quirk.dashboard.api.middleware.auth import require_auth
from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import (
    CbomComponent,
    CertItem,
    CompareEndpoint,
    CompareFinding,
    CompareResponse,
    CompareScanSummary,
    ConfidenceData,
    DarFinding,
    FindingCounts,
    FindingItem,
    IdentityFinding,
    MotionFinding,
    PartialFailureEntry,
    RoadmapData,
    RoadmapEdge,
    RoadmapNode,
    ScanLatestResponse,
    ScanMeta,
    ScanSession,
    ScoreData,
    SubScores,
    SubscoreDelta,
)
from quirk.models import CryptoEndpoint, ScanJob
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.trends import _count_by_bucket
from quirk.scanner.saml_scanner import OIDC_ALG_SEVERITY

router = APIRouter(dependencies=[Depends(require_auth)])

# Phase 38 (D-01): backward bracket from MAX(scanned_at) restores SAML/OIDC visibility under timestamp skew
SESSION_BRACKET = timedelta(minutes=5)

# Map classifier raw labels to frontend display values
_QS_DISPLAY = {
    "quantum-safe": "Safe",
    "quantum-vulnerable": "Vulnerable",
    "hybrid": "At Risk",
    "unknown": "Unknown",
}


def _derive_findings(endpoints: list[CryptoEndpoint]) -> list[FindingItem]:
    """Synthesize findings from CryptoEndpoint rows.

    Findings are not stored in a separate table — they are derived at query time
    from the state of each endpoint.
    """
    now = datetime.now(tz=timezone.utc)
    findings: list[FindingItem] = []

    for ep in endpoints:
        # D-03: skip identity protocol endpoints — handled exclusively by
        # _derive_identity_findings(); none of the TLS checks apply to them.
        proto = (ep.protocol or "").upper()
        if proto in {"KERBEROS", "SAML", "DNSSEC"}:
            continue

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
            ))

        # Legacy TLS version
        if ep.tls_version and ep.tls_version in ("TLSv1", "TLSv1.1", "TLS 1.0", "TLS 1.1"):
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
                ))
            elif days_to_expiry < 30:
                findings.append(FindingItem(
                    id=ep.id,
                    host=ep.host,
                    port=ep.port,
                    severity="HIGH",
                    title=f"Certificate expiring in {days_to_expiry} day(s)",
                    protocol="TLS",
                    description="Certificate expires within 30 days.",
                    remediation="Renew certificate before expiry to avoid service interruption.",
                    quantum_risk=None,
                    source="tls",
                ))

        # Weak RSA key
        if (
            ep.cert_pubkey_alg
            and ep.cert_pubkey_alg.upper().startswith("RSA")
            and ep.cert_pubkey_size
            and ep.cert_pubkey_size < 2048
        ):
            findings.append(FindingItem(
                id=ep.id,
                host=ep.host,
                port=ep.port,
                severity="CRITICAL",
                title=f"Weak RSA key: {ep.cert_pubkey_size} bits",
                protocol="TLS",
                description=f"Certificate uses {ep.cert_pubkey_size}-bit RSA key, below the 2048-bit minimum.",
                remediation="Replace certificate with RSA-2048 minimum or switch to ECDSA P-256.",
                quantum_risk="Vulnerable",
                source="tls",
            ))

        # Quantum-vulnerable algorithm (non-RSA)
        if ep.cert_pubkey_alg and not ep.cert_pubkey_alg.upper().startswith("RSA"):
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
                    ))
            except Exception:
                pass

    # Sort: CRITICAL > HIGH > MEDIUM > LOW > INFO
    _severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    findings.sort(key=lambda f: _severity_order.get(f.severity, 99))
    return findings


def _derive_identity_findings(endpoints: list[CryptoEndpoint]) -> list[IdentityFinding]:
    """Synthesize identity protocol findings from KERBEROS/SAML/DNSSEC endpoints.

    Per D-06: single derivation function returns IdentityFinding list.
    Per D-07: results are exposed as identity_findings AND converted to FindingItem
    for the main findings list.
    """
    results: list[IdentityFinding] = []

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
            alg = (ep.cert_pubkey_alg or "").upper()
            size = ep.cert_pubkey_size
            sd = ep.service_detail or ""

            # RS-family OIDC check (D-01, D-02) — runs before SHA-1 check (highest specificity)
            severity = OIDC_ALG_SEVERITY.get(alg)
            if severity is not None:
                results.append(IdentityFinding(
                    host=ep.host,
                    port=ep.port,
                    severity=severity,
                    title=f"OIDC RS-family algorithm: {alg}",
                    protocol="SAML",
                    description=(
                        f"OIDC endpoint uses {alg} which relies on RSA. "
                        f"RSA is quantum-vulnerable and will be broken by Shor's algorithm."
                    ),
                    remediation=(
                        "Migrate OIDC token signing to ECDSA (ES256/ES384) or EdDSA "
                        "per NIST PQC roadmap recommendations."
                    ),
                    quantum_risk="Vulnerable",
                    source="saml",
                    algorithm=alg,
                ))
            elif alg == "SHA1":
                results.append(IdentityFinding(
                    host=ep.host,
                    port=ep.port,
                    severity="HIGH",
                    title="SHA-1 algorithm URI detected in SAML metadata",
                    protocol="SAML",
                    description=(
                        "SAML metadata references SHA-1 signing algorithm. "
                        "SHA-1 is collision-vulnerable since 2017 (SHAttered attack)."
                    ),
                    remediation="Update IdP to use SHA-256 or SHA-384 signature algorithms.",
                    quantum_risk="Vulnerable",
                    source="saml",
                    algorithm="SHA1",
                ))
            elif alg not in OIDC_ALG_SEVERITY and size is not None and isinstance(size, int) and size < 2048:
                results.append(IdentityFinding(
                    host=ep.host,
                    port=ep.port,
                    severity="CRITICAL",
                    title=f"Weak SAML signing certificate: {alg}-{size}",
                    protocol="SAML",
                    description=(
                        f"SAML signing certificate uses {size}-bit {alg} key, "
                        f"below the 2048-bit minimum for RSA."
                    ),
                    remediation=(
                        "Replace IdP signing certificate with RSA-2048 minimum "
                        "or switch to ECDSA P-256."
                    ),
                    quantum_risk="Vulnerable",
                    source="saml",
                    algorithm=f"{alg}-{size}" if size else alg,
                ))

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


def _derive_motion_findings(endpoints) -> list[MotionFinding]:
    """Synthesize motion findings from email + broker CryptoEndpoints.

    Mirrors _derive_identity_findings (lines 184-330). Carries protocol labels
    verbatim — does NOT normalize "AMQPS/Azure-ServiceBus" (Phase 35 D-03).
    Per RESEARCH.md Pitfall 5, uses getattr() for cipher_suite/cert_not_after.
    """
    EMAIL_PROTOS = {"SMTP-STARTTLS", "SMTPS", "IMAP-STARTTLS", "IMAPS",
                    "POP3-STARTTLS", "POP3S"}
    BROKER_PLAIN = {"KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN"}
    BROKER_TLS = {"KAFKA-TLS", "AMQPS", "AMQPS/Azure-ServiceBus",
                  "HTTPS/AWS-SQS", "REDIS-TLS"}
    MOTION_PROTOS = EMAIL_PROTOS | BROKER_PLAIN | BROKER_TLS
    LEGACY_TLS = {"TLSv1", "TLSv1.0", "TLSv1.1"}

    results: list[MotionFinding] = []
    for ep in endpoints:
        proto = getattr(ep, "protocol", None) or ""
        if proto not in MOTION_PROTOS:
            continue
        port = getattr(ep, "port", 0) or 0
        tls_version = getattr(ep, "tls_version", None) or None
        cipher_suite = getattr(ep, "cipher_suite", None) or None
        cert_dt = getattr(ep, "cert_not_after", None)
        cert_iso = cert_dt.isoformat() if cert_dt else None

        plaintext = proto in BROKER_PLAIN
        starttls_warning = (port == 25 and proto == "SMTP-STARTTLS")

        # Severity rules (per RESEARCH.md §"Pattern 2"):
        if plaintext:
            severity = "HIGH"
            title = f"{proto} plaintext listener exposed"
            quantum_risk = "n/a (plaintext)"
            description = f"{proto} listener accepts plaintext traffic — credentials and message bodies traverse the network unencrypted."
            remediation = "Disable plaintext listener; require TLS-only with modern ciphers and plan PQC migration."
        elif starttls_warning:
            severity = "MEDIUM"
            title = "SMTP STARTTLS susceptible to stripping (port 25)"
            quantum_risk = "depends on negotiated cipher"
            description = "Port 25 SMTP with opportunistic STARTTLS can be downgraded to plaintext by an active attacker (STARTTLS stripping)."
            remediation = "Enforce MTA-STS / DANE, prefer submission on 587 with required STARTTLS, and monitor for downgrade attempts."
        elif proto in BROKER_TLS and tls_version in LEGACY_TLS:
            severity = "HIGH"
            title = f"{proto} legacy TLS version ({tls_version})"
            quantum_risk = "quantum-vulnerable"
            description = f"{proto} endpoint negotiated legacy TLS version {tls_version}, which is deprecated and exposes traffic to known protocol weaknesses."
            remediation = "Upgrade broker/client to TLS 1.2+ (prefer TLS 1.3), disable legacy versions, and plan PQC migration."
        else:
            severity = "LOW"
            title = f"{proto} TLS endpoint"
            quantum_risk = "quantum-vulnerable" if cipher_suite and "RSA" in cipher_suite else "quantum-unknown"
            description = f"{proto} is using TLS. Verify cipher suite and certificate strength."
            remediation = "Enforce TLS 1.2+, disable weak ciphers, and plan PQC migration."

        results.append(MotionFinding(
            host=getattr(ep, "host", "") or "",
            port=port,
            severity=severity,
            title=title,
            protocol=proto,            # verbatim — preserve "AMQPS/Azure-ServiceBus"
            description=description,
            remediation=remediation,
            tls_version=tls_version,
            cipher_suite=cipher_suite,
            cert_not_after=cert_iso,
            quantum_risk=quantum_risk,
            plaintext_exposed=plaintext,
            starttls_warning=starttls_warning,
            source="motion",
        ))

    _severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    results.sort(key=lambda f: _severity_order.get(f.severity, 99))
    return results


# ---- DAR Findings (Phase 39 GAP-04) ----

DAR_PROTOCOLS = {"POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES", "VAULT"}


def _derive_dar_findings(endpoints) -> list[DarFinding]:
    """Synthesize DarFinding list from CryptoEndpoints with DAR posture data.

    Mirrors _derive_motion_findings (Phase 36). Per-protocol dispatch handles
    scanner shape variance: POSTGRESQL/MYSQL/RDS use service_detail; S3, AZURE_BLOB,
    KUBERNETES, VAULT use dat_scan_json. Endpoints with scan_error are skipped.
    Malformed dat_scan_json is tolerated via try/except (V5).
    """
    results: list[DarFinding] = []
    for ep in endpoints:
        if getattr(ep, "scan_error", None):
            continue
        proto = (getattr(ep, "protocol", None) or "").upper()
        if proto not in DAR_PROTOCOLS:
            continue

        host = getattr(ep, "host", "") or ""
        port = getattr(ep, "port", 0) or 0
        severity = getattr(ep, "severity", None) or "INFO"
        service_detail = getattr(ep, "service_detail", None) or ""
        dat_raw = getattr(ep, "dat_scan_json", None)
        dat: dict = {}
        if dat_raw:
            try:
                dat = json.loads(dat_raw)
            except Exception:
                dat = {}

        if proto in {"POSTGRESQL", "MYSQL"}:
            finding = _dar_db(host, port, proto, severity, service_detail)
        elif proto == "RDS":
            finding = _dar_rds(host, port, severity, service_detail)
        elif proto == "S3":
            finding = _dar_s3(host, port, severity, dat)
        elif proto == "AZURE_BLOB":
            finding = _dar_azure_blob(host, port, severity, dat)
        elif proto == "KUBERNETES":
            finding = _dar_k8s(host, port, severity, dat)
        elif proto == "VAULT":
            finding = _dar_vault(host, port, severity, dat)
        else:
            finding = None

        if finding is not None:
            results.append(finding)

    _sev = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    results.sort(key=lambda f: _sev.get(f.severity, 99))
    return results


def _dar_db(host, port, proto, severity, service_detail):
    sd = service_detail or ""
    if "ssl-enforced" in sd:
        enc, tls = True, True
    elif "ssl-off" in sd or "plaintext-connections-allowed" in sd:
        enc, tls = False, False
    elif "-weak" in sd or "-ok" in sd:
        enc, tls = True, True
    else:
        enc, tls = None, None
    return DarFinding(
        host=host, port=port, severity=severity,
        title=f"{proto} encryption posture",
        protocol=proto, category="database",
        encryption_at_rest=enc, tls_in_transit=tls,
        source="database",
    )


def _dar_rds(host, port, severity, service_detail):
    sd = service_detail or ""
    if sd == "RDS/none":
        enc, kms = False, None
    elif sd == "RDS/sse-rds":
        enc, kms = True, None
    elif sd == "RDS/sse-kms-aws":
        enc, kms = True, "AWS-managed"
    elif sd == "RDS/sse-kms-cmk":
        enc, kms = True, "CMK"
    else:
        enc, kms = None, None
    return DarFinding(
        host=host, port=port, severity=severity,
        title="RDS encryption-at-rest",
        protocol="RDS", category="database",
        encryption_at_rest=enc, kms_key_id=kms,
        source="database",
    )


# Note: S3/Azure/K8s/Vault helpers receive the parsed dat dict (not service_detail
# from the endpoint object) — these protocols store context in dat_scan_json only.
def _dar_s3(host, port, severity, dat):
    sd = (dat.get("service_detail") or "").lower()
    kms = None
    if sd == "s3/unencrypted":
        enc, mode = False, "none"
    elif sd == "s3/sse-s3":
        enc, mode = True, "SSE-S3"
    elif sd == "s3/sse-kms-aws":
        enc, mode, kms = True, "SSE-KMS", "AWS-managed"
    elif sd == "s3/sse-kms-cmk":
        enc, mode, kms = True, "SSE-KMS", "CMK"
    else:
        enc, mode = None, None
    bucket = dat.get("bucket", "")
    return DarFinding(
        host=host, port=port, severity=severity,
        title=f"S3 bucket {bucket}".strip(),
        protocol="S3", category="object_storage",
        encryption_at_rest=enc, encryption_mode=mode,
        kms_key_id=kms,
        public_access=None,   # not probed by scanner (Pitfall 6)
        versioning=None,      # not probed by scanner
        source="object_storage",
    )


def _dar_azure_blob(host, port, severity, dat):
    key_source = (dat.get("key_source") or "").lower()
    if key_source == "microsoft.keyvault":
        enc, mode = True, "CMK"
    else:
        enc, mode = True, "SSE-S3"
    account = dat.get("account", "")
    container = dat.get("container", "")
    return DarFinding(
        host=host, port=port, severity=severity,
        title=f"Azure Blob {account}/{container}",
        protocol="AZURE_BLOB", category="object_storage",
        encryption_at_rest=enc, encryption_mode=mode,
        source="object_storage",
    )


def _dar_k8s(host, port, severity, dat):
    if "namespace" in dat:
        ns = dat.get("namespace", "")
        counts = dat.get("secret_type_counts", {}) or {}
        secret_type = ", ".join(
            f"{t}:{c}" for t, c in sorted(counts.items(), key=lambda x: -x[1])
        ) or None
        return DarFinding(
            host=host, port=port, severity=severity,
            title=f"K8s secrets in namespace {ns}",
            protocol="KUBERNETES", category="kubernetes",
            namespace=ns or None, secret_type=secret_type,
            source="kubernetes",
        )
    provider = dat.get("provider", "") or ""
    if provider == "EKS":
        cfg = dat.get("encryptionConfig") or []
        encrypted = any(
            "secrets" in (entry.get("resources") or [])
            for entry in cfg if isinstance(entry, dict)
        )
        enc_provider = "EKS/KMS" if encrypted else None
    elif provider == "GKE":
        encrypted = dat.get("current_state") == 2
        enc_provider = "GKE/Cloud-KMS" if encrypted else None
    elif provider == "AKS":
        encrypted = bool(dat.get("kv_kms_enabled"))
        enc_provider = "AKS/Key-Vault" if encrypted else None
    else:
        encrypted, enc_provider = None, None
    return DarFinding(
        host=host, port=port, severity=severity,
        title=f"{provider or 'K8s'} cluster etcd encryption",
        protocol="KUBERNETES", category="kubernetes",
        encryption_at_rest=encrypted, encryption_provider=enc_provider,
        source="kubernetes",
    )


def _dar_vault(host, port, severity, dat):
    if "key_name" in dat:
        mount_type = "transit"
        title = f"Vault transit key: {dat.get('key_type', '')}".strip(": ")
    elif "mount_point" in dat:
        mount_type = "pki"
        title = f"Vault PKI: {dat.get('mount_point', '')}"
    elif "auth_path" in dat:
        mount_type = "auth"
        title = f"Vault auth: {dat.get('auth_type', '')}"
    else:
        mount_type = None
        title = "Vault endpoint"
    return DarFinding(
        host=host, port=port, severity=severity,
        title=title,
        protocol="VAULT", category="vault",
        mount_type=mount_type,
        seal_type=None,       # not probed (Pitfall 4)
        auto_unseal=None,     # not probed (Pitfall 4)
        remediation=dat.get("remediation"),
        source="vault",
    )


def _derive_cbom(endpoints: list[CryptoEndpoint]) -> list[CbomComponent]:
    """Build CBOM components from endpoints by aggregating algorithm usage."""
    from quirk.cbom.classifier import classify_algorithm, quantum_safety_label

    def _qs_for_alg(alg: str) -> str:
        try:
            _, nist_level, _ = classify_algorithm(alg)
            raw = quantum_safety_label(nist_level)
        except Exception:
            raw = "unknown"
        return _QS_DISPLAY.get(raw, "Unknown")

    algo_map: dict[str, dict] = {}  # algorithm -> {quantum_safety, source_systems: set}

    for ep in endpoints:
        if ep.cert_pubkey_alg:
            alg = ep.cert_pubkey_alg
            qs = _qs_for_alg(alg)
            if alg not in algo_map:
                algo_map[alg] = {"quantum_safety": qs, "key_size": ep.cert_pubkey_size, "type": "signature", "sources": set()}
            algo_map[alg]["sources"].add(f"{ep.host}:{ep.port}")

        if ep.tls_version:
            alg = f"TLS-{ep.tls_version}"
            if alg not in algo_map:
                algo_map[alg] = {"quantum_safety": "Unknown", "key_size": None, "type": "protocol", "sources": set()}
            algo_map[alg]["sources"].add(f"{ep.host}:{ep.port}")

        # Parse SSH audit JSON for algorithm inventory
        if ep.ssh_audit_json:
            try:
                ssh_data = json.loads(ep.ssh_audit_json)
            except (json.JSONDecodeError, TypeError, ValueError):
                ssh_data = {}
            _SSH_TYPE = {"kex": "key-exchange", "key": "signature", "enc": "cipher", "mac": "hash"}
            for section, alg_type in _SSH_TYPE.items():
                for entry in ssh_data.get(section, []):
                    alg = entry.get("algorithm") if isinstance(entry, dict) else None
                    if not alg:
                        continue
                    qs = _qs_for_alg(alg)
                    if alg not in algo_map:
                        algo_map[alg] = {
                            "quantum_safety": qs,
                            "key_size": entry.get("keysize"),
                            "type": alg_type,
                            "sources": set(),
                        }
                    algo_map[alg]["sources"].add(f"{ep.host}:{ep.port}")

        # Parse JWT/cloud/container scan JSON for algorithms
        for json_col in (ep.jwt_scan_json, ep.cloud_scan_json):
            if not json_col:
                continue
            try:
                data = json.loads(json_col)
                alg_field = data.get("algorithm") or data.get("alg")
                if alg_field:
                    qs = _qs_for_alg(str(alg_field))
                    if alg_field not in algo_map:
                        algo_map[alg_field] = {"quantum_safety": qs, "key_size": None, "type": "signature", "sources": set()}
                    algo_map[alg_field]["sources"].add(f"{ep.host}:{ep.port}")
            except (json.JSONDecodeError, AttributeError):
                pass

    return [
        CbomComponent(
            algorithm=alg,
            type=info["type"],
            key_size=info.get("key_size"),
            quantum_safety=info["quantum_safety"],
            source_systems=sorted(info["sources"]),
        )
        for alg, info in sorted(algo_map.items())
    ]


def _derive_roadmap(evidence: dict, scoring: dict) -> RoadmapData:
    """Build migration roadmap graph from build_phased_roadmap()."""
    try:
        from quirk.intelligence.roadmap import build_phased_roadmap
        roadmap = build_phased_roadmap(evidence, scoring)
    except Exception:
        return RoadmapData(nodes=[], edges=[])

    nodes: list[RoadmapNode] = []
    edges: list[RoadmapEdge] = []

    # build_phased_roadmap returns {"items": [...each with "phase"/"title"/"why"/"timeframe"...], ...}
    items_list = roadmap.get("items", []) if isinstance(roadmap, dict) else []
    timeframe_map = {"NOW": "0-30 days", "NEXT": "31-90 days", "LATER": "90+ days"}

    for item in items_list:
        if not isinstance(item, dict):
            continue
        phase_key = str(item.get("phase", "NOW"))
        title = str(item.get("title", ""))
        node_id = f"{phase_key}-{title[:20].replace(' ', '-').lower()}"
        nodes.append(RoadmapNode(
            id=node_id,
            title=title,
            timeframe=item.get("timeframe") or timeframe_map.get(phase_key, phase_key),
            why=str(item.get("why", "")),
            phase=phase_key,
        ))

    # Add phase-to-phase ordering edges (connect last NOW → first NEXT, last NEXT → first LATER)
    for phase_a, phase_b in [("NOW", "NEXT"), ("NEXT", "LATER")]:
        src_items = [n for n in nodes if n.phase == phase_a]
        tgt_items = [n for n in nodes if n.phase == phase_b]
        if src_items and tgt_items:
            edges.append(RoadmapEdge(source=src_items[-1].id, target=tgt_items[0].id, reason="Phase dependency"))

    return RoadmapData(nodes=nodes, edges=edges)


def _fetch_session_endpoints_1s(db: Session, ts: datetime) -> list[CryptoEndpoint]:
    """Fetch CryptoEndpoint rows for a session using a 1-second window.

    list_scans() and compare_scans() group by second-precision timestamps,
    so we cannot reuse trends._fetch_session_endpoints (1ms window — incompatible
    with second-precision ts_sec strings from the GROUP BY query).
    """
    return (
        db.query(CryptoEndpoint)
        .filter(
            CryptoEndpoint.scanned_at >= ts,
            CryptoEndpoint.scanned_at < ts + timedelta(seconds=1),
            CryptoEndpoint.scanned_at.isnot(None),
        )
        .all()
    )


@router.get("/scans", response_model=List[ScanSession])
def list_scans(db: Session = Depends(get_db)) -> List[ScanSession]:
    """GET /api/scans — returns ALL distinct scan sessions, newest first.

    Phase 66 D-01: LIMIT 10 removed — return every session.
    Phase 66 D-02: per-session score computed inline via evidence pipeline.
    Phase 66 D-03: finding severity counts via _count_by_bucket.
    Phase 66 D-04: clone data from ScanJob join; fallback to host reconstruction.

    Groups by second-truncated timestamp because each CryptoEndpoint row is
    written with its own microsecond-precision scanned_at. Grouping by the raw
    value produces one row per endpoint rather than one per scan session.
    """
    ts_sec = func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at).label("ts_sec")
    rows = (
        db.query(ts_sec, func.count(CryptoEndpoint.id).label("cnt"))
        .group_by("ts_sec")
        .order_by(ts_sec.desc())
        .all()
    )  # NO LIMIT — per D-01

    sessions: list[ScanSession] = []
    for ts_str, cnt in rows:
        if ts_str is None:
            continue
        try:
            ts = datetime.fromisoformat(ts_str)
        except ValueError:
            continue

        eps = _fetch_session_endpoints_1s(db, ts)

        # Per-session score (D-02)
        score = 0
        if eps:
            evidence = build_evidence_summary(eps)
            score_dict = compute_readiness_score(evidence)
            score = int(score_dict["score"])

        # Finding counts (D-03)
        keys = [
            (ep.host, ep.port, ep.protocol, ep.severity)
            for ep in eps
            if ep.scan_error is None and ep.severity
        ]
        counts = _count_by_bucket(keys)

        # Clone data (D-04) — try ScanJob join first, fall back to host reconstruction
        # Use ts.isoformat()[:19] (T-separator) because scan_run_id is stored via
        # datetime.isoformat() — ts_str uses a space separator from strftime (Pitfall 2).
        ts_prefix = ts.isoformat()[:19]  # e.g. "2026-05-14T11:51:54"
        job = (
            db.query(ScanJob)
            .filter(ScanJob.scan_run_id.like(f"{ts_prefix}%"))
            .first()
        )
        if job is not None:
            target = job.target
            profile = job.profile
            calibration = job.calibration
        else:
            hosts = sorted({ep.host for ep in eps if ep.host})
            target = ", ".join(hosts) if hosts else None
            profile = None
            calibration = None

        sessions.append(
            ScanSession(
                scan_id=ts_str,
                scanned_at=ts,
                total_endpoints=cnt,
                score=score,
                profile=profile,
                calibration=calibration,
                target=target,
                finding_counts=FindingCounts(
                    high=counts.get("high", 0),
                    medium=counts.get("medium", 0),
                    low=counts.get("low", 0),
                ),
            )
        )
    return sessions


def _cert_expiry_key(c: "CertItem") -> datetime:
    """Return a timezone-aware datetime for sorting; normalises naive datetimes to UTC."""
    dt = c.cert_not_after
    if dt is None:
        return datetime.max.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _load_partial_failures(db: Session, scan_run_id_str: str) -> list[PartialFailureEntry]:
    """Phase 67 RESUME-02: load partial_failures from scan_checkpoints.error_summary.

    Returns [] if no checkpoints exist (pre-Phase 67 scans or clean scans).
    scan_run_id_str: ISO timestamp string (same as CryptoEndpoint.scanned_at value).
    """
    import json as _json
    try:
        from quirk.models import ScanCheckpoint
        cps = (
            db.query(ScanCheckpoint)
            .filter(
                ScanCheckpoint.scan_run_id == scan_run_id_str,
                ScanCheckpoint.partial_failure == True,  # noqa: E712
            )
            .all()
        )
        result: list[PartialFailureEntry] = []
        for cp in cps:
            if not cp.error_summary:
                continue
            try:
                entries = _json.loads(cp.error_summary)
                for entry in entries:
                    result.append(PartialFailureEntry(
                        stage=cp.stage,
                        scanner=entry.get("scanner", "unknown"),
                        error_category=entry.get("error_category", "exception"),
                        error_message=entry.get("error_message", ""),
                        endpoint_count=entry.get("endpoint_count", 0),
                    ))
            except (ValueError, KeyError):
                pass
        return result
    except Exception:
        return []


@router.get("/scan/latest", response_model=ScanLatestResponse)
def get_latest_scan(
    scan_id: Optional[str] = Query(default=None, description="ISO timestamp scan_id to load; omit for latest"),
    db: Session = Depends(get_db),
) -> ScanLatestResponse:
    """GET /api/scan/latest — returns a scan session's full results.

    Without ?scan_id=: returns the most recent scan (MAX scanned_at).
    With ?scan_id=<ISO timestamp>: returns that specific scan session.
    """
    if scan_id is not None:
        try:
            target_ts = datetime.fromisoformat(scan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=format_error("DASHBOARD-004"))
        endpoints: list[CryptoEndpoint] = (
            db.query(CryptoEndpoint)
            .filter(
                CryptoEndpoint.scanned_at >= target_ts,
                CryptoEndpoint.scanned_at < target_ts + timedelta(seconds=1),
            )
            .all()
        )
        if not endpoints:
            raise HTTPException(status_code=404, detail=format_error("DASHBOARD-005"))
        latest_ts = target_ts
    else:
        # D-01: anchor on MAX(scanned_at), then load all endpoints in the
        # SESSION_BRACKET window before that maximum. This restores SAML/OIDC
        # findings that the previous 1-second forward window silently excluded
        # when Kerberos finished last (ISSUE-3 / DEF-v4.4-02).
        latest_ts = db.query(func.max(CryptoEndpoint.scanned_at)).scalar()
        if latest_ts is None:
            raise HTTPException(
                status_code=404,
                detail=format_error("DASHBOARD-006"),
            )
        endpoints: list[CryptoEndpoint] = (
            db.query(CryptoEndpoint)
            .filter(
                CryptoEndpoint.scanned_at >= latest_ts - SESSION_BRACKET,
                CryptoEndpoint.scanned_at <= latest_ts,
            )
            .all()
        )

    if not endpoints:
        raise HTTPException(status_code=404, detail=format_error("DASHBOARD-006"))

    # Derive findings first — needed by evidence summary
    findings = _derive_findings(endpoints)

    # Derive identity findings (IDENT-02 + IDENT-04)
    identity_findings = _derive_identity_findings(endpoints)

    # Per D-07: append identity findings as FindingItem to main findings list
    for idf in identity_findings:
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

    # Build evidence summary for intelligence functions
    try:
        from quirk.intelligence.evidence import build_evidence_summary
        evidence = build_evidence_summary(endpoints, [f.model_dump() for f in findings])
    except Exception:
        evidence = {}

    # Read scan-time profile from intelligence JSON (SCORE-04)
    stored_profile = None
    try:
        import os as _os
        from pathlib import Path as _Path
        from quirk.validate import _latest_intelligence
        import json as _json
        _output_dir = _Path(_os.environ.get("QUIRK_OUTPUT_DIR", "./quirk-output"))
        _intel_path = _latest_intelligence(_output_dir)
        if _intel_path:
            _intel_data = _json.loads(_intel_path.read_text(encoding="utf-8"))
            stored_profile = _intel_data.get("calibration", {}).get("profile")
    except Exception:
        pass  # fall back to balanced default via profile=None

    # Compute score and confidence
    try:
        from quirk.intelligence.scoring import compute_readiness_score
        score_raw = compute_readiness_score(evidence, profile=stored_profile)
    except Exception:
        score_raw = {"score": 0, "rating": "POOR", "subscores": {}, "drivers": []}

    try:
        from quirk.intelligence.confidence import compute_confidence
        confidence_raw = compute_confidence(evidence)
    except Exception:
        confidence_raw = {"confidence_score": 0, "confidence_rating": "NO_DATA", "factor_breakdown": {}}

    subscores_raw = score_raw.get("subscores", {})
    score = ScoreData(
        score=score_raw.get("score", 0),
        rating=score_raw.get("rating", "POOR"),
        subscores=SubScores(
            hygiene=subscores_raw.get("hygiene", 0),
            modern_tls=subscores_raw.get("modern_tls", 0),
            identity_trust=subscores_raw.get("identity_trust", 0),
            agility_signals=subscores_raw.get("agility_signals", 0),
            data_at_rest=subscores_raw.get("data_at_rest", 0),
            data_in_motion=subscores_raw.get("data_in_motion", 0),   # NEW — fixes silent drop
        ),
        drivers=score_raw.get("drivers", []),
    )

    confidence = ConfidenceData(
        confidence_score=confidence_raw.get("confidence_score", 0),
        confidence_rating=confidence_raw.get("confidence_rating", "NO_DATA"),
        factor_breakdown=confidence_raw.get("factor_breakdown", {}),
    )

    # Derive remaining views
    certificates = [
        CertItem(
            host=ep.host,
            port=ep.port,
            cert_subject=ep.cert_subject,
            cert_issuer=ep.cert_issuer,
            cert_not_after=ep.cert_not_after,
            cert_pubkey_alg=ep.cert_pubkey_alg,
            cert_pubkey_size=ep.cert_pubkey_size,
            quantum_safety=_cert_quantum_safety(ep.cert_pubkey_alg),
        )
        for ep in endpoints
        if ep.protocol and ep.protocol.upper() == "TLS"
    ]
    # Sort certificates by expiry ascending (soonest first, per UI-SPEC)
    certificates.sort(key=_cert_expiry_key)

    cbom_components = _derive_cbom(endpoints)
    roadmap = _derive_roadmap(evidence, score_raw)

    response_scan_id = latest_ts.isoformat() if hasattr(latest_ts, "isoformat") else str(latest_ts)

    # Phase 67 RESUME-02: load partial_failures from scan_checkpoints.
    # CR-02: response_scan_id is MAX(scanned_at) (tz-naive ISO), but scan_checkpoints
    # rows are keyed by scan_run_id = started_utc (tz-aware ISO, different event).
    # Resolve the correct scan_run_id via ScanJob: find the completed ScanJob
    # whose completed_at is closest to latest_ts — its scan_run_id is the checkpoint key.
    _checkpoint_scan_run_id: Optional[str] = None
    try:
        _latest_ts_naive = latest_ts if isinstance(latest_ts, datetime) else None
        if _latest_ts_naive is not None:
            # Search window: scan completed within 30 minutes of latest_ts
            _window = timedelta(minutes=30)
            _job = (
                db.query(ScanJob)
                .filter(
                    ScanJob.status == "completed",
                    ScanJob.scan_run_id.isnot(None),
                    ScanJob.completed_at >= _latest_ts_naive - _window,
                    ScanJob.completed_at <= _latest_ts_naive + _window,
                )
                .order_by(ScanJob.completed_at.desc())
                .first()
            )
            if _job and _job.scan_run_id:
                _checkpoint_scan_run_id = _job.scan_run_id
    except Exception:
        pass
    partial_failures = _load_partial_failures(db, _checkpoint_scan_run_id) if _checkpoint_scan_run_id else []

    return ScanLatestResponse(
        meta=ScanMeta(
            scan_id=response_scan_id,
            scanned_at=latest_ts if isinstance(latest_ts, datetime) else None,
            total_endpoints=len(endpoints),
            total_findings=len(findings),
        ),
        score=score,
        confidence=confidence,
        findings=findings,
        certificates=certificates,
        cbom_components=cbom_components,
        roadmap=roadmap,
        identity_findings=identity_findings,
        motion_findings=_derive_motion_findings(endpoints),   # NEW — Phase 36 DASH-05
        dar_findings=_derive_dar_findings(endpoints),          # Phase 39 GAP-04
        partial_failures=partial_failures,                     # Phase 67 RESUME-02
    )


def _cert_quantum_safety(algorithm: Optional[str]) -> Optional[str]:
    if not algorithm:
        return None
    try:
        from quirk.cbom.classifier import classify_algorithm, quantum_safety_label
        _, nist_level, _ = classify_algorithm(algorithm)
        raw = quantum_safety_label(nist_level)
        return _QS_DISPLAY.get(raw, "Unknown")
    except Exception:
        return "Unknown"


@router.get("/compare", response_model=CompareResponse)
def compare_scans(
    a: str = Query(..., description="scan_id of scan A (newer)"),
    b: str = Query(..., description="scan_id of scan B (baseline)"),
    db: Session = Depends(get_db),
) -> CompareResponse:
    """GET /api/compare?a=X&b=Y — return a structured diff between two scan sessions.

    Phase 66 D-07: score delta, subscore deltas, added/removed findings,
    endpoint diff (only_in_a, only_in_b, changed_endpoints).

    Auth: inherited from router-level require_auth (do NOT add per-route — Pitfall 4).
    Error handling:
      - a == b  → HTTP 400 (Cannot compare a scan to itself.)
      - malformed scan_id → HTTP 400 (Invalid scan_id format.)
      - session not found  → HTTP 404
    """
    if a == b:
        raise HTTPException(status_code=400, detail=format_error("DASHBOARD-007"))
    try:
        ts_a = datetime.fromisoformat(a)
        ts_b = datetime.fromisoformat(b)
    except ValueError:
        raise HTTPException(status_code=400, detail=format_error("DASHBOARD-004"))

    eps_a = _fetch_session_endpoints_1s(db, ts_a)
    eps_b = _fetch_session_endpoints_1s(db, ts_b)
    if not eps_a:
        raise HTTPException(status_code=404, detail=format_error("DASHBOARD-005"))
    if not eps_b:
        raise HTTPException(status_code=404, detail=format_error("DASHBOARD-005"))

    # Scores + subscores (D-07)
    # compute_readiness_score returns subscores as a plain dict — use dict access
    evidence_a = build_evidence_summary(eps_a)
    evidence_b = build_evidence_summary(eps_b)
    sd_a = compute_readiness_score(evidence_a)
    sd_b = compute_readiness_score(evidence_b)
    score_a = int(sd_a["score"])
    score_b = int(sd_b["score"])
    sub_a = sd_a["subscores"]  # dict: {"hygiene": int, "modern_tls": int, ...}
    sub_b = sd_b["subscores"]

    subscore_deltas = SubscoreDelta(
        hygiene=int(sub_a.get("hygiene", 0)) - int(sub_b.get("hygiene", 0)),
        modern_tls=int(sub_a.get("modern_tls", 0)) - int(sub_b.get("modern_tls", 0)),
        identity_trust=int(sub_a.get("identity_trust", 0)) - int(sub_b.get("identity_trust", 0)),
        agility_signals=int(sub_a.get("agility_signals", 0)) - int(sub_b.get("agility_signals", 0)),
        data_at_rest=int(sub_a.get("data_at_rest", 0)) - int(sub_b.get("data_at_rest", 0)),
        data_in_motion=int(sub_a.get("data_in_motion", 0)) - int(sub_b.get("data_in_motion", 0)),
    )

    # Finding diff: (host, protocol, severity) composite key (D-07, Pattern 3)
    def _ep_key(ep: CryptoEndpoint) -> tuple[str, str, str] | None:
        if ep.scan_error or not ep.severity:
            return None
        return (ep.host or "", ep.protocol or "", ep.severity or "")

    def _key_to_finding(key: tuple[str, str, str]) -> CompareFinding:
        host, proto, sev = key
        return CompareFinding(host=host, protocol=proto or None, severity=sev)

    keys_a = {k for k in (_ep_key(ep) for ep in eps_a) if k is not None}
    keys_b = {k for k in (_ep_key(ep) for ep in eps_b) if k is not None}
    added_findings = [_key_to_finding(k) for k in sorted(keys_a - keys_b)]
    removed_findings = [_key_to_finding(k) for k in sorted(keys_b - keys_a)]

    # Endpoint diff: host sets + posture comparison
    hosts_a: dict[str, CryptoEndpoint] = {ep.host: ep for ep in eps_a if ep.host}
    hosts_b: dict[str, CryptoEndpoint] = {ep.host: ep for ep in eps_b if ep.host}
    only_in_a = sorted(set(hosts_a) - set(hosts_b))
    only_in_b = sorted(set(hosts_b) - set(hosts_a))
    common = sorted(set(hosts_a) & set(hosts_b))
    changed_endpoints: list[CompareEndpoint] = []
    for host in common:
        ea, eb = hosts_a[host], hosts_b[host]
        reasons = []
        if ea.tls_version != eb.tls_version:
            reasons.append("tls_version changed")
        if ea.cipher_suite != eb.cipher_suite:
            reasons.append("cipher_suite changed")
        if ea.cert_pubkey_alg != eb.cert_pubkey_alg:
            reasons.append("cert_pubkey_alg changed")
        if reasons:
            changed_endpoints.append(CompareEndpoint(host=host, reason="; ".join(reasons)))

    return CompareResponse(
        scan_a=CompareScanSummary(scan_id=a, scanned_at=ts_a, score=score_a),
        scan_b=CompareScanSummary(scan_id=b, scanned_at=ts_b, score=score_b),
        score_delta=score_a - score_b,
        subscore_deltas=subscore_deltas,
        added_findings=added_findings,
        removed_findings=removed_findings,
        endpoints_only_in_a=only_in_a,
        endpoints_only_in_b=only_in_b,
        changed_endpoints=changed_endpoints,
    )
