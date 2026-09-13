"""Hardware compatibility matrix staleness metadata — Phase 127 (HWCOMPAT-02/06).

Mirrors quirk/qramm/model_meta.py staleness pattern.
STALENESS_THRESHOLD_DAYS is 90 (quarterly cadence) because PQC vendor advisories
are updated frequently and the matrix should be re-verified quarterly.

See CLAUDE.md "Staleness Review Cadence" for the bump procedure.
"""
from __future__ import annotations

import datetime

# Per HWCOMPAT-06 — quarterly re-verification cadence for an active PQC advisory catalog.
# See CLAUDE.md "Staleness Review Cadence" for the bump procedure.
STALENESS_THRESHOLD_DAYS: int = 90

HARDWARE_MATRIX = {
    "last_verified": "2026-06-13",
    "source_url": "https://www.nsa.gov/Cybersecurity/CNSA-2-0/",
    "entries": [
        {
            "vendor": "F5",
            "model_pattern": r"BIG-IP",
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-06-13",
            "source_url": "https://support.f5.com/csp/article/K000141701",
            "notes": "PQC support via SPK (Service Proxy for Kubernetes) module only; core TMOS does not support PQC cipher suites as of 2026-Q2.",
        },
        {
            "vendor": "Cisco",
            "model_pattern": r"Cisco|ASA|FTD|Firepower",
            "pqc_status": "unsupported",
            "eol_date": None,
            "last_verified": "2026-06-13",
            "source_url": "https://sec.cloudapps.cisco.com/security/center/resources/pqc-readiness",
            "notes": "ASA and FTD do not support PQC cipher suites; Cisco roadmap lists PQC for future FTD releases. SSH-2.0-Cisco-* banner detected via ssh_banner path.",
        },
        {
            "vendor": "Palo Alto",
            "model_pattern": r"PAN-OS|Palo Alto",
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-06-13",
            "source_url": "https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-admin/decryption/post-quantum-cryptography",
            "notes": "PAN-OS 11.1+ supports X25519MLKEM768 hybrid KEM for TLS decryption; management plane and older releases remain unsupported.",
        },
        {
            "vendor": "Fortinet",
            "model_pattern": r"FortiGate|FortiOS",
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-09-13",
            "source_url": "https://docs.fortinet.com/document/fortigate/8.0.0/administration-guide/527690/post-quantum-preshared-key-support",
            "notes": "FortiOS supports post-quantum preshared keys (PPK, RFC 8784) for IPsec IKEv2 from 6.0+ without EAP; PPK with IKEv2 EAP requires 8.0.0+ (silently not applied on earlier releases even with 'ppk require'). FortiOS 7.6.1+ additionally supports PQC KEM for IPsec key exchange (RFC 9370 / RFC 9242, ML-KEM per NIST FIPS 203) — a separate, parallel mechanism to PPK. TLS/management-plane PQC not addressed by the vendor IPsec documentation. HTTP mgmt via /api/v2/cmdb/system/status. source_url corrected 2026-09-13: the prior 7.6.0/761917 URL silently redirects to the guide's 'Getting started' page with HTTP 200 rather than 404ing; 8.0.0/527690 is the live replacement. notes corrected 2026-09-13: the prior '7.4+ PQPPK' version floor was wrong (vendor states 6.0+), and PQC KEM support was absent entirely.",
        },
        {
            "vendor": "Juniper",
            "model_pattern": r"JUNOS|SRX|MX\b",
            "pqc_status": "unsupported",
            "eol_date": None,
            "last_verified": "2026-06-13",
            "source_url": "https://supportportal.juniper.net/s/article/Junos-Post-Quantum-Cryptography-Status",
            "notes": "Junos OS does not support PQC algorithms as of 2026-Q2; roadmap items pending. Detected via JUNOS string in SSH banner or management HTTP title.",
        },
        {
            "vendor": "HPE",
            "model_pattern": r"iLO\s*[3-7]|Integrated Lights-Out",
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-06-13",
            "source_url": "https://www.hpe.com/h20195/v2/GetPDF.aspx/a00128516en_us.pdf",
            "notes": "iLO 6 (Gen11 servers) supports PQC hybrid TLS via firmware 1.60+; iLO 3/4/5 do not. Detected via Server header 'iLO/' or X-Device-Model header.",
        },
        {
            "vendor": "IPMI",
            "model_pattern": r"IPMI|ipmi",
            "pqc_status": "VENDOR-SILENT",
            "eol_date": None,
            "last_verified": "2026-06-13",
            "source_url": "https://www.intel.com/content/www/us/en/products/docs/servers/ipmi/ipmi-second-gen-interface-spec-v2-rev1-1.html",
            "notes": "IPMI 2.0 specification predates PQC; individual BMC vendors have made no public PQC statements. VENDOR-SILENT assigned — no advisory found.",
        },
        {
            "vendor": "Thales",
            "model_pattern": r"Luna|SafeNet",
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-06-13",
            "source_url": "https://thalesdocs.com/gphsm/luna/7/docs/network/Content/admin_partition/pqc.htm",
            "notes": "Thales Luna Network HSM 7 firmware 7.7.1+ supports PQC key generation (ML-KEM, ML-DSA) via PKCS#11 extension; older firmware and Luna 6 are VENDOR-SILENT.",
        },
    ],
}


def is_hardware_matrix_stale(today: datetime.date | None = None) -> bool:
    """Returns True when the hardware matrix has not been re-verified within
    ``STALENESS_THRESHOLD_DAYS`` (90) days of ``today`` (default: ``date.today()``).

    Boundary: ``age > STALENESS_THRESHOLD_DAYS`` (strict greater-than), so
    exactly 90 days is NOT stale.

    Mirrors is_qramm_model_stale() math from quirk/qramm/model_meta.py.
    Phase 127 HWCOMPAT-06 — 90-day CI staleness gate.
    """
    reference = today or datetime.date.today()
    last_verified = datetime.date.fromisoformat(HARDWARE_MATRIX["last_verified"])
    age = (reference - last_verified).days
    return age > STALENESS_THRESHOLD_DAYS
