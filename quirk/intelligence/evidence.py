from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Mapping, Optional, Set, Tuple

EVIDENCE_SCHEMA_VERSION = "1.0.0"

_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES")


def _as_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _to_iso_z(dt: datetime) -> str:
    return _as_utc_naive(dt).isoformat() + "Z"


def _resolve_reference_utc(endpoints: Iterable[Any], reference_utc: Optional[datetime]) -> datetime:
    if reference_utc is not None:
        return _as_utc_naive(reference_utc)

    latest: Optional[datetime] = None
    for ep in endpoints:
        scanned_at = getattr(ep, "scanned_at", None)
        if not isinstance(scanned_at, datetime):
            continue
        v = _as_utc_naive(scanned_at)
        if latest is None or v > latest:
            latest = v

    return latest if latest is not None else datetime(1970, 1, 1)


def _finding_targets(findings: Iterable[Mapping[str, Any]], wanted_title: str) -> Set[Tuple[str, int]]:
    out: Set[Tuple[str, int]] = set()
    for f in findings:
        if (f.get("title") or "") != wanted_title:
            continue
        host = str(f.get("host") or "")
        port = int(f.get("port") or 0)
        out.add((host, port))
    return out


def build_evidence_summary(
    endpoints: Iterable[Any],
    findings: Optional[Iterable[Mapping[str, Any]]] = None,
    *,
    expiring_days: int = 30,
    reference_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    endpoint_list = list(endpoints)
    finding_list = list(findings) if findings is not None else []
    ref_utc = _resolve_reference_utc(endpoint_list, reference_utc)
    expiring_cutoff = ref_utc + timedelta(days=max(0, int(expiring_days)))

    protocol_counts = {k: 0 for k in _PROTOCOL_KEYS}
    cert_key_type_counts = {"RSA": 0, "ECDSA": 0}
    tls_enum_success_count = 0

    certs_observed = 0
    cert_expired_count = 0
    cert_expiring_count = 0
    cert_self_signed_count = 0

    scan_error_count = 0
    mtls_targets: Set[Tuple[str, int]] = set()

    identity_weak_etype_count = 0
    saml_weak_signing_count = 0
    dnssec_weak_algo_count = 0

    # DAR protocol counters (Phase 27+)
    dar_db_plaintext_count = 0    # PG ssl=off + MySQL SSL disabled
    dar_db_weak_ssl_count = 0     # MySQL weak cipher

    # Object storage DAR counters (Phase 28, per D-09)
    dar_storage_unencrypted_count = 0   # S3/unencrypted (HIGH)
    dar_storage_aws_managed_count = 0   # S3/sse-kms-aws + BLOB/platform-managed (MEDIUM)

    # Kubernetes DAR counters (Phase 29)
    dar_k8s_unencrypted_count = 0       # EKS/GKE/AKS unencrypted clusters (HIGH)
    dar_k8s_inaccessible_count = 0      # AKS/platform-managed, encryption-config-inaccessible, rbac-403 (MEDIUM)

    for ep in endpoint_list:
        host = str(getattr(ep, "host", "") or "")
        port = int(getattr(ep, "port", 0) or 0)

        proto = str(getattr(ep, "protocol", "") or "").upper()
        if proto in protocol_counts:
            protocol_counts[proto] += 1
        if proto == "TLS" and (getattr(ep, "tls_supported_versions", "") or ""):
            tls_enum_success_count += 1

        scan_error = getattr(ep, "scan_error", None)
        if scan_error:
            scan_error_count += 1

        blocker = str(getattr(ep, "tls_blocker_reason", "") or "")
        if blocker == "MTLS_REQUIRED":
            mtls_targets.add((host, port))

        key_alg = str(getattr(ep, "cert_pubkey_alg", "") or "").upper()
        if key_alg.startswith("RSA"):
            cert_key_type_counts["RSA"] += 1
        elif key_alg.startswith("ECDSA"):
            cert_key_type_counts["ECDSA"] += 1

        cert_not_after = getattr(ep, "cert_not_after", None)
        if isinstance(cert_not_after, datetime):
            certs_observed += 1
            na = _as_utc_naive(cert_not_after)
            if na < ref_utc:
                cert_expired_count += 1
            elif na <= expiring_cutoff:
                cert_expiring_count += 1

        subject = str(getattr(ep, "cert_subject", "") or "").strip()
        issuer = str(getattr(ep, "cert_issuer", "") or "").strip()
        if subject and issuer and subject == issuer:
            cert_self_signed_count += 1

        # Identity protocol counters (IDENT-01)
        if proto == "KERBEROS":
            sd = str(getattr(ep, "service_detail", "") or "")
            # service_detail format: "etype:{id}:{name}:{severity}"
            parts = sd.split(":")
            if len(parts) >= 4 and parts[-1] in ("CRITICAL", "HIGH"):
                identity_weak_etype_count += 1

        elif proto == "SAML":
            _saml_alg = str(getattr(ep, "cert_pubkey_alg", "") or "").upper()
            _saml_size = getattr(ep, "cert_pubkey_size", None)
            if _saml_alg == "SHA1":
                saml_weak_signing_count += 1
            elif _saml_size is not None and isinstance(_saml_size, int) and _saml_size < 2048:
                saml_weak_signing_count += 1

        elif proto == "DNSSEC":
            _dnssec_alg = str(getattr(ep, "cert_pubkey_alg", "") or "").upper()
            # Weak algorithms per RFC 8624/9905 plus unsigned/broken zone indicators
            _DNSSEC_WEAK_ALGS = {"RSASHA1", "RSASHA1-NSEC3-SHA1", "RSAMD5", "DSA", "DSA-NSEC3-SHA1", "SHA1-DS"}
            if _dnssec_alg in _DNSSEC_WEAK_ALGS:
                dnssec_weak_algo_count += 1
            elif _dnssec_alg == "NONE":
                # Unsigned zone — no algorithm weakness but high security concern
                dnssec_weak_algo_count += 1

        elif proto == "POSTGRESQL":
            if getattr(ep, "scan_error", None) == "insufficient-privilege":
                pass  # privilege gap — not a confirmed vulnerability
            else:
                sd = str(getattr(ep, "service_detail", "") or "")
                if "ssl-off" in sd:
                    dar_db_plaintext_count += 1

        elif proto == "MYSQL":
            sd = str(getattr(ep, "service_detail", "") or "")
            if "ssl-off" in sd:
                dar_db_plaintext_count += 1
            elif "-weak" in sd:
                dar_db_weak_ssl_count += 1

        elif proto == "RDS":
            sd = str(getattr(ep, "service_detail", "") or "")
            if "RDS/none" in sd:
                dar_db_plaintext_count += 1
            # RDS/sse-rds and RDS/sse-kms-* are positive posture — no penalty

        elif proto == "S3":
            sd = str(getattr(ep, "service_detail", "") or "")
            if "S3/unencrypted" in sd:
                dar_storage_unencrypted_count += 1
            elif "S3/sse-kms-aws" in sd:
                dar_storage_aws_managed_count += 1
            # S3/sse-s3 and S3/sse-kms-cmk are positive posture — no penalty

        elif proto == "AZURE_BLOB":
            sd = str(getattr(ep, "service_detail", "") or "")
            if "BLOB/platform-managed" in sd:
                dar_storage_aws_managed_count += 1
            # BLOB/cmk is positive posture — no penalty

        elif proto == "KUBERNETES":
            sd = str(getattr(ep, "service_detail", "") or "")
            scan_err = str(getattr(ep, "scan_error", "") or "")
            if "/unencrypted" in sd:
                # Matches "EKS/unencrypted" and "GKE/unencrypted" (HIGH severity)
                dar_k8s_unencrypted_count += 1
            elif (scan_err == "insufficient-rbac-privileges"
                  or scan_err == "encryption-config-inaccessible"
                  or "encryption-config-inaccessible" in sd
                  or "/platform-managed" in sd):
                # Phase 29: connector emits scan_error='insufficient-rbac-privileges' for
                # RBAC 403 (K8S-03 path) and scan_error='encryption-config-inaccessible' via
                # _emit_inaccessible_finding (K8S-03 path). Service-detail substring
                # '/platform-managed' matches the AKS platform-managed case.
                dar_k8s_inaccessible_count += 1
            # EKS/encrypted, GKE/encrypted, AKS/kv-kms, secret-types-summary are positive/neutral

    plaintext_http_targets = _finding_targets(finding_list, "Plaintext HTTP service detected")
    http_on_tls_port_targets = _finding_targets(finding_list, "HTTP on TLS-designated port")
    mtls_targets |= _finding_targets(finding_list, "mTLS required")

    finding_severity_counter = Counter(str(f.get("severity") or "INFO").upper() for f in finding_list)
    finding_severity_counts = {
        "CRITICAL": finding_severity_counter.get("CRITICAL", 0),
        "HIGH": finding_severity_counter.get("HIGH", 0),
        "MEDIUM": finding_severity_counter.get("MEDIUM", 0),
        "LOW": finding_severity_counter.get("LOW", 0),
        "INFO": finding_severity_counter.get("INFO", 0),
    }

    total_endpoints = len(endpoint_list)
    scan_error_rate = round((scan_error_count / total_endpoints), 4) if total_endpoints else 0.0
    tls_total = protocol_counts["TLS"]
    tls_enum_coverage_ratio = round((tls_enum_success_count / tls_total), 4) if tls_total else 1.0

    return {
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "reference_utc": _to_iso_z(ref_utc),
        "expiring_within_days": max(0, int(expiring_days)),
        "totals": {
            "endpoints": total_endpoints,
            "findings": len(finding_list),
        },
        "protocol_counts": protocol_counts,
        "plaintext_http_count": len(plaintext_http_targets),
        "http_on_tls_port_count": len(http_on_tls_port_targets),
        "mtls_present_count": len(mtls_targets),
        "cert_key_type_counts": cert_key_type_counts,
        "certificate_observations": {
            "certs_observed": certs_observed,
            "expired_count": cert_expired_count,
            "expiring_count": cert_expiring_count,
            "self_signed_count": cert_self_signed_count,
        },
        "scan_error": {
            "count": scan_error_count,
            "rate": scan_error_rate,
        },
        "tls_enum_coverage_ratio": tls_enum_coverage_ratio,
        "tls_enum_coverage_pct": round(tls_enum_coverage_ratio * 100.0, 2),
        "finding_severity_counts": finding_severity_counts,
        "identity_weak_etype_count": identity_weak_etype_count,
        "saml_weak_signing_count": saml_weak_signing_count,
        "dnssec_weak_algo_count": dnssec_weak_algo_count,
        "identity_kerberos_weak_etype_ratio": round(identity_weak_etype_count / total_endpoints, 4) if total_endpoints else 0.0,
        "identity_saml_weak_signing_ratio": round(saml_weak_signing_count / total_endpoints, 4) if total_endpoints else 0.0,
        "identity_dnssec_weak_algo_ratio": round(dnssec_weak_algo_count / total_endpoints, 4) if total_endpoints else 0.0,
        "dar_db_plaintext_count": dar_db_plaintext_count,
        "dar_db_weak_ssl_count": dar_db_weak_ssl_count,
        "dar_db_plaintext_ratio": round(dar_db_plaintext_count / total_endpoints, 4) if total_endpoints else 0.0,
        "dar_db_weak_ssl_ratio": round(dar_db_weak_ssl_count / total_endpoints, 4) if total_endpoints else 0.0,
        "dar_storage_unencrypted_count": dar_storage_unencrypted_count,
        "dar_storage_aws_managed_count": dar_storage_aws_managed_count,
        "dar_storage_unencrypted_ratio": round(dar_storage_unencrypted_count / total_endpoints, 4) if total_endpoints else 0.0,
        "dar_storage_aws_managed_ratio": round(dar_storage_aws_managed_count / total_endpoints, 4) if total_endpoints else 0.0,
        "dar_k8s_unencrypted_count": dar_k8s_unencrypted_count,
        "dar_k8s_inaccessible_count": dar_k8s_inaccessible_count,
        "dar_k8s_unencrypted_ratio": round(dar_k8s_unencrypted_count / total_endpoints, 4) if total_endpoints else 0.0,
        "dar_k8s_inaccessible_ratio": round(dar_k8s_inaccessible_count / total_endpoints, 4) if total_endpoints else 0.0,
    }
