"""RED tests for STOR-01 — S3 bucket encryption severity ladder.

These tests fail until quirk/scanner/aws_connector.py implements _scan_s3_encryption
in Plan 02. Mocks boto3 to avoid live AWS credentials.
"""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def _make_client_error(code: str):
    from botocore.exceptions import ClientError
    return ClientError({"Error": {"Code": code}}, "GetBucketEncryption")


def test_s3_unavailable_returns_empty():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    with patch("quirk.scanner.aws_connector.BOTO3_AVAILABLE", False):
        result = _scan_s3_encryption(session=MagicMock(), logger=None)
        assert result == []


def test_s3_no_encryption_config_error():
    """ServerSideEncryptionConfigurationNotFoundError MUST map to HIGH/S3/unencrypted."""
    from quirk.scanner.aws_connector import _scan_s3_encryption
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": [{"Name": "my-bucket"}]}
    mock_client.get_bucket_encryption.side_effect = _make_client_error(
        "ServerSideEncryptionConfigurationNotFoundError"
    )
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    result = _scan_s3_encryption(session=mock_session, logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.protocol == "S3"
    assert "S3/unencrypted" in ep.service_detail
    assert ep.severity == "HIGH"


def test_s3_sse_s3_no_finding():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": [{"Name": "encrypted"}]}
    mock_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    result = _scan_s3_encryption(session=mock_session, logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.service_detail == "S3/sse-s3"
    assert getattr(ep, "severity", None) is None


def test_s3_sse_kms_aws_managed():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": [{"Name": "kms-aws"}]}
    mock_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                    "KMSMasterKeyID": "alias/aws/s3",
                }
            }]
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    result = _scan_s3_encryption(session=mock_session, logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.service_detail == "S3/sse-kms-aws"
    assert ep.severity == "MEDIUM"


def test_s3_sse_kms_aws_managed_absent_keyid():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": [{"Name": "kms-no-id"}]}
    mock_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms"}}]
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    result = _scan_s3_encryption(session=mock_session, logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.service_detail == "S3/sse-kms-aws"
    assert ep.severity == "MEDIUM"


def test_s3_sse_kms_cmk_no_finding():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": [{"Name": "kms-cmk"}]}
    mock_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                    "KMSMasterKeyID": "arn:aws:kms:us-east-1:111122223333:key/abcd-efgh",
                }
            }]
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    result = _scan_s3_encryption(session=mock_session, logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.service_detail == "S3/sse-kms-cmk"
    assert getattr(ep, "severity", None) is None


def test_s3_parallel_scan_processes_all_buckets():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {
        "Buckets": [{"Name": f"b{i}"} for i in range(3)]
    }
    mock_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    result = _scan_s3_encryption(session=mock_session, logger=None)
    assert len(result) == 3
    assert mock_client.get_bucket_encryption.call_count == 3


def test_s3_session_start_propagates():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    fixed = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": [{"Name": "b1"}]}
    mock_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    result = _scan_s3_encryption(session=mock_session, logger=None, session_start=fixed)
    assert len(result) == 1
    # scanned_at must equal fixed (with tzinfo stripped) — proving session_start was used
    assert result[0].scanned_at == fixed.replace(tzinfo=None)


def test_s3_dat_scan_json_populated():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": [{"Name": "logbucket"}]}
    mock_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    result = _scan_s3_encryption(session=mock_session, logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.dat_scan_json is not None
    parsed = json.loads(ep.dat_scan_json)
    assert parsed.get("bucket") == "logbucket"


def test_s3_endpoint_url_passed_to_client():
    """When endpoint_url provided (MinIO override), boto3 client must be created with it."""
    from quirk.scanner.aws_connector import _scan_s3_encryption
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": []}
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    _scan_s3_encryption(session=mock_session, logger=None, endpoint_url="http://minio:9000")
    # Verify session.client called with endpoint_url
    call_kwargs = mock_session.client.call_args.kwargs
    assert call_kwargs.get("endpoint_url") == "http://minio:9000"
