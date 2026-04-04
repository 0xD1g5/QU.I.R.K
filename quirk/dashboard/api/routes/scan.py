"""GET /api/scan/latest — returns the most recent scan session's full results."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import (
    CbomComponent,
    CertItem,
    ConfidenceData,
    FindingItem,
    RoadmapData,
    RoadmapEdge,
    RoadmapNode,
    ScanLatestResponse,
    ScanMeta,
    ScoreData,
    SubScores,
)
from quirk.models import CryptoEndpoint

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


@router.get("/scan/latest", response_model=ScanLatestResponse)
def get_latest_scan(db: Session = Depends(get_db)) -> ScanLatestResponse:
    """GET /api/scan/latest — returns the most recent scan session's full results.

    scan_id is derived from MAX(scanned_at) — no separate session table needed.
    The response is shaped for future multi-scan navigation: scan_id field present,
    future endpoint can accept ?scan_id= param without breaking this response shape.
    """
    # Find the most recent scan timestamp
    latest_ts = db.query(func.max(CryptoEndpoint.scanned_at)).scalar()
    if latest_ts is None:
        raise HTTPException(
            status_code=404,
            detail="No scan results found. Run your first scan: quirk --config config.yaml",
        )

    # Load all endpoints from that scan session
    endpoints: list[CryptoEndpoint] = (
        db.query(CryptoEndpoint)
        .filter(CryptoEndpoint.scanned_at == latest_ts)
        .all()
    )

    if not endpoints:
        raise HTTPException(status_code=404, detail="No endpoints found for latest scan.")

    # Derive findings first — needed by evidence summary
    findings = _derive_findings(endpoints)

    # Build evidence summary for intelligence functions
    try:
        from quirk.intelligence.evidence import build_evidence_summary
        evidence = build_evidence_summary(endpoints, [f.model_dump() for f in findings])
    except Exception:
        evidence = {}

    # Compute score and confidence
    try:
        from quirk.intelligence.scoring import compute_readiness_score
        score_raw = compute_readiness_score(evidence)
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
    certificates.sort(key=lambda c: c.cert_not_after or datetime.max.replace(tzinfo=timezone.utc))

    cbom_components = _derive_cbom(endpoints)
    roadmap = _derive_roadmap(evidence, score_raw)

    scan_id = latest_ts.isoformat() if hasattr(latest_ts, "isoformat") else str(latest_ts)

    return ScanLatestResponse(
        meta=ScanMeta(
            scan_id=scan_id,
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
