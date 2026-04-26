"""AWS cloud connector for cryptographic resource enumeration (SCAN-06).

Scans ACM certificates, KMS keys, CloudFront distributions, and ELB listeners.
Uses ambient credential resolution only — no credentials stored in this module.
Degrades gracefully when boto3 is not installed.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint

# ---------------------------------------------------------------------------
# boto3 optional import (D-15, D-17)
# ---------------------------------------------------------------------------
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None  # type: ignore[assignment]
    BOTO3_AVAILABLE = False

# ---------------------------------------------------------------------------
# KMS KeySpec -> (algorithm, key_size) mapping
# ---------------------------------------------------------------------------
KMS_KEY_SPEC_MAP = {
    "RSA_2048": ("RSA", 2048),
    "RSA_3072": ("RSA", 3072),
    "RSA_4096": ("RSA", 4096),
    "ECC_NIST_P256": ("ECDSA", 256),
    "ECC_NIST_P384": ("ECDSA", 384),
    "ECC_NIST_P521": ("ECDSA", 521),
    "ECC_SECG_P256K1": ("ECDSA", 256),
    "SYMMETRIC_DEFAULT": ("AES", 256),
    "HMAC_224": ("HMAC", 224),
    "HMAC_256": ("HMAC", 256),
    "HMAC_384": ("HMAC", 384),
    "HMAC_512": ("HMAC", 512),
    "SM2": ("SM2", 256),
}


def _scan_acm(session, logger) -> List[CryptoEndpoint]:
    """Enumerate ACM certificates using paginator (pitfall: must use paginator, not list_certificates directly)."""
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("acm")
        paginator = client.get_paginator("list_certificates")
        for page in paginator.paginate():
            for cert_summary in page.get("CertificateSummaryList", []):
                arn = cert_summary.get("CertificateArn", "")
                try:
                    detail = client.describe_certificate(CertificateArn=arn).get("Certificate", {})
                    key_alg = detail.get("KeyAlgorithm", "")
                    ep = CryptoEndpoint(
                        host=arn,
                        port=0,
                        protocol="AWS",
                        cert_pubkey_alg=key_alg,
                        cloud_scan_json=json.dumps(detail, default=str),
                        service_detail="ACM",
                    )
                    results.append(ep)
                except Exception as exc:
                    if logger:
                        logger.v(f"ACM describe_certificate failed for {arn}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"ACM scan error: {exc}")
    return results


def _scan_rds_encryption(session, logger) -> List[CryptoEndpoint]:
    """Detect RDS instance encryption-at-rest posture (DB-03).

    Derives service_detail from StorageEncrypted + KmsKeyId fields
    (NOT StorageEncryptionType -- that field does not exist in the boto3 API):
      RDS/none         -- StorageEncrypted == False -> HIGH finding
      RDS/sse-rds      -- StorageEncrypted True, KmsKeyId absent/empty
      RDS/sse-kms-aws  -- StorageEncrypted True, KmsKeyId with alias/aws/ pattern
      RDS/sse-kms-cmk  -- StorageEncrypted True, KmsKeyId present (customer-managed)
    """
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("rds")
        paginator = client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                db_id = db.get("DBInstanceIdentifier", "unknown")
                db_arn = db.get("DBInstanceArn", db_id)
                try:
                    encrypted = db.get("StorageEncrypted", False)
                    kms_key = str(db.get("KmsKeyId") or "").strip()

                    if not encrypted:
                        service_detail = "RDS/none"
                        severity = "HIGH"
                    elif not kms_key:
                        service_detail = "RDS/sse-rds"
                        severity = None
                    elif "alias/aws/" in kms_key:
                        service_detail = "RDS/sse-kms-aws"
                        severity = None
                    else:
                        service_detail = "RDS/sse-kms-cmk"
                        severity = None

                    db_port = int((db.get("Endpoint") or {}).get("Port") or 5432)
                    ep = CryptoEndpoint(
                        host=db_arn,
                        port=db_port,
                        protocol="RDS",
                        service_detail=service_detail,
                        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    if severity:
                        ep.severity = severity
                    results.append(ep)

                except Exception as exc:
                    if logger:
                        logger.v(f"RDS instance scan error for {db_id}: {exc}")

    except Exception as exc:
        if logger:
            logger.v(f"RDS scan error: {exc}")
    return results


def _scan_s3_encryption(
    session,
    logger,
    session_start=None,
    endpoint_url=None,
) -> List[CryptoEndpoint]:
    """Detect S3 bucket encryption posture per bucket (STOR-01).

    Per D-06 severity ladder:
      ServerSideEncryptionConfigurationNotFoundError → HIGH/S3/unencrypted
      Empty Rules / SSEAlgorithm 'none'              → HIGH/S3/unencrypted
      SSEAlgorithm 'AES256'                          → S3/sse-s3 (no severity)
      SSEAlgorithm 'aws:kms' + alias/aws/s3 or absent KeyID → MEDIUM/S3/sse-kms-aws
      SSEAlgorithm 'aws:kms' + customer KeyID        → S3/sse-kms-cmk (no severity)

    Uses ThreadPoolExecutor(max_workers=10) per D-06. list_buckets is NOT a paginator
    (raises OperationNotPageableError); call it directly. ServerSideEncryptionConfiguration-
    NotFoundError is NOT a scan error — it IS the unencrypted detection path.

    Args:
        session: boto3 Session (or MagicMock in tests).
        logger: optional logger with .v() method.
        session_start: timezone-aware datetime; falls back to now() when absent (ISSUE-3).
        endpoint_url: optional MinIO/LocalStack endpoint override (D-08, Phase 28 chaos lab).
    """
    from concurrent.futures import ThreadPoolExecutor
    from botocore.exceptions import ClientError

    if not BOTO3_AVAILABLE:
        if logger:
            logger.v("boto3 not installed — S3 scanning unavailable")
        return []

    results: List[CryptoEndpoint] = []
    ts = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)

    try:
        client_kwargs = {}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        client = session.client("s3", **client_kwargs)

        # list_buckets is NOT a paginator — calling get_paginator() raises OperationNotPageableError.
        buckets = client.list_buckets().get("Buckets", []) or []

        def _classify(bucket_name: str):
            """Returns dict {service_detail, severity} or None to skip the bucket."""
            try:
                resp = client.get_bucket_encryption(Bucket=bucket_name)
                rules = (resp.get("ServerSideEncryptionConfiguration", {}) or {}).get("Rules", []) or []
                if not rules:
                    return {"service_detail": "S3/unencrypted", "severity": "HIGH"}
                rule = rules[0].get("ApplyServerSideEncryptionByDefault", {}) or {}
                algo = str(rule.get("SSEAlgorithm", "") or "").strip()
                kms_key = str(rule.get("KMSMasterKeyID") or "").strip()
                if algo == "AES256":
                    return {"service_detail": "S3/sse-s3", "severity": None}
                if algo == "aws:kms":
                    if not kms_key or "alias/aws/s3" in kms_key:
                        return {"service_detail": "S3/sse-kms-aws", "severity": "MEDIUM"}
                    return {"service_detail": "S3/sse-kms-cmk", "severity": None}
                # SSEAlgorithm "none" or unknown → unencrypted
                return {"service_detail": "S3/unencrypted", "severity": "HIGH"}
            except ClientError as exc:
                code = (exc.response or {}).get("Error", {}).get("Code", "") if hasattr(exc, "response") else ""
                if code == "ServerSideEncryptionConfigurationNotFoundError":
                    # Detection path — NOT a scan error
                    return {"service_detail": "S3/unencrypted", "severity": "HIGH"}
                if logger:
                    logger.v(f"S3 get_bucket_encryption error for {bucket_name}: {exc}")
                return None
            except Exception as exc:
                if logger:
                    logger.v(f"S3 get_bucket_encryption error for {bucket_name}: {exc}")
                return None

        def _build_endpoint(bucket):
            name = bucket.get("Name", "") if isinstance(bucket, dict) else ""
            if not name:
                return None
            classification = _classify(name)
            if classification is None:
                return None
            ep = CryptoEndpoint(
                host=f"arn:aws:s3:::{name}",
                port=0,
                protocol="S3",
                service_detail=classification["service_detail"],
                dat_scan_json=json.dumps(
                    {"bucket": name, **classification}, default=str
                ),
                scanned_at=ts,
            )
            if classification["severity"]:
                ep.severity = classification["severity"]
            return ep

        with ThreadPoolExecutor(max_workers=10) as executor:
            for ep in executor.map(_build_endpoint, buckets):
                if ep is not None:
                    results.append(ep)

    except Exception as exc:
        if logger:
            logger.v(f"S3 scan error: {exc}")

    return results


def _scan_kms(session, logger) -> List[CryptoEndpoint]:
    """Enumerate KMS keys and map their KeySpec to algorithm/size."""
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("kms")
        paginator = client.get_paginator("list_keys")
        for page in paginator.paginate():
            for key_entry in page.get("Keys", []):
                key_id = key_entry.get("KeyId", "")
                try:
                    metadata = client.describe_key(KeyId=key_id).get("KeyMetadata", {})
                    arn = metadata.get("Arn", key_id)
                    # KeySpec preferred; fall back to CustomerMasterKeySpec for older keys
                    key_spec = metadata.get("KeySpec") or metadata.get("CustomerMasterKeySpec", "")
                    alg_name, key_size = KMS_KEY_SPEC_MAP.get(key_spec, (key_spec, None))
                    ep = CryptoEndpoint(
                        host=arn,
                        port=0,
                        protocol="AWS",
                        cert_pubkey_alg=alg_name,
                        cert_pubkey_size=key_size,
                        cloud_scan_json=json.dumps(metadata, default=str),
                        service_detail="KMS",
                    )
                    results.append(ep)
                except Exception as exc:
                    if logger:
                        logger.v(f"KMS describe_key failed for {key_id}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"KMS scan error: {exc}")
    return results


def _scan_cloudfront(session, logger) -> List[CryptoEndpoint]:
    """Enumerate CloudFront distributions and capture minimum TLS protocol version."""
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("cloudfront")
        paginator = client.get_paginator("list_distributions")
        for page in paginator.paginate():
            dist_list = page.get("DistributionList", {})
            for item in dist_list.get("Items", []):
                arn = item.get("ARN", "")
                viewer_cert = item.get("ViewerCertificate", {})
                min_proto = viewer_cert.get("MinimumProtocolVersion", "")
                dist_data = {
                    "ARN": arn,
                    "Id": item.get("Id", ""),
                    "ViewerCertificate": viewer_cert,
                }
                ep = CryptoEndpoint(
                    host=arn,
                    port=443,
                    protocol="AWS",
                    tls_version=min_proto,
                    cloud_scan_json=json.dumps(dist_data, default=str),
                    service_detail="CloudFront",
                )
                results.append(ep)
    except Exception as exc:
        if logger:
            logger.v(f"CloudFront scan error: {exc}")
    return results


def _scan_elbv2(session, logger) -> List[CryptoEndpoint]:
    """Enumerate ELBv2 load balancers and their HTTPS listener SSL policies."""
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("elbv2")
        lb_paginator = client.get_paginator("describe_load_balancers")
        for lb_page in lb_paginator.paginate():
            for lb in lb_page.get("LoadBalancers", []):
                lb_arn = lb.get("LoadBalancerArn", "")
                try:
                    listeners_resp = client.describe_listeners(LoadBalancerArn=lb_arn)
                    for listener in listeners_resp.get("Listeners", []):
                        if listener.get("Protocol") not in ("HTTPS", "TLS"):
                            continue
                        listener_arn = listener.get("ListenerArn", "")
                        listener_port = listener.get("Port", 443)
                        ssl_policy = listener.get("SslPolicy", "")
                        ep = CryptoEndpoint(
                            host=listener_arn,
                            port=listener_port,
                            protocol="AWS",
                            tls_version=ssl_policy,
                            cloud_scan_json=json.dumps(listener, default=str),
                            service_detail="ELBv2",
                        )
                        results.append(ep)
                except Exception as exc:
                    if logger:
                        logger.v(f"ELBv2 describe_listeners failed for {lb_arn}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"ELBv2 scan error: {exc}")
    return results


def scan_aws_targets(
    region: str,
    profile: Optional[str] = None,
    logger=None,
) -> List[CryptoEndpoint]:
    """Enumerate AWS cryptographic resources and return as CryptoEndpoint list.

    Scans: ACM certificates, KMS keys, CloudFront distributions, ELBv2 HTTPS listeners.

    Args:
        region: AWS region name (e.g. "us-east-1").
        profile: Optional AWS named profile from ~/.aws/credentials.
        logger: Optional logger with .v() method.

    Returns:
        List of CryptoEndpoint instances. Empty list if boto3 not installed.
    """
    if not BOTO3_AVAILABLE:
        if logger:
            logger.v("boto3 not installed — AWS scanning unavailable")
        return []
    session = boto3.Session(region_name=region, profile_name=profile)
    results: List[CryptoEndpoint] = []
    results.extend(_scan_kms(session, logger))
    results.extend(_scan_cloudfront(session, logger))
    results.extend(_scan_elbv2(session, logger))
    results.extend(_scan_acm(session, logger))
    results.extend(_scan_rds_encryption(session, logger))
    return results
