from __future__ import annotations

import re
from typing import Dict, Final, FrozenSet, List


# Phase 74-03 D-08 (WR-09): canonical algorithm synonym map + word-boundary
# matcher. Replaces substring matching that produced false positives like
# `'DES' in 'DESede'` and `'DES' in 'libdes3.so'`. Word-boundaries (`\b`)
# eliminate the substring-inside-identifier class. Also consumed by
# `quirk/qramm/evidence_bridge.py::_walk_json_for_alg_strings` (D-09).
CANONICAL_ALG_SYNONYMS: Final[Dict[str, FrozenSet[str]]] = {
    "DES":  frozenset({"DES", "DES-EDE", "DES-CBC"}),
    "3DES": frozenset({"3DES", "TripleDES", "DES-EDE3"}),
    "RC4":  frozenset({"RC4", "ARCFOUR"}),
    "MD5":  frozenset({"MD5"}),
    "SHA1": frozenset({"SHA1", "SHA-1"}),
}


def _matches(canonical: str, text: str) -> bool:
    """Word-boundary regex match for ``canonical`` (or any of its synonyms) in ``text``.

    Case-insensitive. Returns False when the canonical token appears only as a
    substring inside a larger identifier (e.g. ``DESede``, ``libdes3.so``).
    """
    variants = CANONICAL_ALG_SYNONYMS.get(canonical, frozenset({canonical}))
    pattern = r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


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

        # Legacy TLS — Phase 74 D-08: word-boundary match on title token
        if re.search(r"\blegacy tls\b", title):
            recs.append({
                "host": host,
                "port": port,
                "severity": sev,
                "path": "Hygiene → Modernization",
                "recommendation": "Upgrade to TLS 1.2+ immediately; prefer TLS 1.3. Standardize termination configs and block legacy versions at gateways/LBs.",
            })
            continue

        # Plaintext HTTP — Phase 74 D-08: word-boundary
        if re.search(r"\bplaintext http\b", title):
            recs.append({
                "host": host,
                "port": port,
                "severity": sev,
                "path": "Hygiene",
                "recommendation": "Migrate HTTP→HTTPS. If legacy, front with TLS-terminating reverse proxy and enforce redirects + HSTS where applicable.",
            })
            continue

        # Quantum transition — Phase 74 D-08: word-boundary
        if re.search(r"\bquantum\b", title):
            recs.append({
                "host": host,
                "port": port,
                "severity": sev,
                "path": "Modernization → PQC Preparation",
                "recommendation": "Stabilize on modern classical crypto baselines (TLS 1.3, standardized configs) and prepare for hybrid/PQC vendor upgrades. Prioritize long-lived sensitive data flows and trust anchors.",
            })
            continue

        # SSH planning — Phase 74 D-08: word-boundary closes `sshfp` false positive
        if re.search(r"\bssh\b", title):
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
