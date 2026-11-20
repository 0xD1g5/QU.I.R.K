"""SNMP vendor matrix staleness metadata — Phase 133 (SNMP-01/SNMP-05).

Mirrors quirk/scanner/hardware_meta.py staleness pattern.
STALENESS_THRESHOLD_DAYS is 90 (quarterly cadence) because vendor SNMP OID
assignments and PQC advisories are updated frequently.

See CLAUDE.md "Staleness Review Cadence" for the bump procedure.
"""
from __future__ import annotations

import datetime

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
            "pqc_status": "partial",
            "last_verified": "2026-09-02",
            "source_url": (
                "https://networkingdocs.hpe.com/documentation/us/en/software/junos/"
                "release-notes/25.4/junos-evo-release-notes-25.4r1/topics/"
                "new-features/feature-descriptions/Post-Quantum-Cryptography.html"
            ),
            "notes": (
                "Junos OS Evolved 25.4R1 introduces PQC on ACX, PTX and QFX "
                "Series: ML-DSA-87 software-image signatures and the hybrid "
                "sntrup761x25519-sha512 SSH key exchange. SCOPE CAVEAT: the "
                "cited release note covers ACX/PTX/QFX on Junos OS Evolved "
                "only; classic Junos OS (SRX, MX, EX) is not covered by it. "
                "source_url corrected 2026-11-19: the prior "
                "juniper.net/documentation/ index now forwards to a generic "
                "HPE Networking Documentation landing page that supports no "
                "claim; the 25.4R1 release note (read 2026-11-19) is the live "
                "replacement. notes corrected 2026-11-19: the prior 'JUNOS "
                "does not support PQC cipher suites as of 2026-Q2' is "
                "contradicted by that release note, matching hardware_meta "
                "(2026-09-13); pqc_status moved unsupported -> partial. The "
                "entry's last_verified is not bumped: the catalog-level "
                "re-verification is pending."
            ),
        },
        {
            "vendor": "Fortinet",
            "model_pattern": r"FortiGate|FortiOS|Fortinet",
            "pqc_status": "partial",
            "last_verified": "2026-09-02",
            "source_url": (
                "https://docs.fortinet.com/document/fortigate/8.0.0/"
                "administration-guide/527690/post-quantum-preshared-key-support"
            ),
            "notes": (
                "FortiOS supports post-quantum preshared keys (PPK, RFC 8784) "
                "for IPsec IKEv2, and FortiOS 7.6.1+ supports PQC KEM for "
                "IPsec key exchange (RFC 9370 / RFC 9242, ML-KEM per FIPS "
                "203). TLS and management-plane PQC are not addressed by that "
                "documentation. "
                "source_url corrected 2026-11-19: the prior "
                "support.fortinet.com/Information/ProductLifecycle.aspx now "
                "forwards to a JavaScript lifecycle application with no "
                "readable content; the FortiOS 8.0.0 PPK page (read "
                "2026-11-19) is the live replacement. notes corrected "
                "2026-11-19: the prior 'do not support PQC cipher suites' "
                "ignored IPsec PQC, matching hardware_meta (2026-09-13); "
                "pqc_status moved unsupported -> partial. The entry's "
                "last_verified is not bumped: the catalog-level "
                "re-verification is pending."
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
            "pqc_status": "unsupported",
            "last_verified": "2026-09-02",
            "source_url": (
                "https://docs.paloaltonetworks.com/network-security/decryption/"
                "administration/post-quantum-cryptography-decryption/"
                "detection-control-post-quantum-cryptography"
            ),
            "notes": (
                "In a decryption path a PAN-OS NGFW is a PQC downgrade point, "
                "not a PQC-capable device: under SSL Forward Proxy or SSL "
                "Inbound Inspection rules it removes PQC and hybrid PQC groups "
                "from the ClientHello and drops sessions that negotiate only "
                "PQC; traffic matching a no-decrypt rule, or no rule, may "
                "negotiate PQC end to end. "
                "source_url corrected 2026-11-19: the prior "
                "pan-os/11-1/.../post-quantum-cryptography deep link 404s; "
                "the live page is 'Post-Quantum Cryptography Detection and "
                "Control' (read 2026-11-19). notes corrected 2026-11-19: the "
                "prior claim that PAN-OS 11.1+ supports X25519MLKEM768 hybrid "
                "KEM for TLS decryption was inverted, matching the same "
                "correction in hardware_meta (2026-09-13); pqc_status moved "
                "partial -> unsupported. The entry's last_verified is not "
                "bumped: the catalog-level re-verification is pending."
            ),
        },
    ],
}


def is_snmp_vendor_matrix_stale(today: "datetime.date | None" = None) -> bool:
    """Return True when the matrix has not been re-verified within
    ``STALENESS_THRESHOLD_DAYS`` (90) days of ``today`` (default: ``date.today()``).

    Boundary: ``age > STALENESS_THRESHOLD_DAYS`` (strict greater-than), so
    exactly 90 days is NOT stale.  Reads the matrix at call time.
    """
    reference = today or datetime.date.today()
    last_verified = datetime.date.fromisoformat(SNMP_VENDOR_MATRIX["last_verified"])
    return (reference - last_verified).days > STALENESS_THRESHOLD_DAYS
