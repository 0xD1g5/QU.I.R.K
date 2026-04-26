"""RED tests for Phase 28 dar_storage_* evidence counters and scoring weights (D-09, D-10)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


def _ep(protocol: str, service_detail: str):
    ep = MagicMock()
    ep.protocol = protocol
    ep.service_detail = service_detail
    ep.scanned_at = datetime(2026, 4, 25, tzinfo=timezone.utc).replace(tzinfo=None)
    # All other attributes default to None / 0 via MagicMock; pin a few that build_evidence_summary reads
    ep.scan_error = None
    ep.tls_blocker_reason = ""
    ep.cert_pubkey_alg = ""
    ep.cert_pubkey_size = None
    ep.cert_not_after = None
    ep.cert_subject = ""
    ep.cert_issuer = ""
    ep.tls_supported_versions = ""
    ep.host = "test-host"
    ep.port = 0
    return ep


def test_protocol_keys_includes_storage_protocols():
    from quirk.intelligence.evidence import _PROTOCOL_KEYS
    assert "S3" in _PROTOCOL_KEYS
    assert "AZURE_BLOB" in _PROTOCOL_KEYS


def test_dar_storage_unencrypted_count_s3():
    from quirk.intelligence.evidence import build_evidence_summary
    endpoints = [_ep("S3", "S3/unencrypted")]
    result = build_evidence_summary(endpoints)
    assert result["dar_storage_unencrypted_count"] == 1
    assert result["dar_storage_aws_managed_count"] == 0


def test_dar_storage_aws_managed_count_s3():
    from quirk.intelligence.evidence import build_evidence_summary
    endpoints = [_ep("S3", "S3/sse-kms-aws")]
    result = build_evidence_summary(endpoints)
    assert result["dar_storage_aws_managed_count"] == 1
    assert result["dar_storage_unencrypted_count"] == 0


def test_dar_storage_blob_platform_managed_counts():
    from quirk.intelligence.evidence import build_evidence_summary
    endpoints = [_ep("AZURE_BLOB", "BLOB/platform-managed")]
    result = build_evidence_summary(endpoints)
    # platform-managed counts as aws_managed (compliance gap), NOT unencrypted (which is HIGH)
    assert result["dar_storage_aws_managed_count"] == 1
    assert result["dar_storage_unencrypted_count"] == 0


def test_dar_storage_no_finding_paths_no_increment():
    from quirk.intelligence.evidence import build_evidence_summary
    endpoints = [
        _ep("S3", "S3/sse-s3"),
        _ep("S3", "S3/sse-kms-cmk"),
        _ep("AZURE_BLOB", "BLOB/cmk"),
    ]
    result = build_evidence_summary(endpoints)
    assert result["dar_storage_unencrypted_count"] == 0
    assert result["dar_storage_aws_managed_count"] == 0


def test_dar_storage_ratio_keys_present():
    from quirk.intelligence.evidence import build_evidence_summary
    endpoints = [_ep("S3", "S3/unencrypted")]
    result = build_evidence_summary(endpoints)
    assert "dar_storage_unencrypted_ratio" in result
    assert "dar_storage_aws_managed_ratio" in result
    assert isinstance(result["dar_storage_unencrypted_ratio"], float)
    assert result["dar_storage_unencrypted_ratio"] == 1.0  # 1 of 1 endpoint


def test_score_weights_dar_storage_values():
    from quirk.intelligence.scoring import SCORE_WEIGHTS
    assert SCORE_WEIGHTS["dar_storage_unencrypted_ratio"] == 12.0
    assert SCORE_WEIGHTS["dar_storage_aws_managed_ratio"] == 4.0


def test_dar_score_includes_storage_drivers():
    from quirk.intelligence.scoring import compute_readiness_score
    evidence = {
        "totals": {"endpoints": 4, "findings": 1},
        "dar_storage_unencrypted_count": 2,
        "dar_storage_aws_managed_count": 1,
        "dar_db_plaintext_count": 0,
        "dar_db_weak_ssl_count": 0,
    }
    result = compute_readiness_score(evidence, profile="balanced")
    # The dar subscore should include impacts from object storage
    drivers = result.get("drivers", [])
    labels = [d.get("reason", "") for d in drivers]
    # At least one storage-related driver appears
    assert any("storage" in lbl.lower() or "Object storage" in lbl for lbl in labels)


def test_dar_storage_unencrypted_ratio_applied():
    """When unencrypted ratio is high, dar subscore must be lower than baseline (no findings)."""
    from quirk.intelligence.scoring import compute_readiness_score
    baseline_evidence = {
        "totals": {"endpoints": 4, "findings": 0},
        "dar_storage_unencrypted_count": 0,
        "dar_storage_aws_managed_count": 0,
        "dar_db_plaintext_count": 0,
        "dar_db_weak_ssl_count": 0,
    }
    bad_evidence = dict(baseline_evidence)
    bad_evidence["dar_storage_unencrypted_count"] = 4  # 100% unencrypted
    baseline = compute_readiness_score(baseline_evidence, profile="balanced")
    bad = compute_readiness_score(bad_evidence, profile="balanced")
    assert bad["subscores"]["data_at_rest"] < baseline["subscores"]["data_at_rest"]
