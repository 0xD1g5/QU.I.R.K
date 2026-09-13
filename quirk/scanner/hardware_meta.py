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
    # NOTE: this top-level date is COMPUTED — it is min() of the entries'
    # last_verified dates, never bumped in its own right, so the staleness gate
    # cannot read greener than the weakest vendor (Phase 203 D-01). The
    # invariant is enforced by
    # tests/test_hardware_staleness.py::test_hardware_matrix_top_level_is_min_of_entries.
    #
    # 2026-09-13: recomputed to min() of the entries after the last outstanding
    # vendor (IPMI) was verified against the specification itself. All 8 entries
    # now carry 2026-09-13, so min() is 2026-09-13 and the staleness gate goes
    # green on its own merits — no date was bumped and
    # QUIRK_CI_STALENESS_OVERRIDE_DATE was never set. The Phase 203 deferral
    # recorded in .planning/STATE.md is hereby discharged.
    "last_verified": "2026-09-13",
    # source_url corrected 2026-09-13: the prior
    # https://www.nsa.gov/Cybersecurity/CNSA-2-0/ redirects to the generic
    # /Cybersecurity/ index (verified in a real browser — the long-documented
    # HTTP 403 to non-browser agents was bot-blocking only, and Chrome did get
    # through). This is the live post-quantum landing page.
    "source_url": "https://www.nsa.gov/Cybersecurity/Post-Quantum-Cryptography/",
    "entries": [
        {
            "vendor": "F5",
            "model_pattern": r"BIG-IP",
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-09-13",
            "source_url": "https://my.f5.com/manage/s/article/K000136126",
            "notes": "BIG-IP TMOS supports hybrid ML-KEM key agreement for TLS 1.3: X25519MLKEM768 on both client-side and server-side TLS from 17.5.1 (client-side X25519Kyber768Draft00 from 17.5.0); SecP256r1MLKEM768 and SecP384r1MLKEM1024 on both sides from 21.1.0. NOT enabled by default \u2014 the default DH-group list is P256:X25519:P384:FFDHE2048/3072/4096, so a BIG-IP only negotiates PQC when an operator builds an explicit cipher rule. No PQC signature algorithms (no ML-DSA, no SLH-DSA) in the supported signature-algorithm set, which is why this stays partial. source_url corrected 2026-09-13: the prior support.f5.com/csp/article/K000141701 now 301s to my.f5.com and 404s \u2014 the K-number did not survive article retirement. K000136126 (SSL ciphers supported on BIG-IP platforms 16.1.x-21.x) is the authoritative support matrix; see also K000149577 'Enable post-quantum cryptography in F5 BIG-IP TMOS' for the configuration procedure. notes corrected 2026-09-13: the prior claim 'core TMOS does not support PQC cipher suites' was FALSE and had been false since F5 published K000149577 in Feb 2025 \u2014 sixteen months before the prior last_verified date. The prior SPK-only assertion is unsupported by either article.",
        },
        {
            "vendor": "Cisco",
            "model_pattern": r"Cisco|ASA|FTD|Firepower",
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-09-13",
            "source_url": "https://www.cisco.com/c/en/us/td/docs/security/asa/roadmap/asa_new_features.html",
            "notes": "Cisco Secure Firewall ASA supports Multiple Key Exchanges for IKEv2 from ASA 9.20(1) (the RFC 9370 mechanism, configured via 'additional-key-exchange'), which Cisco documents as securing IPsec communication against quantum computers. TLS-plane PQC is NOT addressed by that document and is not claimed here. UNVERIFIED: whether an ML-KEM group is among the offered additional key-exchange methods \u2014 RFC 9370 is the framework for carrying extra KE payloads, not a guarantee of ML-KEM; confirm against the ASA IKEv2 configuration guide before naming an algorithm. source_url corrected 2026-09-13: the prior sec.cloudapps.cisco.com/security/center/resources/pqc-readiness returns HTTP 200 with the body text 'No Data Found For This Page.'; the Cisco Trust Center PQC page is a corporate landing page with no ASA/FTD statement, and the Next Generation Cryptography page mentions ASA only in IPsec transform-set examples. The ASA New Features by Release roadmap doc is the live replacement. notes corrected 2026-09-13: the prior 'ASA and FTD do not support PQC cipher suites' was false for IPsec as of 9.20(1). The prior roadmap clause was DROPPED, not re-sourced \u2014 the only public statement of FTD 10.5 / ASA 9.25 ML-KEM timing is a Cisco blog post, and a roadmap is a promise rather than a capability. SSH-2.0-Cisco-* banner detected via ssh_banner path.",
        },
        {
            "vendor": "Palo Alto",
            "model_pattern": r"PAN-OS|Palo Alto",
            "pqc_status": "unsupported",
            "eol_date": None,
            "last_verified": "2026-09-13",
            "source_url": "https://docs.paloaltonetworks.com/network-security/decryption/administration/post-quantum-cryptography-decryption/detection-control-post-quantum-cryptography",
            "notes": "In a decryption path a PAN-OS NGFW is a PQC DOWNGRADE POINT, not a PQC-capable device. Palo Alto states plainly that traffic encrypted with PQC or hybrid PQC algorithms cannot be decrypted; when SSL Forward Proxy or SSL Inbound Inspection decryption rules apply, the NGFW REMOVES PQC and hybrid PQC groups from the ClientHello supported_groups extension, forcing the client to renegotiate with classical algorithms, and DROPS the session outright if the client will only negotiate PQC. Traffic matching a 'no-decrypt' rule, or no rule, is allowed to negotiate PQC end-to-end (the firewall is passing it through, not supporting it). Operational signals: 'show counter global name ssl_pqc_session_cnt' increments on each PQC negotiation attempt, and decryption logs record the negotiated EC curve for no-decrypt sessions. UNVERIFIED: management-plane TLS PQC is reported to have shipped Aug 2025, and IPsec/VPN hybrid key exchange Mid-2024 \u2014 neither was confirmed in this pass, and neither is claimed here. source_url corrected 2026-09-13: the prior pan-os/11-1/.../post-quantum-cryptography 404s, as does the restructured network-security path for that slug; the live page is 'Post-Quantum Cryptography Detection and Control', recorded above in its VERSION-FREE form (the vendor maintains this topic page in place rather than forking it per release). notes corrected 2026-09-13: the prior claim that PAN-OS 11.1+ supports X25519MLKEM768 for TLS decryption was INVERTED \u2014 the NGFW strips that exact class of group rather than negotiating it.",
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
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-09-13",
            "source_url": "https://www.juniper.net/documentation/us/en/software/junos/release-notes/25.4/junos-evo-release-notes-25.4r1/topics/new-features/feature-descriptions/Post-Quantum-Cryptography.html",
            "notes": "Junos OS Evolved 25.4R1 introduces PQC on ACX, PTX and QFX Series: ML-DSA-87 with SHA-512 for software-image signatures with off-box verification (CNSA 2.0-aligned), and the hybrid sntrup761x25519-sha512 SSH key exchange (Streamlined NTRU Prime 761 + X25519), configured at [edit system services ssh key-exchange]. Note sntrup761x25519 is Shor-resistant but NOT a NIST selection \u2014 it is neither FIPS 203 nor CNSA 2.0, unlike the ML-DSA-87 image signing. Juniper's 'Quantum Buffer' for JSSH is NOT post-quantum: it refreshes finite-field Diffie-Hellman moduli for group-exchange-sha1/sha2 and is described by the vendor as a phased approach toward PQC. SCOPE CAVEAT: this catalog entry's model_pattern targets JUNOS/SRX/MX, and the cited evidence covers ACX/PTX/QFX on Junos OS Evolved only \u2014 classic Junos OS on SRX and MX is NOT covered by this document. source_url corrected 2026-09-13: the prior supportportal.juniper.net article requires a support login ('You do not have the required access privileges'); this replacement is on the public juniper.net/documentation tree, so the entry is no longer access-gated. notes corrected 2026-09-13: the prior 'Junos OS does not support PQC algorithms as of 2026-Q2; roadmap items pending' was falsified by a shipped-feature release note dated 17-Dec-25. Detected via JUNOS string in SSH banner or management HTTP title.",
        },
        {
            "vendor": "HPE",
            "model_pattern": r"iLO\s*[3-7]|Integrated Lights-Out",
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-09-13",
            "source_url": "https://www.hpe.com/us/en/collaterals/collateral.c04154343.html",
            "notes": "PQC on HPE iLO appears at iLO 7, as a CNSA 2.0-aligned NIST-approved LMS algorithm ensuring PQC-ready FIRMWARE UPDATES \u2014 i.e. hash-based signing of update images, NOT a hybrid TLS key exchange. No iLO generation is documented in the QuickSpecs as negotiating PQC or hybrid PQC for TLS transport. iLO 6 carries FIPS 140-2/140-3 validation and DMTF SPDM but no PQC. source_url corrected 2026-09-13: the prior hpe.com/h20195/v2/GetPDF.aspx/a00128516en_us.pdf times out (60s, zero bytes, no extractable text in a real browser); doc c04154343 (HPE Integrated Lights-Out QuickSpecs, covering iLO 4/5/6/7) is the live replacement. notes corrected 2026-09-13: the prior claim was wrong on three counts \u2014 wrong generation (iLO 7, not iLO 6), wrong mechanism (LMS firmware-update signing, not hybrid TLS), and a 'firmware 1.60+' version floor with no support in any located source. Detected via Server header 'iLO/' or X-Device-Model header.",
        },
        {
            "vendor": "IPMI",
            "model_pattern": r"IPMI|ipmi",
            "pqc_status": "unsupported",
            "eol_date": None,
            "last_verified": "2026-09-13",
            "source_url": "https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf",
            "notes": "IPMI 2.0 session security (RMCP+/RAKP) negotiates from an enumerated algorithm table carrying no PQC option, and the specification is terminal at v2.0 rev 1.1 (1 October 2013, Intel/Hewlett-Packard/NEC/Dell). Verified 2026-09-13 by reading the specification itself: Table 13-17 Authentication Algorithm Numbers enumerates 00h RAKP-none, 01h RAKP-HMAC-SHA1, 02h RAKP-HMAC-MD5, 03h RAKP-HMAC-SHA256; Tables 13-18/13-19 likewise enumerate the integrity and confidentiality algorithms (HMAC-SHA1-96, HMAC-SHA256-128, AES-CBC-128, xRC4). Every standard algorithm is classical; none is quantum-resistant, and a dead specification cannot add one. NOT REMEDIABLE IN PLACE: migrate to Redfish (HTTPS/TLS, which inherits PQC from the TLS stack rather than defining its own) or disable IPMI-over-LAN. CORRECTION 2026-09-13, the prior claim was WRONG: it asserted a CLOSED cipher-suite table 'with no algorithm-negotiation extension point'. An extension point DOES exist \u2014 all three algorithm tables reserve C0h-FFh for OEM use, and the Cipher Suite record format defines an OEM variant (C1h Start-Of-Record carrying an OEM Cipher Suite ID plus the OEM's IANA enterprise number) alongside the standard C0h form. pqc_status nevertheless remains unsupported, on a narrower and better-supported basis: the OEM range is vendor-proprietary rather than an algorithm-agility mechanism, and as printed it is not usably specified \u2014 the algorithm-number field is six bits ([5:0], and Table 13-17's own footnote states 'The number range is limited to six (6) bits (00h-3Fh)'), while C0h is 1100_0000b = 192 and therefore cannot be represented in that field at all. The specification contradicts itself on this point; treat any OEM PQC cipher suite as a per-vendor claim requiring its own evidence, not as something IPMI 2.0 provides. pqc_status was first moved from VENDOR-SILENT to unsupported on 2026-09-13 as a fail-safe before this verification: VENDOR-SILENT plus high confidence resolves to Tier 3 in hardware_tier.assign_tier \u2014 the same remediation tier as a fully PQC-capable device \u2014 so a banner reading 'IPMI 2.0' scored LOWER urgency than a bare 'IPMI' banner. That change is now an attestation rather than a precaution. A prior claim that individual BMC vendors have made no public PQC statements \u2014 a negative-existence claim across an open set of vendors that no single document can ever support \u2014 was removed rather than re-sourced, and is deliberately NOT reinstated: this row attests to the protocol only. source_url corrected 2026-09-13: the prior products/docs/servers/ipmi/...html page returns HTTP 200 but silently redirects to a generic Intel Server Products selector on the wrong subject, and the ipmi-technical-resources.html index likewise redirects to a generic products overview \u2014 Intel has retired the IPMI doc tree. The recorded PDF resolves directly (HTTP 200, application/pdf, 644 pages, no redirect) and is the specification itself rather than a page describing it. NOTE this row is keyed on a PROTOCOL, not a vendor: it is the only such entry of the eight, and Intel is a specification co-author rather than the subject.",
        },
        {
            "vendor": "Thales",
            "model_pattern": r"Luna|SafeNet",
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": "2026-09-13",
            "source_url": "https://thalesdocs.com/gphsm/luna/7/docs/network/Content/sdk/extensions/pqc/post_quantum_algorithms.htm",
            "notes": "Luna HSM firmware 7.9.0+ provides ML-KEM and ML-DSA, FIPS-compliant per NIST CAVP; keys are cloneable, backup/restorable and HA-replicable. ML-KEM is session-key only (no persistent key generation); ML-DSA supports persistent keys \u2014 which is why this stays partial. LMS-HSS arrived earlier, at firmware 7.8.9+, but is not cloneable, so no backup and no HA replication. Firmware 7.9.1 adds private-key wrapping/unwrapping for ML-KEM and ML-DSA plus PQC key attestation (both require Luna HSM Client 10.9.1+); PQC generally requires Luna Client 10.9.0+. source_url corrected 2026-09-13: the prior .../admin_partition/pqc.htm returns AccessDenied in a real browser (S3-backed docs host, not bot-blocking); the replacement is the vendor's Post Quantum Algorithms topic page, recorded in its VERSION-FREE form deliberately \u2014 firmware-numbered CRN paths are exactly what rotted here. notes corrected 2026-09-13: the prior '7.7.1+' floor was WRONG \u2014 the 7.7.1 customer release note contains no mention of ML-KEM, ML-DSA, PQC or post-quantum at all, and the real floor is 7.9.0. The prior claim also omitted the LMS-HSS family entirely. Luna 6 remains out of scope of this document.",
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
