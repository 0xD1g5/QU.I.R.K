"""SNMP vendor matrix staleness metadata — Phase 133 (SNMP-01/SNMP-05).

Mirrors quirk/scanner/hardware_meta.py staleness pattern.
STALENESS_THRESHOLD_DAYS is 90 (quarterly cadence) because vendor SNMP OID
assignments and PQC advisories are updated frequently.

See CLAUDE.md "Staleness Review Cadence" for the bump procedure.
"""
from __future__ import annotations

# Per SNMP-05 — quarterly re-verification cadence matching hardware_meta.py.
# See CLAUDE.md "Staleness Review Cadence" for the bump procedure.
STALENESS_THRESHOLD_DAYS: int = 90

SNMP_VENDOR_MATRIX = {
    "last_verified": "2026-09-02",
    "source_url": "https://www.iana.org/assignments/enterprise-numbers/enterprise-numbers",
    "entries": [
        {
            "vendor": "Cisco",
            "model_pattern": r"Cisco|IOS Software|IOS XR|NX-OS",
            "pqc_status": "unsupported",
            "last_verified": "2026-09-02",
            "source_url": "https://sec.cloudapps.cisco.com/security/center/resources/pqc-readiness",
            "notes": (
                "Cisco IOS, IOS XR, and NX-OS do not support PQC cipher suites "
                "as of 2026-Q2. PQC is on Cisco roadmap for future FTD releases."
            ),
        },
        {
            "vendor": "Juniper",
            "model_pattern": r"JUNOS|Juniper Networks|Juniper.*SRX|Juniper.*EX|Juniper.*QFX",
            "pqc_status": "unsupported",
            "last_verified": "2026-09-02",
            "source_url": "https://www.juniper.net/documentation/",
            "notes": (
                "Juniper Networks JUNOS does not support PQC cipher suites "
                "as of 2026-Q2. Consult Juniper roadmap for future PQC support."
            ),
        },
        {
            "vendor": "Fortinet",
            "model_pattern": r"FortiGate|FortiOS|Fortinet",
            "pqc_status": "unsupported",
            "last_verified": "2026-09-02",
            "source_url": "https://support.fortinet.com/Information/ProductLifecycle.aspx",
            "notes": (
                "FortiGate and FortiOS do not support PQC cipher suites "
                "as of 2026-Q2. Verify against FortiOS 7.x release notes. "
                "source_url corrected 2026-09-02: the prior "
                "fortinet.com/support/product-lifecycle URL now 404s; "
                "support.fortinet.com/Information/ProductLifecycle.aspx is "
                "the live replacement."
            ),
        },
        {
            "vendor": "Linux",
            "model_pattern": r"Linux.*\d+\.\d+|GNU/Linux",
            "pqc_status": "partial",
            "last_verified": "2026-09-02",
            "source_url": "https://github.com/open-quantum-safe/oqs-provider",
            "notes": (
                "Linux hosts with OpenSSL 3.x + OQS provider can support PQC "
                "cipher suites. Kernel version alone is not sufficient; "
                "library-level support must be verified separately. "
                "source_url corrected 2026-09-02: the prior openssl.org "
                "GitHub Pages doc now 404s; the oqs-provider project's own "
                "GitHub repo is the live replacement."
            ),
        },
        {
            "vendor": "Palo Alto",
            "model_pattern": r"PAN-OS|Palo Alto",
            "pqc_status": "partial",
            "last_verified": "2026-09-02",
            "source_url": (
                "https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-admin/"
                "decryption/post-quantum-cryptography"
            ),
            "notes": (
                "PAN-OS 11.1+ supports X25519MLKEM768 hybrid KEM for TLS "
                "decryption; management plane and older releases remain "
                "unsupported. KNOWN ISSUE (2026-09-02): this deep link now "
                "404s; docs.paloaltonetworks.com's own site index confirms "
                "the content was reorganized into a dedicated 'Quantum "
                "Security Administration' book, but the exact new URL could "
                "not be resolved during this sweep. pqc_status corroborated "
                "via that site-index evidence, not a live page fetch — "
                "flagged for a follow-up doc-link fix."
            ),
        },
    ],
}
