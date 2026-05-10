"""GCP cloud connector for cryptographic resource enumeration (GCP-01, GCP-02, GCP-03).

Scans Cloud KMS key specs, Cloud SQL TLS enforcement, and GCS bucket encryption.
Uses Application Default Credentials (ADC) -- no credentials stored in this module.
Degrades gracefully when google-api-python-client is not installed.

Minimum required GCP IAM roles for scanner:
  - roles/cloudkms.viewer (or cloudkms.cryptoKeys.list)
  - roles/cloudsql.viewer (or cloudsql.instances.list)
  - roles/storage.objectViewer (or storage.buckets.list)
"""
from __future__ import annotations

import json
from typing import List, Optional

from quirk.models import CryptoEndpoint
from quirk.util.safe_exc import safe_str

# ---------------------------------------------------------------------------
# google-api-python-client optional import (D-02, D-07)
# Names must remain at module level (even as None) for test patching.
# ---------------------------------------------------------------------------
try:
    from googleapiclient.discovery import build as _gcp_build
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    GCP_AVAILABLE = True
except ImportError:
    _gcp_build = None           # type: ignore[assignment]
    google = None               # type: ignore[assignment]
    DefaultCredentialsError = None  # type: ignore[assignment]
    GCP_AVAILABLE = False

# ---------------------------------------------------------------------------
# GCP KMS CryptoKeyVersionAlgorithm -> (algorithm, key_size) mapping (D-07)
# All 47 entries from cloudkms.v1.json in google-api-python-client 2.194.0
# ---------------------------------------------------------------------------
GCP_KMS_ALGORITHM_MAP = {
    # Symmetric encryption
    "GOOGLE_SYMMETRIC_ENCRYPTION": ("AES", 256),
    "AES_128_GCM": ("AES", 128),
    "AES_256_GCM": ("AES", 256),
    "AES_128_CBC": ("AES", 128),
    "AES_256_CBC": ("AES", 256),
    "AES_128_CTR": ("AES", 128),
    "AES_256_CTR": ("AES", 256),
    # RSA signing -- PKCS1
    "RSA_SIGN_PKCS1_2048_SHA256": ("RSA", 2048),
    "RSA_SIGN_PKCS1_3072_SHA256": ("RSA", 3072),
    "RSA_SIGN_PKCS1_4096_SHA256": ("RSA", 4096),
    "RSA_SIGN_PKCS1_4096_SHA512": ("RSA", 4096),
    # RSA signing -- PSS
    "RSA_SIGN_PSS_2048_SHA256": ("RSA", 2048),
    "RSA_SIGN_PSS_3072_SHA256": ("RSA", 3072),
    "RSA_SIGN_PSS_4096_SHA256": ("RSA", 4096),
    "RSA_SIGN_PSS_4096_SHA512": ("RSA", 4096),
    # RSA signing -- Raw PKCS1
    "RSA_SIGN_RAW_PKCS1_2048": ("RSA", 2048),
    "RSA_SIGN_RAW_PKCS1_3072": ("RSA", 3072),
    "RSA_SIGN_RAW_PKCS1_4096": ("RSA", 4096),
    # RSA decryption
    "RSA_DECRYPT_OAEP_2048_SHA256": ("RSA", 2048),
    "RSA_DECRYPT_OAEP_3072_SHA256": ("RSA", 3072),
    "RSA_DECRYPT_OAEP_4096_SHA256": ("RSA", 4096),
    "RSA_DECRYPT_OAEP_4096_SHA512": ("RSA", 4096),
    "RSA_DECRYPT_OAEP_2048_SHA1": ("RSA", 2048),
    "RSA_DECRYPT_OAEP_3072_SHA1": ("RSA", 3072),
    "RSA_DECRYPT_OAEP_4096_SHA1": ("RSA", 4096),
    # EC signing
    "EC_SIGN_P256_SHA256": ("ECDSA", 256),
    "EC_SIGN_P384_SHA384": ("ECDSA", 384),
    "EC_SIGN_SECP256K1_SHA256": ("ECDSA", 256),
    "EC_SIGN_ED25519": ("EdDSA", 256),
    # HMAC
    "HMAC_SHA256": ("HMAC", 256),
    "HMAC_SHA1": ("HMAC", 160),
    "HMAC_SHA384": ("HMAC", 384),
    "HMAC_SHA512": ("HMAC", 512),
    "HMAC_SHA224": ("HMAC", 224),
    # External (wrapping key -- algorithm from external KMS)
    "EXTERNAL_SYMMETRIC_ENCRYPTION": ("AES", 256),
    # PQC algorithms (Cloud KMS, produce quantum-safe findings)
    "ML_KEM_768": ("ml-kem-768", 768),
    "ML_KEM_1024": ("ml-kem-1024", 1024),
    "KEM_XWING": ("ml-kem-768", 768),
    "PQ_SIGN_ML_DSA_44": ("ml-dsa-44", 44),
    "PQ_SIGN_ML_DSA_65": ("ml-dsa-65", 65),
    "PQ_SIGN_ML_DSA_87": ("ml-dsa-87", 87),
    "PQ_SIGN_SLH_DSA_SHA2_128S": ("slh-dsa-128", 128),
    "PQ_SIGN_HASH_SLH_DSA_SHA2_128S_SHA256": ("slh-dsa-128", 128),
    "PQ_SIGN_ML_DSA_44_EXTERNAL_MU": ("ml-dsa-44", 44),
    "PQ_SIGN_ML_DSA_65_EXTERNAL_MU": ("ml-dsa-65", 65),
    "PQ_SIGN_ML_DSA_87_EXTERNAL_MU": ("ml-dsa-87", 87),
    # Unspecified -- skip/unknown
    "CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED": ("UNKNOWN", None),
}

# ---------------------------------------------------------------------------
# Cloud SQL TLS finding map (D-08)
# TRUSTED_CLIENT_CERTIFICATE_REQUIRED -> no finding (mTLS enforced, safe)
# None / "" / SSL_MODE_UNSPECIFIED -> treat as ALLOW_UNENCRYPTED (Pitfall 7)
# ---------------------------------------------------------------------------
SSL_FINDING_MAP = {
    "ALLOW_UNENCRYPTED_AND_ENCRYPTED": ("HIGH", "plaintext connections allowed"),
    "ENCRYPTED_ONLY": ("MEDIUM", "encryption required but no client certificate validation"),
    # "TRUSTED_CLIENT_CERTIFICATE_REQUIRED" -> no finding (mTLS enforced)
}

# ---------------------------------------------------------------------------
# Protection level -> service_detail encoding
# ---------------------------------------------------------------------------
_PROTECTION_LEVEL_MAP = {
    "SOFTWARE": "CloudKMS/SOFTWARE",
    "HSM": "CloudKMS/HSM",
    "EXTERNAL": "CloudKMS/EXTERNAL",
    "EXTERNAL_VPC": "CloudKMS/EXTERNAL_VPC",
    "HSM_SINGLE_TENANT": "CloudKMS/HSM_SINGLE_TENANT",
}


def _scan_kms(service, project_id: str, logger) -> List[CryptoEndpoint]:
    """Enumerate Cloud KMS keys with auto-location discovery and primary version algorithm mapping.

    Auto-discovers all KMS locations via projects.locations.list (D-05).
    One CryptoEndpoint per key (primary version only, per D-04).
    """
    results: List[CryptoEndpoint] = []
    project_resource = f"projects/{project_id}"
    try:
        # Auto-discover all locations
        loc_request = service.projects().locations().list(name=project_resource)
        while loc_request is not None:
            loc_response = loc_request.execute()
            for location in loc_response.get("locations", []):
                location_id = location.get("locationId", "")
                location_name = f"{project_resource}/locations/{location_id}"

                # List key rings in this location
                kr_request = service.projects().locations().keyRings().list(
                    parent=location_name
                )
                while kr_request is not None:
                    kr_response = kr_request.execute()
                    for key_ring in kr_response.get("keyRings", []):
                        key_ring_name = key_ring.get("name", "")

                        # List crypto keys in this key ring
                        ck_request = service.projects().locations().keyRings().cryptoKeys().list(
                            parent=key_ring_name
                        )
                        while ck_request is not None:
                            ck_response = ck_request.execute()
                            for key in ck_response.get("cryptoKeys", []):
                                key_name = key.get("name", "")
                                try:
                                    # Guard against missing primary field (Pitfall 3)
                                    primary = key.get("primary") or {}
                                    state = primary.get("state", "")

                                    # Skip disabled/destroyed keys
                                    if state and state != "ENABLED":
                                        continue

                                    # Extract algorithm from primary version; fall back to versionTemplate
                                    algorithm = primary.get("algorithm", "")
                                    if not algorithm:
                                        algorithm = key.get("versionTemplate", {}).get("algorithm", "")

                                    alg_name, key_size = GCP_KMS_ALGORITHM_MAP.get(
                                        algorithm, (algorithm or "UNKNOWN", None)
                                    )

                                    # Skip keys with unspecified/unrecognised algorithm
                                    if alg_name == "UNKNOWN":
                                        if logger:
                                            logger.v(
                                                f"Cloud KMS key {key_name} has unspecified"
                                                " algorithm -- skipped"
                                            )
                                        continue

                                    # Protection level
                                    protection_level_raw = primary.get("protectionLevel", "SOFTWARE")
                                    protection_level = _PROTECTION_LEVEL_MAP.get(
                                        protection_level_raw, "CloudKMS/SOFTWARE"
                                    )

                                    ep = CryptoEndpoint(
                                        host=key_name,
                                        port=0,
                                        protocol="GCP",
                                        cert_pubkey_alg=alg_name,
                                        cert_pubkey_size=key_size,
                                        service_detail=protection_level,
                                        cloud_scan_json=json.dumps(
                                            {
                                                "gcp_algorithm": algorithm,
                                                "key_size": key_size,
                                                "protectionLevel": protection_level,
                                                "purpose": key.get("purpose", ""),
                                            },
                                            default=str,
                                        ),
                                    )
                                    results.append(ep)
                                except Exception as exc:
                                    if logger:
                                        logger.v(f"Cloud KMS key scan error for {key_name}: {exc}")

                            ck_request = (
                                service.projects().locations().keyRings()
                                .cryptoKeys().list_next(
                                    previous_request=ck_request,
                                    previous_response=ck_response,
                                )
                            )

                    kr_request = service.projects().locations().keyRings().list_next(
                        previous_request=kr_request, previous_response=kr_response
                    )

            loc_request = service.projects().locations().list_next(
                previous_request=loc_request, previous_response=loc_response
            )
    except Exception as exc:
        if logger:
            logger.v(f"Cloud KMS scan error: {exc}")
    return results


def _scan_cloud_sql(service, project_id: str, logger) -> List[CryptoEndpoint]:
    """Enumerate Cloud SQL instances and produce TLS enforcement findings.

    Maps sslMode values per D-08. Missing/null/SSL_MODE_UNSPECIFIED treated as HIGH (Pitfall 7).
    TRUSTED_CLIENT_CERTIFICATE_REQUIRED produces no finding (mTLS enforced).
    """
    results: List[CryptoEndpoint] = []
    try:
        request = service.instances().list(project=project_id)
        while request is not None:
            response = request.execute()
            for instance in response.get("items", []):
                instance_name = instance.get("name", "")
                try:
                    settings = instance.get("settings", {})
                    ip_cfg = settings.get("ipConfiguration", {})
                    ssl_mode = ip_cfg.get("sslMode")

                    # Treat missing/empty/SSL_MODE_UNSPECIFIED as ALLOW_UNENCRYPTED (Pitfall 7)
                    if not ssl_mode or ssl_mode == "SSL_MODE_UNSPECIFIED":
                        ssl_mode = "ALLOW_UNENCRYPTED_AND_ENCRYPTED"

                    # TRUSTED_CLIENT_CERTIFICATE_REQUIRED -> no finding (mTLS enforced, safe)
                    if ssl_mode == "TRUSTED_CLIENT_CERTIFICATE_REQUIRED":
                        continue

                    finding = SSL_FINDING_MAP.get(ssl_mode)
                    if finding is None:
                        continue

                    severity, description = finding
                    ep = CryptoEndpoint(
                        host=f"gcp://{project_id}/sql/{instance_name}",
                        port=0,
                        protocol="CLOUD_SQL",
                        cert_pubkey_alg=severity,
                        service_detail=instance_name,
                        cloud_scan_json=json.dumps(
                            {"sslMode": ssl_mode, "finding": description},
                            default=str,
                        ),
                    )
                    results.append(ep)
                except Exception as exc:
                    if logger:
                        logger.v(f"Cloud SQL instance scan error for {instance_name}: {exc}")

            request = service.instances().list_next(
                previous_request=request, previous_response=response
            )
    except Exception as exc:
        if logger:
            logger.v(f"Cloud SQL scan error: {exc}")
    return results


def _scan_gcs(service, project_id: str, logger) -> List[CryptoEndpoint]:
    """Enumerate GCS buckets, detect CMEK vs Google-managed encryption.

    Creates one sentinel endpoint with gcs_scan_json for Phase 28 hand-off (D-03).
    Creates per-bucket endpoints for CMEK/Google-Managed findings.
    Response field is 'items', NOT 'buckets' (Pitfall 4).
    """
    results: List[CryptoEndpoint] = []
    bucket_list: list = []
    try:
        request = service.buckets().list(project=project_id)
        while request is not None:
            response = request.execute()
            # CRITICAL: response field is "items", NOT "buckets" (Pitfall 4)
            for bucket in response.get("items", []):
                bucket_list.append(bucket)

            request = service.buckets().list_next(
                previous_request=request, previous_response=response
            )

        # Sentinel endpoint: carries the full bucket list for Phase 28 (D-03)
        sentinel = CryptoEndpoint(
            host=f"gcp://{project_id}/storage",
            port=0,
            protocol="GCP",
            cert_pubkey_alg="GCS-SUMMARY",
            gcs_scan_json=json.dumps(bucket_list, default=str),
            service_detail="GCS",
        )
        results.append(sentinel)

        # Per-bucket endpoints for CMEK/Google-Managed findings
        for bucket in bucket_list:
            bucket_name = bucket.get("name", "")
            try:
                enc = bucket.get("encryption", {})
                kms_key = enc.get("defaultKmsKeyName")
                alg = "CMEK" if kms_key else "Google-Managed"
                ep = CryptoEndpoint(
                    host=f"gcp://{project_id}/buckets/{bucket_name}",
                    port=0,
                    protocol="GCP",
                    cert_pubkey_alg=alg,
                    service_detail="GCS",
                    cloud_scan_json=json.dumps(bucket, default=str),
                )
                results.append(ep)
            except Exception as exc:
                if logger:
                    logger.v(f"GCS bucket scan error for {bucket_name}: {exc}")

    except Exception as exc:
        if logger:
            logger.v(f"GCS scan error: {exc}")
    return results


def scan_gcp_targets(project_id: str, logger=None) -> List[CryptoEndpoint]:
    """Enumerate GCP cryptographic resources and return as CryptoEndpoint list.

    Scans: Cloud KMS key specs (GCP-01), Cloud SQL TLS enforcement (GCP-02),
    GCS bucket encryption (GCP-03).

    Uses Application Default Credentials (ADC) -- no credentials stored here.
    Degrades gracefully when google-api-python-client is not installed or credentials unavailable.

    Args:
        project_id: GCP project ID string (e.g. "my-gcp-project").
        logger: Optional logger with .v() method.

    Returns:
        List of CryptoEndpoint instances. Empty list if GCP SDK not installed or
        project_id is empty. Single scan_error endpoint if credentials unavailable.
    """
    if not GCP_AVAILABLE:
        if logger:
            logger.v("google-api-python-client not installed -- GCP scanning unavailable")
        return []

    # V5 input validation (T-26-03): validate non-empty project_id before any API call
    if not project_id:
        if logger:
            logger.v("scan_gcp_targets: project_id is empty -- GCP scanning skipped")
        return []

    # Acquire Application Default Credentials (D-02)
    # Catch DefaultCredentialsError at google.auth.default() AND as generic Exception fallback
    try:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    except Exception as exc:
        # DefaultCredentialsError fires here when no ADC is configured (D-04 / Pitfall 2)
        scan_error_msg = f"gcp-credentials-unavailable: {safe_str(exc)}"
        if logger:
            logger.v(scan_error_msg)
        return [
            CryptoEndpoint(
                host=f"gcp://{project_id}",
                port=0,
                protocol="GCP",
                scan_error=scan_error_msg,
            )
        ]

    # Build one service object per GCP API (D-02)
    try:
        kms_service = _gcp_build("cloudkms", "v1", credentials=credentials)
    except Exception as exc:
        if logger:
            logger.v(f"GCP cloudkms service build error: {exc}")
        kms_service = None

    try:
        sql_service = _gcp_build("sqladmin", "v1", credentials=credentials)
    except Exception as exc:
        if logger:
            logger.v(f"GCP sqladmin service build error: {exc}")
        sql_service = None

    try:
        storage_service = _gcp_build("storage", "v1", credentials=credentials)
    except Exception as exc:
        if logger:
            logger.v(f"GCP storage service build error: {exc}")
        storage_service = None

    results: List[CryptoEndpoint] = []

    if kms_service is not None:
        results.extend(_scan_kms(kms_service, project_id, logger))

    if sql_service is not None:
        results.extend(_scan_cloud_sql(sql_service, project_id, logger))

    if storage_service is not None:
        results.extend(_scan_gcs(storage_service, project_id, logger))

    return results
