"""Tests for AWS, Azure, and GCP cloud connectors (SCAN-06, SCAN-07, GCP-01, GCP-02, GCP-03).

Tests mock boto3/azure/GCP SDK calls to avoid requiring cloud credentials.
Scanner modules: quirk/scanner/aws_connector.py, quirk/scanner/azure_connector.py, quirk/scanner/gcp_connector.py
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from quirk.scanner.aws_connector import scan_aws_targets
from quirk.scanner.azure_connector import scan_azure_targets

try:
    from quirk.scanner.gcp_connector import scan_gcp_targets
    _HAS_GCP_MODULE = True
except ImportError:
    _HAS_GCP_MODULE = False


# ---- AWS Tests (SCAN-06) ----

def test_aws_acm_pagination():
    """AWS ACM connector must use paginator, not direct list_certificates (pitfall 3)."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"CertificateSummaryList": [
            {"CertificateArn": "arn:aws:acm:us-east-1:123:certificate/abc"}
        ]}
    ]
    mock_client = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_client.describe_certificate.return_value = {
        "Certificate": {
            "CertificateArn": "arn:aws:acm:us-east-1:123:certificate/abc",
            "KeyAlgorithm": "RSA_2048",
            "DomainName": "example.com",
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client

    with patch("quirk.scanner.aws_connector.boto3.Session", return_value=mock_session):
        endpoints = scan_aws_targets(region="us-east-1", profile=None)
        mock_client.get_paginator.assert_called_with("list_certificates")
        assert len(endpoints) >= 1
        assert endpoints[0].protocol == "AWS"


def test_kms_key_spec_mapping():
    """KMS KeySpec must be mapped to cert_pubkey_alg correctly."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Keys": [{"KeyId": "1234abcd"}]}
    ]
    mock_client = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_client.describe_key.return_value = {
        "KeyMetadata": {
            "KeyId": "1234abcd",
            "Arn": "arn:aws:kms:us-east-1:123:key/1234abcd",
            "KeySpec": "RSA_2048",
            "KeyUsage": "SIGN_VERIFY",
            "KeyState": "Enabled",
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client

    with patch("quirk.scanner.aws_connector.boto3.Session", return_value=mock_session):
        endpoints = scan_aws_targets(region="us-east-1", profile=None)
        kms_eps = [ep for ep in endpoints if ep.service_detail and "KMS" in ep.service_detail]
        assert len(kms_eps) >= 1


def test_aws_boto3_unavailable():
    """If boto3 is not importable, scan_aws_targets must return empty list."""
    with patch("quirk.scanner.aws_connector.BOTO3_AVAILABLE", False):
        endpoints = scan_aws_targets(region="us-east-1", profile=None)
        assert endpoints == []


# ---- Azure Tests (SCAN-07) ----

def test_azure_keyvault():
    """Azure Key Vault key type must produce CryptoEndpoint with protocol='AZURE'."""
    mock_key = MagicMock()
    mock_key.name = "my-rsa-key"
    mock_key.key_type = "RSA"
    mock_key.key_size = 2048
    mock_key.id = "https://myvault.vault.azure.net/keys/my-rsa-key/abc123"

    mock_key_client = MagicMock()
    mock_key_client.list_properties_of_keys.return_value = [mock_key]

    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("quirk.scanner.azure_connector.KeyClient", return_value=mock_key_client), \
         patch("quirk.scanner.azure_connector.DefaultAzureCredential"):
        endpoints = scan_azure_targets(
            subscription_id="sub-123",
            keyvault_urls=["https://myvault.vault.azure.net"]
        )
        azure_eps = [ep for ep in endpoints if ep.protocol == "AZURE"]
        assert len(azure_eps) >= 1
        assert azure_eps[0].host is not None


def test_azure_sdk_unavailable():
    """If azure SDK is not importable, scan_azure_targets must return empty list."""
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", False):
        endpoints = scan_azure_targets(subscription_id="sub-123", keyvault_urls=[])
        assert endpoints == []


# ---- GCP Tests (GCP-01, GCP-02, GCP-03) ----

def _build_gcp_mock_service():
    """Build a MagicMock GCP service with chainable Discovery API patterns.

    All list_next() methods return None by default to terminate pagination.
    Individual tests customize specific return values as needed.
    """
    svc = MagicMock()

    # Default: locations list returns empty, terminates pagination
    loc_list = svc.projects.return_value.locations.return_value.list.return_value
    loc_list.execute.return_value = {"locations": []}
    svc.projects.return_value.locations.return_value.list_next.return_value = None

    # Default: keyRings list returns empty
    kr_list = svc.projects.return_value.locations.return_value.keyRings.return_value.list.return_value
    kr_list.execute.return_value = {"keyRings": []}
    svc.projects.return_value.locations.return_value.keyRings.return_value.list_next.return_value = None

    # Default: cryptoKeys list returns empty
    ck_list = (svc.projects.return_value.locations.return_value.keyRings.return_value
               .cryptoKeys.return_value.list.return_value)
    ck_list.execute.return_value = {"cryptoKeys": []}
    (svc.projects.return_value.locations.return_value.keyRings.return_value
     .cryptoKeys.return_value.list_next.return_value) = None

    # Default: Cloud SQL instances list returns empty
    sql_list = svc.instances.return_value.list.return_value
    sql_list.execute.return_value = {}
    svc.instances.return_value.list_next.return_value = None

    # Default: GCS buckets list returns empty
    bucket_list = svc.buckets.return_value.list.return_value
    bucket_list.execute.return_value = {}
    svc.buckets.return_value.list_next.return_value = None

    return svc


@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")
def test_gcp_unavailable():
    """If google-api-python-client is not installed, scan_gcp_targets must return empty list."""
    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", False):
        endpoints = scan_gcp_targets(project_id="my-project")
        assert endpoints == []


@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")
def test_gcp_credentials_error_graceful():
    """DefaultCredentialsError at API call time must produce scan_error endpoint, not crash."""
    mock_service = _build_gcp_mock_service()
    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", True), \
         patch("quirk.scanner.gcp_connector._gcp_build", return_value=mock_service), \
         patch("quirk.scanner.gcp_connector.google") as mock_google:
        mock_google.auth.default.side_effect = Exception(
            "DefaultCredentialsError: Could not automatically determine credentials"
        )
        result = scan_gcp_targets(project_id="my-project")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0].scan_error is not None
        assert "gcp-credentials-unavailable" in result[0].scan_error


@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")
def test_gcp_kms_algorithm_mapping():
    """Cloud KMS RSA_SIGN_PKCS1_2048_SHA256 must map to cert_pubkey_alg=RSA, size=2048."""
    mock_service = _build_gcp_mock_service()

    project = "my-project"
    location = "us-east1"
    ring_name = f"projects/{project}/locations/{location}/keyRings/my-ring"
    key_name = f"{ring_name}/cryptoKeys/my-key"

    # Configure locations list
    (mock_service.projects.return_value.locations.return_value.list.return_value
     .execute.return_value) = {"locations": [{"locationId": location}]}

    # Configure keyRings list
    (mock_service.projects.return_value.locations.return_value.keyRings.return_value
     .list.return_value.execute.return_value) = {"keyRings": [{"name": ring_name}]}

    # Configure cryptoKeys list
    (mock_service.projects.return_value.locations.return_value.keyRings.return_value
     .cryptoKeys.return_value.list.return_value.execute.return_value) = {
        "cryptoKeys": [{
            "name": key_name,
            "primary": {
                "algorithm": "RSA_SIGN_PKCS1_2048_SHA256",
                "protectionLevel": "SOFTWARE",
                "state": "ENABLED",
            },
            "purpose": "ASYMMETRIC_SIGN",
        }]
    }

    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", True), \
         patch("quirk.scanner.gcp_connector._gcp_build", return_value=mock_service), \
         patch("quirk.scanner.gcp_connector.google") as mock_google:
        mock_google.auth.default.return_value = (MagicMock(), project)
        endpoints = scan_gcp_targets(project_id=project)

    gcp_eps = [ep for ep in endpoints
               if ep.protocol == "GCP" and ep.service_detail and "CloudKMS" in ep.service_detail]
    assert len(gcp_eps) >= 1
    assert gcp_eps[0].cert_pubkey_alg == "RSA"
    assert gcp_eps[0].cert_pubkey_size == 2048
    # Confirm pagination terminated at every KMS level (list_next called once and returned None).
    # Guards against future pagination paths auto-creating truthy MagicMock and looping.
    (mock_service.projects.return_value.locations.return_value
     .list_next.assert_called_once())
    (mock_service.projects.return_value.locations.return_value
     .keyRings.return_value.list_next.assert_called_once())
    (mock_service.projects.return_value.locations.return_value
     .keyRings.return_value.cryptoKeys.return_value.list_next.assert_called_once())


@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")
def test_gcp_cloud_sql_plaintext_allowed():
    """Cloud SQL ALLOW_UNENCRYPTED_AND_ENCRYPTED sslMode must produce HIGH finding."""
    mock_service = _build_gcp_mock_service()
    mock_service.instances.return_value.list.return_value.execute.return_value = {
        "items": [{
            "name": "my-instance",
            "settings": {
                "ipConfiguration": {"sslMode": "ALLOW_UNENCRYPTED_AND_ENCRYPTED"}
            }
        }]
    }

    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", True), \
         patch("quirk.scanner.gcp_connector._gcp_build", return_value=mock_service), \
         patch("quirk.scanner.gcp_connector.google") as mock_google:
        mock_google.auth.default.return_value = (MagicMock(), "my-project")
        endpoints = scan_gcp_targets(project_id="my-project")

    sql_eps = [ep for ep in endpoints if ep.protocol == "CLOUD_SQL"]
    assert len(sql_eps) >= 1
    assert any("HIGH" in (ep.cert_pubkey_alg or "") for ep in sql_eps)


@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")
def test_gcp_cloud_sql_encrypted_only():
    """Cloud SQL ENCRYPTED_ONLY sslMode must produce MEDIUM finding."""
    mock_service = _build_gcp_mock_service()
    mock_service.instances.return_value.list.return_value.execute.return_value = {
        "items": [{
            "name": "my-instance",
            "settings": {
                "ipConfiguration": {"sslMode": "ENCRYPTED_ONLY"}
            }
        }]
    }

    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", True), \
         patch("quirk.scanner.gcp_connector._gcp_build", return_value=mock_service), \
         patch("quirk.scanner.gcp_connector.google") as mock_google:
        mock_google.auth.default.return_value = (MagicMock(), "my-project")
        endpoints = scan_gcp_targets(project_id="my-project")

    sql_eps = [ep for ep in endpoints if ep.protocol == "CLOUD_SQL"]
    assert len(sql_eps) >= 1
    assert any("MEDIUM" in (ep.cert_pubkey_alg or "") for ep in sql_eps)


@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")
def test_gcp_cloud_sql_mtls_no_finding():
    """Cloud SQL TRUSTED_CLIENT_CERTIFICATE_REQUIRED sslMode must produce no CLOUD_SQL endpoint."""
    mock_service = _build_gcp_mock_service()
    mock_service.instances.return_value.list.return_value.execute.return_value = {
        "items": [{
            "name": "my-instance",
            "settings": {
                "ipConfiguration": {"sslMode": "TRUSTED_CLIENT_CERTIFICATE_REQUIRED"}
            }
        }]
    }

    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", True), \
         patch("quirk.scanner.gcp_connector._gcp_build", return_value=mock_service), \
         patch("quirk.scanner.gcp_connector.google") as mock_google:
        mock_google.auth.default.return_value = (MagicMock(), "my-project")
        endpoints = scan_gcp_targets(project_id="my-project")

    sql_eps = [ep for ep in endpoints if ep.protocol == "CLOUD_SQL"]
    assert len(sql_eps) == 0


@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")
def test_gcp_cloud_sql_null_ssl_mode():
    """Cloud SQL instance with no sslMode must produce HIGH finding (D-08 missing/null case)."""
    mock_service = _build_gcp_mock_service()
    mock_service.instances.return_value.list.return_value.execute.return_value = {
        "items": [{
            "name": "my-instance",
            "settings": {
                "ipConfiguration": {}  # no sslMode key
            }
        }]
    }

    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", True), \
         patch("quirk.scanner.gcp_connector._gcp_build", return_value=mock_service), \
         patch("quirk.scanner.gcp_connector.google") as mock_google:
        mock_google.auth.default.return_value = (MagicMock(), "my-project")
        endpoints = scan_gcp_targets(project_id="my-project")

    sql_eps = [ep for ep in endpoints if ep.protocol == "CLOUD_SQL"]
    assert len(sql_eps) >= 1
    assert any("HIGH" in (ep.cert_pubkey_alg or "") for ep in sql_eps)


@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")
def test_gcp_gcs_cmek_detection():
    """GCS bucket with defaultKmsKeyName must have cert_pubkey_alg=CMEK; plain bucket must not."""
    mock_service = _build_gcp_mock_service()
    mock_service.buckets.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "name": "cmek-bucket",
                "encryption": {
                    "defaultKmsKeyName": "projects/my-project/locations/us/keyRings/kr/cryptoKeys/ck"
                },
            },
            {
                "name": "default-bucket",
            },
        ]
    }

    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", True), \
         patch("quirk.scanner.gcp_connector._gcp_build", return_value=mock_service), \
         patch("quirk.scanner.gcp_connector.google") as mock_google:
        mock_google.auth.default.return_value = (MagicMock(), "my-project")
        endpoints = scan_gcp_targets(project_id="my-project")

    gcs_eps = [ep for ep in endpoints
               if ep.protocol == "GCP"
               and ep.service_detail == "GCS"
               and ep.cert_pubkey_alg != "GCS-SUMMARY"]
    assert len(gcs_eps) >= 2
    assert any(ep.cert_pubkey_alg == "CMEK" for ep in gcs_eps)
    assert any(ep.cert_pubkey_alg != "CMEK" for ep in gcs_eps)


@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")
def test_gcp_gcs_scan_json_written():
    """Sentinel GCS endpoint must carry gcs_scan_json with full bucket list as JSON array."""
    mock_service = _build_gcp_mock_service()
    mock_service.buckets.return_value.list.return_value.execute.return_value = {
        "items": [
            {"name": "cmek-bucket", "encryption": {"defaultKmsKeyName": "projects/p/kr/ck"}},
            {"name": "default-bucket"},
        ]
    }

    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", True), \
         patch("quirk.scanner.gcp_connector._gcp_build", return_value=mock_service), \
         patch("quirk.scanner.gcp_connector.google") as mock_google:
        mock_google.auth.default.return_value = (MagicMock(), "my-project")
        endpoints = scan_gcp_targets(project_id="my-project")

    sentinel_eps = [ep for ep in endpoints
                    if ep.protocol == "GCP" and ep.cert_pubkey_alg == "GCS-SUMMARY"]
    assert len(sentinel_eps) >= 1
    sentinel = sentinel_eps[0]
    assert sentinel.gcs_scan_json is not None
    bucket_list = json.loads(sentinel.gcs_scan_json)
    assert isinstance(bucket_list, list)
    assert len(bucket_list) == 2


def test_gcp_ensure_columns_idempotent():
    """_ensure_gcp_columns() must be idempotent — calling init_db() twice raises no error."""
    import tempfile
    import os
    from quirk.db import init_db
    from sqlalchemy import inspect as sa_inspect

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_gcp.db")
        # First call: creates DB + migrates
        engine = init_db(db_path)
        # Second call: must not raise
        engine2 = init_db(db_path)
        # Verify gcs_scan_json column exists
        columns = {c["name"] for c in sa_inspect(engine2).get_columns("crypto_endpoints")}
        assert "gcs_scan_json" in columns
