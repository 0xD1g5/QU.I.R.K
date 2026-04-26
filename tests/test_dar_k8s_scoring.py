"""RED→GREEN tests for Phase 29 dar_k8s_* counters, weights, and impacts.

Phase 29 Plan 01 seeded connector tests (test_k8s_connector.py) but not the intelligence-
layer counter tests; this file fills that gap and turns GREEN once Plan 03 Task 1 edits land.
"""
from __future__ import annotations
from datetime import datetime, timezone

import pytest

from quirk.intelligence.evidence import _PROTOCOL_KEYS, build_evidence_summary
from quirk.intelligence.scoring import SCORE_WEIGHTS, compute_readiness_score
from quirk.models import CryptoEndpoint


def _ep(
    service_detail: str,
    severity: str | None = None,
    scan_error: str | None = None,
) -> CryptoEndpoint:
    return CryptoEndpoint(
        host="cluster-test",
        port=443,
        protocol="KUBERNETES",
        service_detail=service_detail,
        severity=severity,
        scan_error=scan_error,
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )


def test_protocol_keys_includes_kubernetes():
    assert "KUBERNETES" in _PROTOCOL_KEYS


def test_dar_k8s_unencrypted_count_eks():
    endpoints = [_ep("EKS/unencrypted", severity="HIGH")]
    summary = build_evidence_summary(endpoints)
    assert summary["dar_k8s_unencrypted_count"] == 1
    assert summary["dar_k8s_inaccessible_count"] == 0


def test_dar_k8s_unencrypted_count_gke():
    endpoints = [_ep("GKE/unencrypted", severity="HIGH")]
    summary = build_evidence_summary(endpoints)
    assert summary["dar_k8s_unencrypted_count"] == 1


def test_dar_k8s_inaccessible_count_aks_platform_managed():
    endpoints = [_ep("AKS/platform-managed", severity="MEDIUM")]
    summary = build_evidence_summary(endpoints)
    assert summary["dar_k8s_inaccessible_count"] == 1
    assert summary["dar_k8s_unencrypted_count"] == 0


def test_dar_k8s_inaccessible_count_explicit_inaccessible():
    endpoints = [_ep("encryption-config-inaccessible", severity="MEDIUM")]
    summary = build_evidence_summary(endpoints)
    assert summary["dar_k8s_inaccessible_count"] == 1


def test_dar_k8s_inaccessible_count_rbac_403():
    # Live shape: connector emits scan_error='insufficient-rbac-privileges' with a
    # remediation-text service_detail (NOT the substring 'rbac-403'). This used to be
    # a false-green; CR-01 forces evidence.py to count the scan_error field.
    endpoints = [_ep(
        "Remediation: RBAC role requires get,list on secrets in namespace 'default'",
        severity=None,
        scan_error="insufficient-rbac-privileges",
    )]
    summary = build_evidence_summary(endpoints)
    assert summary["dar_k8s_inaccessible_count"] == 1
    assert summary["dar_k8s_unencrypted_count"] == 0


def test_dar_k8s_no_finding_paths_no_increment():
    endpoints = [
        _ep("EKS/encrypted", severity=None),
        _ep("GKE/encrypted", severity=None),
        _ep("AKS/kv-kms", severity=None),
    ]
    summary = build_evidence_summary(endpoints)
    assert summary["dar_k8s_unencrypted_count"] == 0
    assert summary["dar_k8s_inaccessible_count"] == 0


def test_dar_k8s_secret_types_summary_neutral():
    endpoints = [_ep("secret-types-summary", severity=None)]
    summary = build_evidence_summary(endpoints)
    assert summary["dar_k8s_unencrypted_count"] == 0
    assert summary["dar_k8s_inaccessible_count"] == 0


def test_dar_k8s_ratio_keys_present():
    endpoints = [_ep("EKS/unencrypted", severity="HIGH")]
    summary = build_evidence_summary(endpoints)
    assert "dar_k8s_unencrypted_ratio" in summary
    assert "dar_k8s_inaccessible_ratio" in summary


def test_score_weights_dar_k8s_values():
    assert SCORE_WEIGHTS["dar_k8s_unencrypted_ratio"] == 10.0
    assert SCORE_WEIGHTS["dar_k8s_inaccessible_ratio"] == 4.0


def test_dar_score_includes_k8s_drivers():
    endpoints = [
        _ep("EKS/unencrypted", severity="HIGH"),
        _ep("AKS/platform-managed", severity="MEDIUM"),
    ]
    summary = build_evidence_summary(endpoints)
    score = compute_readiness_score(summary, profile="balanced")
    labels = " ".join(d[0] if isinstance(d, (list, tuple)) else str(d)
                      for d in score.get("drivers", []))
    assert "Kubernetes" in labels or "etcd" in labels


def test_dar_k8s_unencrypted_ratio_applied():
    # 5 unencrypted clusters out of 5 endpoints → max ratio
    endpoints = [_ep("EKS/unencrypted", severity="HIGH") for _ in range(5)]
    summary = build_evidence_summary(endpoints)
    score = compute_readiness_score(summary, profile="balanced")
    # data_at_rest subscore should be measurably reduced
    dar_subscore = score.get("subscores", {}).get("data_at_rest", 100)
    assert dar_subscore < 100, f"dar subscore expected < 100, got {dar_subscore}"
