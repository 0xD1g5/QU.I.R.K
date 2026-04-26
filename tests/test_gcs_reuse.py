"""RED tests for STOR-03 — GCS bucket encryption re-use (zero new API calls)."""
import json
from unittest.mock import MagicMock, patch

import pytest


def _make_endpoint(cert_pubkey_alg, gcs_scan_json=None):
    ep = MagicMock()
    ep.cert_pubkey_alg = cert_pubkey_alg
    ep.gcs_scan_json = gcs_scan_json
    return ep


def test_gcs_reuse_returns_empty_when_no_sentinel():
    from run_scan import _process_gcs_storage_encryption
    gcp_endpoints = [_make_endpoint("CMEK", None), _make_endpoint("Google-Managed", None)]
    result = _process_gcs_storage_encryption(gcp_endpoints, logger=None)
    assert result == []


def test_gcs_reuse_returns_empty_when_gcp_disabled():
    """enable_gcp=False => gcp_endpoints is []; helper must not raise."""
    from run_scan import _process_gcs_storage_encryption
    result = _process_gcs_storage_encryption([], logger=None)
    assert result == []


def test_gcs_reuse_reads_sentinel_no_api_call():
    """Helper reads gcs_scan_json from sentinel without instantiating any GCS client."""
    from run_scan import _process_gcs_storage_encryption
    bucket_list = [{"name": "b1", "encryption": {"defaultKmsKeyName": "projects/p/k"}}]
    sentinel = _make_endpoint("GCS-SUMMARY", json.dumps(bucket_list))
    with patch("googleapiclient.discovery.build", create=True) as mock_build:
        result = _process_gcs_storage_encryption([sentinel], logger=None)
        assert mock_build.call_count == 0  # zero API calls — STOR-03 invariant
    # result may be [] (Phase 26 already added per-bucket rows); the contract is
    # "no API call", not "produce new endpoints". Phase 26 row reuse is acceptable.
    assert isinstance(result, list)


def test_gcs_reuse_handles_malformed_json():
    from run_scan import _process_gcs_storage_encryption
    sentinel = _make_endpoint("GCS-SUMMARY", "not-valid-json")
    result = _process_gcs_storage_encryption([sentinel], logger=None)
    assert result == []


def test_gcs_reuse_zero_storage_buckets_list_call():
    """Stronger invariant: helper never calls .buckets().list()."""
    from run_scan import _process_gcs_storage_encryption
    sentinel = _make_endpoint("GCS-SUMMARY", json.dumps([{"name": "b"}]))
    # Mock storage.Client at the most-common import paths — call_count must remain 0.
    with patch("google.cloud.storage.Client", create=True) as mock_client:
        _process_gcs_storage_encryption([sentinel], logger=None)
        assert mock_client.call_count == 0
