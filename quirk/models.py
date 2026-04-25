from __future__ import annotations

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text

Base = declarative_base()


class CryptoEndpoint(Base):
    __tablename__ = "crypto_endpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)

    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)

    protocol = Column(String(32), nullable=True)
    scanned_at = Column(DateTime, nullable=True)

    # Existing fields (kept compatible with your v3.x)
    sni_used = Column(Boolean, default=False)

    tls_version = Column(String(64), nullable=True)
    cipher_suite = Column(String(255), nullable=True)

    cert_subject = Column(Text, nullable=True)
    cert_issuer = Column(Text, nullable=True)
    cert_sans = Column(Text, nullable=True)
    cert_sig_alg = Column(String(128), nullable=True)
    cert_pubkey_alg = Column(String(64), nullable=True)
    cert_pubkey_size = Column(Integer, nullable=True)
    cert_not_before = Column(DateTime, nullable=True)
    cert_not_after = Column(DateTime, nullable=True)

    scan_error = Column(Text, nullable=True)
    tls_blocker_reason = Column(String(64), nullable=True)
    service_detail = Column(Text, nullable=True)

    # ==========================
    # v3.6 TLS capability fields
    # ==========================
    tls_supported_versions = Column(Text, nullable=True)        # e.g. "TLSv1,TLSv1.2,TLSv1.3"
    tls_supported_ciphers_sample = Column(Text, nullable=True)  # pipe or comma delimited
    tls_weak_ciphers_present = Column(Boolean, default=False)
    tls_legacy_suites_present = Column(Boolean, default=False)
    tls_pfs_supported = Column(Boolean, default=False)
    tls_enum_mode = Column(String(16), nullable=True)           # "fast" or "deep"
    tls_enum_notes = Column(Text, nullable=True)
    tls_capabilities_json = Column(Text, nullable=True)  # sslyze deep scan results (JSON)

    # ==========================
    # v4.0 SSH audit fields
    # ==========================
    ssh_audit_json = Column(Text, nullable=True)  # Full ssh-audit JSON output

    # ==========================
    # v4.0 Phase 3 scanner fields
    # ==========================
    jwt_scan_json = Column(Text, nullable=True)        # Full JWKS key entry JSON
    container_scan_json = Column(Text, nullable=True)   # Full syft artifact JSON
    source_scan_json = Column(Text, nullable=True)      # Full semgrep finding JSON
    cloud_scan_json = Column(Text, nullable=True)       # Full cloud resource metadata JSON

    # ==========================
    # v4.2 Identity scanner fields
    # ==========================
    kerberos_scan_json = Column(Text, nullable=True)  # Full Kerberos scan JSON
    saml_scan_json = Column(Text, nullable=True)       # Full SAML scan JSON
    dnssec_scan_json = Column(Text, nullable=True)     # Full DNSSEC scan JSON

    # ==========================
    # v4.3 GCP connector fields
    # ==========================
    gcs_scan_json = Column(Text, nullable=True)        # GCS bucket list JSON (Phase 28 hand-off)

    # ==========================
    # v4.3 Data-at-Rest fields
    # ==========================
    dat_scan_json = Column(Text, nullable=True)  # Universal DAR scan result JSON (Phase 27+)
    severity = Column(String(16), nullable=True)  # Finding severity: HIGH, MEDIUM, LOW, INFO
