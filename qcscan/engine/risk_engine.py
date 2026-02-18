from typing import Dict, List
from qcscan.models import CryptoEndpoint

SEV_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


def evaluate_endpoints(cfg, endpoints: List[CryptoEndpoint]) -> List[Dict]:
    findings: List[Dict] = []

    for ep in endpoints:
        # Fingerprint-only endpoints can be "open" and not errors.
        if ep.scan_error:
            findings.append({
                "severity": "INFO",
                "title": "Scan error",
                "description": ep.scan_error,
                "recommendation": "Validate reachability or confirm service protocol.",
                "host": ep.host,
                "port": ep.port,
            })
            continue

        # HTTP plaintext discovery
        if ep.protocol == "HTTP":
            findings.append({
                "severity": "MEDIUM",
                "title": "Plaintext HTTP service detected",
                "description": f"HTTP service detected ({ep.tls_version or 'unknown status'}).",
                "recommendation": "Migrate management/application endpoints to HTTPS/TLS where feasible.",
                "host": ep.host,
                "port": ep.port,
            })

        # TLS analysis
        if ep.protocol == "TLS":
            if ep.cert_pubkey_alg in ("RSA", "ECDSA", "Ed25519", "Ed448"):
                findings.append({
                    "severity": "HIGH",
                    "title": "Quantum-transition required (public key crypto)",
                    "description": f"{ep.cert_pubkey_alg} detected in certificate.",
                    "recommendation": "Plan migration to PQC/hybrid as vendor support matures; prioritize long-lived sensitive data.",
                    "host": ep.host,
                    "port": ep.port,
                })

            if ep.tls_version in ("TLSv1", "TLSv1.1"):
                findings.append({
                    "severity": "CRITICAL",
                    "title": "Deprecated TLS version",
                    "description": f"{ep.tls_version} detected.",
                    "recommendation": "Upgrade to TLS 1.2+ (prefer TLS 1.3).",
                    "host": ep.host,
                    "port": ep.port,
                })
            elif ep.tls_version == "TLSv1.2":
                findings.append({
                    "severity": "LOW",
                    "title": "TLS 1.2 in use",
                    "description": "TLS 1.2 is acceptable but not the latest.",
                    "recommendation": "Adopt TLS 1.3 where feasible.",
                    "host": ep.host,
                    "port": ep.port,
                })

        # SSH analysis
        if ep.protocol == "SSH":
            findings.append({
                "severity": "HIGH",
                "title": "SSH cryptography requires quantum planning",
                "description": f"SSH banner: {ep.tls_version or 'unknown'}",
                "recommendation": "Inventory SSH host keys and KEX algorithms; evaluate lifecycle and PQC readiness.",
                "host": ep.host,
                "port": ep.port,
            })

        # Unknown open services
        if ep.protocol == "UNKNOWN":
            findings.append({
                "severity": "LOW",
                "title": "Unknown service detected",
                "description": ep.tls_version or "Open port, protocol not identified",
                "recommendation": "Fingerprint with a deeper probe or validate service ownership and purpose.",
                "host": ep.host,
                "port": ep.port,
            })

    findings.sort(key=lambda x: SEV_RANK.get(x["severity"], 0), reverse=True)
    return findings
