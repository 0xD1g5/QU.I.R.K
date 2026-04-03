from __future__ import annotations

from typing import Dict, List


def recommend_migration_paths(findings: List[Dict]) -> List[Dict]:
    """
    Convert raw findings into recommended migration paths.
    This is a rules-based v3.5 layer; later becomes richer with
    cipher enumeration, chain analysis, cloud/PKI connectors.
    """
    recs: List[Dict] = []

    for f in findings:
        title = (f.get("title") or "").lower()
        sev = f.get("severity")
        host = f.get("host")
        port = f.get("port")

        if sev == "INFO":
            continue

        # Legacy TLS
        if "legacy tls" in title:
            recs.append({
                "host": host,
                "port": port,
                "severity": sev,
                "path": "Hygiene → Modernization",
                "recommendation": "Upgrade to TLS 1.2+ immediately; prefer TLS 1.3. Standardize termination configs and block legacy versions at gateways/LBs.",
            })
            continue

        # Plaintext HTTP
        if "plaintext http" in title:
            recs.append({
                "host": host,
                "port": port,
                "severity": sev,
                "path": "Hygiene",
                "recommendation": "Migrate HTTP→HTTPS. If legacy, front with TLS-terminating reverse proxy and enforce redirects + HSTS where applicable.",
            })
            continue

        # Quantum transition
        if "quantum" in title:
            recs.append({
                "host": host,
                "port": port,
                "severity": sev,
                "path": "Modernization → PQC Preparation",
                "recommendation": "Stabilize on modern classical crypto baselines (TLS 1.3, standardized configs) and prepare for hybrid/PQC vendor upgrades. Prioritize long-lived sensitive data flows and trust anchors.",
            })
            continue

        # SSH planning
        if "ssh" in title:
            recs.append({
                "host": host,
                "port": port,
                "severity": sev,
                "path": "Modernization → PQC Preparation",
                "recommendation": "Inventory SSH host keys/KEX algorithms, rotate off legacy RSA where feasible, and plan for vendor support of hybrid/PQC approaches as they mature.",
            })
            continue

        # Default
        recs.append({
            "host": host,
            "port": port,
            "severity": sev,
            "path": "Modernization",
            "recommendation": f.get("recommendation") or "Standardize crypto baselines and plan phased upgrades.",
        })

    return recs

