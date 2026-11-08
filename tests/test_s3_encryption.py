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


# ---------------------------------------------------------------------------
# Phase 235.3 D-05: per-target outcome recording (hermetic: MagicMock sessions)
# ---------------------------------------------------------------------------

def _s3_session(list_buckets=None, side_effect=None):
    client = MagicMock()
    if side_effect is not None:
        client.list_buckets.side_effect = side_effect
    else:
        client.list_buckets.return_value = list_buckets
    session = MagicMock()
    session.client.return_value = client
    return session, client


def _s3_outcomes(label="s3:closure-label"):
    from quirk.scanner.target_outcome import TargetOutcomes
    return TargetOutcomes([label])


def _only(sink):
    res = sink.resolved()
    assert len(res) == 1
    return res[0]


def test_s3_outcome_no_credentials_is_missing_credentials():
    from botocore.exceptions import NoCredentialsError
    from quirk.scanner.aws_connector import _scan_s3_encryption
    session, _ = _s3_session(side_effect=NoCredentialsError())
    sink = _s3_outcomes()
    assert _scan_s3_encryption(session, None, outcomes=sink) == []
    assert _only(sink).kind == "missing_credentials"


@pytest.mark.parametrize("code", ["InvalidAccessKeyId", "SignatureDoesNotMatch"])
def test_s3_outcome_rejected_credentials_is_auth_failed(code):
    from quirk.scanner.aws_connector import _scan_s3_encryption
    session, _ = _s3_session(side_effect=_make_client_error(code))
    sink = _s3_outcomes()
    _scan_s3_encryption(session, None, outcomes=sink)
    assert _only(sink).kind == "auth_failed"


def test_s3_outcome_endpoint_unreachable():
    from botocore.exceptions import EndpointConnectionError
    from quirk.scanner.aws_connector import _scan_s3_encryption
    session, _ = _s3_session(side_effect=EndpointConnectionError(endpoint_url="http://x"))
    sink = _s3_outcomes()
    _scan_s3_encryption(session, None, outcomes=sink)
    assert _only(sink).kind == "unreachable"


def test_s3_outcome_empty_account_is_answered_and_label_comes_from_sink():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    session, _ = _s3_session({"Buckets": []})
    sink = _s3_outcomes("s3:closure-label")
    assert _scan_s3_encryption(session, None, outcomes=sink) == []
    res = sink.resolved()
    assert [(o.target, o.kind) for o in res] == [("s3:closure-label", "answered")]


def test_s3_outcome_bucket_error_not_reclassified():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    session, client = _s3_session({"Buckets": [{"Name": "a"}, {"Name": "b"}]})

    def _enc(Bucket):
        if Bucket == "a":
            raise _make_client_error("AccessDenied")
        return {"ServerSideEncryptionConfiguration": {"Rules": [
            {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}}

    client.get_bucket_encryption.side_effect = _enc
    sink = _s3_outcomes()
    rows = _scan_s3_encryption(session, None, outcomes=sink)
    assert len(rows) == 1
    assert _only(sink).kind == "answered"


def test_s3_outcome_list_buckets_access_denied_names_iam():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    session, _ = _s3_session(side_effect=_make_client_error("AccessDenied"))
    sink = _s3_outcomes()
    _scan_s3_encryption(session, None, outcomes=sink)
    o = _only(sink)
    assert o.kind == "auth_failed"
    assert "lack a required IAM permission" in o.detail


def test_s3_outcome_detail_does_not_leak_secret_key():
    from botocore.exceptions import ClientError
    from quirk.scanner.aws_connector import _scan_s3_encryption
    exc = ClientError(
        {"Error": {"Code": "InvalidAccessKeyId",
                   "Message": "secret wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY12 is bad"}}, "ListBuckets")
    session, _ = _s3_session(side_effect=exc)
    sink = _s3_outcomes()
    _scan_s3_encryption(session, None, outcomes=sink)
    assert "wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY12" not in _only(sink).detail


def test_s3_outcome_none_sink_unchanged():
    from botocore.exceptions import NoCredentialsError
    from quirk.scanner.aws_connector import _scan_s3_encryption
    session, _ = _s3_session(side_effect=NoCredentialsError())
    assert _scan_s3_encryption(session, None) == []
    session, _ = _s3_session({"Buckets": []})
    assert _scan_s3_encryption(session, None) == []


def test_s3_outcome_contract_violation_propagates():
    from quirk.scanner.aws_connector import _scan_s3_encryption
    from quirk.scanner.target_outcome import TargetOutcomeContractError, TargetOutcomes
    session, _ = _s3_session({"Buckets": []})
    # two-target sink: sole_target() cannot be satisfied
    sink = TargetOutcomes(["x", "y"])
    with pytest.raises(TargetOutcomeContractError):
        _scan_s3_encryption(session, None, outcomes=sink)
