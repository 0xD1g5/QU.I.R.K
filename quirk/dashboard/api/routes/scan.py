"""GET /api/scan/latest — returns the most recent scan session's full results."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import (
    CbomComponent,
    CertItem,
    ConfidenceData,
    FindingItem,
    IdentityFinding,
    MotionFinding,
    RoadmapData,
    RoadmapEdge,
    RoadmapNode,
    ScanLatestResponse,
    ScanMeta,
    ScanSession,
    ScoreData,
    SubScores,
)
from quirk.models import CryptoEndpoint
from quirk.scanner.saml_scanner import OIDC_ALG_SEVERITY

router = APIRouter()

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
        elif starttls_warning:
            severity = "MEDIUM"
            title = "SMTP STARTTLS susceptible to stripping (port 25)"
            quantum_risk = "depends on negotiated cipher"
        elif proto in BROKER_TLS and tls_version in LEGACY_TLS:
            severity = "HIGH"
            title = f"{proto} legacy TLS version ({tls_version})"
            quantum_risk = "quantum-vulnerable"
        else:
            severity = "LOW"
            title = f"{proto} TLS endpoint"
            quantum_risk = "quantum-vulnerable" if cipher_suite and "RSA" in cipher_suite else "quantum-unknown"

        results.append(MotionFinding(
            host=getattr(ep, "host", "") or "",
            port=port,
            severity=severity,
            title=title,
            protocol=proto,            # verbatim — preserve "AMQPS/Azure-ServiceBus"
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


@router.get("/scans", response_model=List[ScanSession])
def list_scans(db: Session = Depends(get_db)) -> List[ScanSession]:
    """GET /api/scans — returns the last 10 distinct scan sessions, newest first.

    Groups by second-truncated timestamp because each CryptoEndpoint row is
    written with its own microsecond-precision scanned_at. Grouping by the raw
    value produces one row per endpoint rather than one per scan session.
    """
    ts_sec = func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at).label("ts_sec")
    rows = (
        db.query(ts_sec, func.count(CryptoEndpoint.id).label("cnt"))
        .group_by("ts_sec")
        .order_by(ts_sec.desc())
        .limit(10)
        .all()
    )
    return [
        ScanSession(
            scan_id=ts_str,
            scanned_at=datetime.fromisoformat(ts_str),
            total_endpoints=cnt,
        )
        for ts_str, cnt in rows
    ]


def _cert_expiry_key(c: "CertItem") -> datetime:
    """Return a timezone-aware datetime for sorting; normalises naive datetimes to UTC."""
    dt = c.cert_not_after
    if dt is None:
        return datetime.max.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


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
            raise HTTPException(status_code=400, detail=f"Invalid scan_id format: {scan_id!r}")
        endpoints: list[CryptoEndpoint] = (
            db.query(CryptoEndpoint)
            .filter(
                CryptoEndpoint.scanned_at >= target_ts,
                CryptoEndpoint.scanned_at < target_ts + timedelta(seconds=1),
            )
            .all()
        )
        if not endpoints:
            raise HTTPException(status_code=404, detail=f"No scan found with scan_id={scan_id!r}")
        latest_ts = target_ts
    else:
        # Derive the latest scan second from MAX, then load all endpoints in that second.
        # Cannot use MAX + exact equality because each endpoint row gets its own
        # microsecond-precision scanned_at; a range window captures the full session.
        latest_ts_str = db.query(
            func.strftime("%Y-%m-%d %H:%M:%S", func.max(CryptoEndpoint.scanned_at))
        ).scalar()
        if latest_ts_str is None:
            raise HTTPException(
                status_code=404,
                detail="No scan results found. Run your first scan: quirk --config config.yaml",
            )
        latest_ts = datetime.fromisoformat(latest_ts_str)
        endpoints: list[CryptoEndpoint] = (
            db.query(CryptoEndpoint)
            .filter(
                CryptoEndpoint.scanned_at >= latest_ts,
                CryptoEndpoint.scanned_at < latest_ts + timedelta(seconds=1),
            )
            .all()
        )

    if not endpoints:
        raise HTTPException(status_code=404, detail="No endpoints found for latest scan.")

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
