"""Phase 125 — POSTURE-02 RED scaffolds.

POSTURE-02 / CE-04: GCP and AWS connectors swallow per-API IAM errors silently
(logger.v() only). An operator cannot tell which APIs were inaccessible.

Post-fix: when a 403/AccessDenied IAM error occurs at the service level,
a scan_error CryptoEndpoint is emitted so the finding surfaces in the scan report.

RED: scan_error endpoints are NOT currently emitted for IAM errors; the tests
assert scan_error is set and will fail until the fix is applied.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# POSTURE-02a: GCP IAM 403 → scan_error endpoint
# ---------------------------------------------------------------------------

def _make_http_error(status: int = 403, reason: str = "PERMISSION_DENIED"):
    """Minimal HttpError-like exception (google-api-python-client shape)."""
    try:
        from googleapiclient.errors import HttpError
        import io
        resp = MagicMock()
        resp.status = status
        resp.reason = reason
        return HttpError(resp=resp, content=b"Permission denied")
    except ImportError:
        exc = Exception(f"HttpError {status}: {reason}")
        exc.resp = MagicMock()
        exc.resp.status = status
        return exc


def test_gcp_kms_403_emits_scan_error():
    """GCP Cloud KMS 403 → scan_error CryptoEndpoint returned, not silently dropped.

    RED: currently the 403 is caught and logged only; no scan_error endpoint is emitted.
    """
    from quirk.scanner.gcp_connector import _scan_kms

    service = MagicMock()
    service.projects().locations().list().execute.side_effect = _make_http_error(403)

    results = _scan_kms(service, "my-project", logger=None)

    scan_errors = [ep for ep in results if ep.scan_error]
    assert scan_errors, (
        "GCP Cloud KMS 403 (IAM permission denied) must produce a scan_error "
        "CryptoEndpoint. Currently none emitted — POSTURE-02 not yet fixed."
    )
    assert any("iam" in (ep.scan_error or "").lower() or "403" in (ep.scan_error or "") or "permission" in (ep.scan_error or "").lower() for ep in scan_errors), (
        f"scan_error text should reference IAM/403/permission. Got: {[ep.scan_error for ep in scan_errors]}"
    )


def test_gcp_sql_403_emits_scan_error():
    """GCP Cloud SQL 403 → scan_error CryptoEndpoint returned.

    RED: currently silently swallowed.
    """
    from quirk.scanner.gcp_connector import _scan_cloud_sql as _scan_sql

    service = MagicMock()
    service.instances().list().execute.side_effect = _make_http_error(403)

    results = _scan_sql(service, "my-project", logger=None)

    scan_errors = [ep for ep in results if ep.scan_error]
    assert scan_errors, (
        "GCP Cloud SQL 403 (IAM permission denied) must produce a scan_error endpoint. "
        "Currently none emitted — POSTURE-02 not yet fixed."
    )


# ---------------------------------------------------------------------------
# POSTURE-02b: AWS AccessDenied → scan_error endpoint
# ---------------------------------------------------------------------------

def _make_aws_access_denied(service: str = "kms"):
    """Minimal botocore ClientError for AccessDenied."""
    try:
        from botocore.exceptions import ClientError
        return ClientError(
            error_response={"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            operation_name="ListKeys",
        )
    except ImportError:
        exc = Exception(f"ClientError: AccessDeniedException on {service}")
        exc.response = {"Error": {"Code": "AccessDeniedException"}}
        return exc


def test_aws_kms_access_denied_emits_scan_error(tmp_path, monkeypatch):
    """AWS KMS AccessDenied → scan_error CryptoEndpoint returned.

    RED: currently silently swallowed in _scan_kms's except Exception block.
    """
    from quirk.scanner import aws_connector

    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    mock_client.get_paginator.return_value.paginate.side_effect = _make_aws_access_denied("kms")

    results = aws_connector._scan_kms(mock_session, logger=None)

    scan_errors = [ep for ep in results if ep.scan_error]
    assert scan_errors, (
        "AWS KMS AccessDenied must produce a scan_error CryptoEndpoint. "
        "Currently none emitted — POSTURE-02 not yet fixed."
    )
    assert any("iam" in (ep.scan_error or "").lower() or "access" in (ep.scan_error or "").lower() for ep in scan_errors), (
        f"scan_error text should reference IAM/access denied. Got: {[ep.scan_error for ep in scan_errors]}"
    )
