"""Phase 235.3 code review, Part B fixes (orchestration and scoring).

Each test drives a real in-process ``run_scan.main()`` through
``tests/connector_coverage_harness.py`` with the optional-extra flags and the
scanner entry points patched, then reads the persisted ``scan_phase_records``
and ``CryptoEndpoint`` rows. Row-loss findings assert the rows SURVIVE;
double-count findings assert the missing extra is counted exactly once.

The availability of optional packages is patched both at the scanner flag and
at ``quirk.util.optional_extra.find_spec`` so each test gives the same result
with or without the extra installed (local .venv vs CI).
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List

import pytest

import run_scan
from quirk.config import load_config
from quirk.db import get_session
from quirk.models import CryptoEndpoint
from quirk.scanner.target_outcome import (
    OUTCOME_REFUSED,
    OUTCOME_UNREACHABLE,
    TargetOutcomes,
)
from tests import connector_coverage_harness as h

pytestmark = pytest.mark.slow


def _hide_modules(monkeypatch, *names):
    """Make probe_missing_extras see *names* as not installed."""
    import quirk.util.optional_extra as oe

    real = oe.find_spec

    def fake(name, *a, **kw):
        if name in names:
            return None
        return real(name, *a, **kw)

    monkeypatch.setattr(oe, "find_spec", fake)


def _scan(tmp_path, monkeypatch, overrides, extra_argv=()):
    h.scrub_cloud_env(monkeypatch)
    cfg_path = h.build_config(tmp_path, overrides)
    cfg = load_config(cfg_path)
    mp = pytest.MonkeyPatch()
    try:
        mp.chdir(os.path.dirname(os.path.abspath(cfg_path)))
        mp.setattr(sys, "argv", [
            "run_scan.py", "--config", str(cfg_path),
            "--db-path", str(cfg.output.db_path), *extra_argv,
        ])
        run_scan.main()
    finally:
        mp.undo()
    phases = {r["phase_name"]: r for r in h.phase_rows(cfg.output.db_path)}
    with get_session(cfg.output.db_path) as session:
        eps = [
            {"host": e.host, "port": e.port, "protocol": e.protocol,
             "category": e.scan_error_category, "error": e.scan_error,
             "detail": e.service_detail}
            for e in session.query(CryptoEndpoint).all()
        ]
    return phases, eps


def _missing_extra(eps: List[Dict]) -> List[Dict]:
    return [e for e in eps if e["category"] == "missing_extra" and e["error"]]


# ------------------------------------------------------------------ B-CR-01

def _patch_k8s_without_sdk(monkeypatch, eks_rows):
    import quirk.scanner.aws_connector as aws
    import quirk.scanner.k8s_connector as k8s

    monkeypatch.setattr(k8s, "K8S_AVAILABLE", False)
    _hide_modules(monkeypatch, "kubernetes")
    monkeypatch.setattr(aws, "BOTO3_AVAILABLE", True)
    monkeypatch.setattr(
        aws, "_scan_eks_encryption", lambda session, logger, session_start=None: list(eks_rows),
    )


def test_k8s_missing_sdk_keeps_answered_eks_rows(tmp_path, monkeypatch):
    eks_row = CryptoEndpoint(
        host="eks-harness-cluster", port=443, protocol="KUBERNETES",
        service_detail="EKS/kms-envelope",
    )
    _patch_k8s_without_sdk(monkeypatch, [eks_row])
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_k8s": True, "k8s_provider": "eks", "k8s_cluster_name": "harness",
    }})
    assert phases["k8s_scanning"]["status"] == "ran"
    assert [e for e in eps if e["host"] == "eks-harness-cluster"], "EKS row was discarded"
    assert len(_missing_extra(eps)) == 1, _missing_extra(eps)
    assert not any("[k8s]" in (e["error"] or "") for e in eps)


def test_k8s_missing_sdk_skip_counts_extra_once_and_names_cloud(tmp_path, monkeypatch):
    _patch_k8s_without_sdk(monkeypatch, [])
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_k8s": True, "k8s_provider": "gke", "k8s_cluster_name": "harness",
    }})
    row = phases["k8s_scanning"]
    assert row["status"] == "skipped" and row["reason"] == "missing-extra"
    assert "extras: cloud" in row["detail"]
    assert len(_missing_extra(eps)) == 1, _missing_extra(eps)
    assert not any("[k8s]" in (e["error"] or "") for e in eps)
    # K8S-03 path B in-band inaccessible row is forwarded, not deleted.
    assert [e for e in eps if e["error"] == "encryption-config-inaccessible"]


# ------------------------------------------------------------------ B-CR-02

def test_kerberos_missing_impacket_is_missing_extra_counted_once(tmp_path, monkeypatch):
    import quirk.scanner.kerberos_scanner as krb

    monkeypatch.setattr(krb, "IMPACKET_AVAILABLE", False)
    _hide_modules(monkeypatch, "impacket")
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_kerberos": True, "kerberos_targets": ["127.0.0.1"],
    }})
    row = phases["kerberos_scanning"]
    assert row["status"] == "skipped" and row["reason"] == "missing-extra"
    assert "extras: identity" in row["detail"]
    assert len(_missing_extra(eps)) == 1, _missing_extra(eps)
    assert not [e for e in eps if e["category"] == "targets_unreachable"]


def test_codesign_missing_ldap3_is_missing_extra(tmp_path, monkeypatch):
    import quirk.scanner.codesign_scanner as cs

    monkeypatch.setattr(cs, "LDAP3_AVAILABLE", False)
    monkeypatch.setattr(cs, "scan_codesign_from_tls_endpoints", lambda *a, **kw: [])
    phases, eps = _scan(
        tmp_path, monkeypatch,
        {"connectors": {"codesign_targets": ["ldap://127.0.0.1:1"]}},
        extra_argv=("--inventory-code-signing",),
    )
    row = phases["codesign_scanning"]
    assert row["status"] == "skipped" and row["reason"] == "missing-extra"
    assert len(_missing_extra(eps)) == 1, _missing_extra(eps)
    assert not [e for e in eps if e["category"] == "targets_unreachable"]


def test_openapi_missing_extra_is_missing_extra_counted_once(tmp_path, monkeypatch):
    import quirk.scanner.openapi_scanner as oas

    monkeypatch.setattr(oas, "OPENAPI_AVAILABLE", False)
    spec = tmp_path / "spec.yaml"
    spec.write_text("openapi: 3.0.0\ninfo: {title: t, version: '1'}\npaths: {}\n")
    phases, eps = _scan(tmp_path, monkeypatch, {"scan": {"openapi_spec_path": str(spec)}})
    row = phases["openapi_scanning"]
    assert row["status"] == "skipped" and row["reason"] == "missing-extra"
    assert "extras: api" in row["detail"]
    assert len(_missing_extra(eps)) == 1, _missing_extra(eps)
    assert not [e for e in eps if e["category"] == "targets_unreachable"]


def test_db_only_uninstalled_driver_targets_is_missing_extra(tmp_path, monkeypatch):
    import quirk.scanner.db_connector as db

    monkeypatch.setattr(db, "PSYCOPG2_AVAILABLE", True)
    monkeypatch.setattr(db, "PYMYSQL_AVAILABLE", False)
    _hide_modules(monkeypatch, "pymysql")
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_db": True, "mysql_targets": ["127.0.0.1:1"],
    }})
    row = phases["db_scanning"]
    assert row["status"] == "skipped" and row["reason"] == "missing-extra"
    assert len(_missing_extra(eps)) == 1, _missing_extra(eps)
    assert not [e for e in eps if e["category"] == "targets_unreachable"]


def test_classifier_empty_expected_set_is_not_failed():
    rec = run_scan._PhaseRecorder()
    eps: list = []
    result = run_scan._classify_connector_outcomes(
        "x_scanner", TargetOutcomes([]), [], eps, rec,
    )
    assert result is run_scan._PHASE_SKIPPED
    assert rec._pending_reason == "no-eligible-targets"
    assert not [e for e in eps if e.scan_error_category == "targets_unreachable"]


# ------------------------------------------------------------------ A-WR-03

def _hide_run_scan_modules(monkeypatch, *names):
    real = run_scan._module_available
    monkeypatch.setattr(
        run_scan, "_module_available", lambda n: False if n in names else real(n),
    )


def test_azure_subscription_without_network_sdk_is_missing_extra(tmp_path, monkeypatch):
    _hide_run_scan_modules(monkeypatch, "azure.mgmt.network")
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_azure": True, "azure_subscription_id": "00000000-harness",
    }})
    row = phases["azure_scanning"]
    assert row["status"] == "skipped" and row["reason"] == "missing-extra"
    assert len(_missing_extra(eps)) == 1, _missing_extra(eps)
    assert not [e for e in eps if e["category"] == "targets_unreachable"]


def test_azure_keyvault_answered_network_sdk_missing_no_unanswered_row(tmp_path, monkeypatch):
    import quirk.scanner.azure_connector as az

    _hide_run_scan_modules(monkeypatch, "azure.mgmt.network")

    def fake_kv(credential, vault_url, logger, *, outcomes=None):
        outcomes.answered(vault_url)
        return []

    monkeypatch.setattr(az, "_scan_keyvault_keys", fake_kv)
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_azure": True, "azure_subscription_id": "00000000-harness",
        "azure_keyvault_urls": ["https://harness.vault.azure.net"],
    }})
    assert phases["azure_scanning"]["status"] == "ran"
    assert not [e for e in eps if e["category"] == "target_unanswered"]
    assert len(_missing_extra(eps)) == 1, _missing_extra(eps)


def test_blob_without_storage_sdk_is_missing_extra(tmp_path, monkeypatch):
    _hide_run_scan_modules(monkeypatch, "azure.mgmt.storage")
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_blob": True, "azure_subscription_id": "00000000-harness",
    }})
    row = phases["blob_scanning"]
    assert row["status"] == "skipped" and row["reason"] == "missing-extra"
    assert "extras: cloud" in row["detail"]
    assert len(_missing_extra(eps)) == 1, _missing_extra(eps)


# ------------------------------------------------------------------ B-CR-03

def _patch_broker(monkeypatch, kafka=(), rabbit=(), redis=()):
    import quirk.scanner.broker_scanner as bs

    for flag in ("SSLYZE_AVAILABLE", "KAFKA_AVAILABLE", "REDIS_AVAILABLE"):
        monkeypatch.setattr(bs, flag, True)
    monkeypatch.setattr(run_scan, "scan_kafka_targets", lambda **kw: list(kafka))
    monkeypatch.setattr(run_scan, "scan_rabbitmq_targets", lambda **kw: list(rabbit))
    monkeypatch.setattr(run_scan, "scan_redis_targets", lambda **kw: list(redis))


_BROKER_CFG = {"connectors": {"enable_broker": True, "broker_targets": ["127.0.0.1:9092"]}}


def test_broker_skip_forwards_driver_in_band_error_rows(tmp_path, monkeypatch):
    err = CryptoEndpoint(
        host="127.0.0.1", port=6380, protocol="REDIS", scan_error="harness-redis-error",
    )
    _patch_broker(monkeypatch, redis=[err])
    phases, eps = _scan(tmp_path, monkeypatch, _BROKER_CFG)
    assert phases["broker_scanning"]["status"] == "skipped"
    assert [e for e in eps if e["error"] == "harness-redis-error"], "driver error row dropped"


# ------------------------------------------------------------------ B-WR-01

def test_broker_config_advisory_does_not_count_as_answered(tmp_path, monkeypatch):
    from quirk.scanner.broker_scanner import ADVISORY_BROKER_CLEARTEXT

    adv = CryptoEndpoint(
        host="127.0.0.1", port=15672, protocol="ADVISORY",
        service_detail=ADVISORY_BROKER_CLEARTEXT, severity="HIGH",
        scan_error_category="config",
    )
    _patch_broker(monkeypatch, rabbit=[adv])
    phases, eps = _scan(tmp_path, monkeypatch, _BROKER_CFG)
    row = phases["broker_scanning"]
    assert row["status"] == "skipped" and row["reason"] == "failed"
    # The HIGH config advisory itself is still persisted.
    assert [e for e in eps if e["detail"] == ADVISORY_BROKER_CLEARTEXT]


# ------------------------------------------------------------------ B-WR-02

def test_skip_detail_counts_only_the_chosen_kind():
    o = TargetOutcomes(["a", "b", "c"])
    o.record("a", OUTCOME_REFUSED, "loopback")
    o.record("b", OUTCOME_UNREACHABLE, "ConnectError")
    o.record("c", OUTCOME_UNREACHABLE, "ConnectError")
    rec = run_scan._PhaseRecorder()
    run_scan._classify_connector_outcomes("x_scanner", o, [], [], rec)
    d = rec._pending_detail
    assert d.startswith("1 of 3 targets were refused by the internal-target guard")
    assert "2 more did not answer for other reasons" in d


# ------------------------------------------------------------------ B-WR-03

def test_codesign_tls_eku_rows_with_ldap_unanswered_is_ran_without_skip_advisory(
    tmp_path, monkeypatch,
):
    import quirk.scanner.codesign_scanner as cs

    tls_row = CryptoEndpoint(host="eku-harness", port=443, protocol="CODE_SIGNING")

    def fake_ldap(targets, timeout=10, logger=None, session_start=None, *,
                  search_base=None, outcomes=None):
        for t in targets:
            outcomes.record(t, OUTCOME_UNREACHABLE, "harness down")
        return []

    monkeypatch.setattr(cs, "scan_codesign_from_ldap", fake_ldap)
    monkeypatch.setattr(cs, "scan_codesign_from_tls_endpoints", lambda *a, **kw: [tls_row])
    phases, eps = _scan(
        tmp_path, monkeypatch,
        {"connectors": {"codesign_targets": ["ldap://127.0.0.1:1"]}},
        extra_argv=("--inventory-code-signing",),
    )
    assert phases["codesign_scanning"]["status"] == "ran"
    assert not [
        e for e in eps
        if e["host"] == "codesign_scanner" and e["category"] == "targets_unreachable"
    ]
    assert [e for e in eps if e["category"] == "target_unanswered"]
    assert [e for e in eps if e["host"] == "eku-harness"]


# ------------------------------------------------------------------ B-WR-04

def test_k8s_unset_provider_is_not_missing_credentials(tmp_path, monkeypatch):
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_k8s": True, "k8s_provider": "",
    }})
    row = phases["k8s_scanning"]
    assert row["status"] == "skipped"
    assert row["reason"] == "no-eligible-targets"
    assert "k8s_provider" in row["detail"]
    assert not [e for e in eps if e["category"] == "missing_credentials"]
    # The K8S-03 path A inaccessible row is still persisted.
    assert [e for e in eps if e["error"] == "encryption-config-inaccessible"]


# ------------------------------------------------------------------ B-WR-05

def test_s3_bad_profile_is_missing_credentials_not_failed(tmp_path, monkeypatch):
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_s3": True, "aws_profile": "quirk-harness-no-such-profile",
    }})
    row = phases["s3_scanning"]
    assert row["status"] == "skipped"
    assert row["reason"] == "missing-credentials"
    assert not [e for e in eps if e["category"] == "exception"]


def test_eks_bad_profile_records_missing_credentials(tmp_path, monkeypatch):
    import quirk.scanner.aws_connector as aws
    import quirk.scanner.k8s_connector as k8s

    def fake_k8s(**kw):
        kw["outcomes"].answered(kw["outcomes"].sole_target())
        return []

    monkeypatch.setattr(k8s, "scan_k8s_targets", fake_k8s)
    monkeypatch.setattr(aws, "BOTO3_AVAILABLE", True)
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {
        "enable_k8s": True, "k8s_provider": "eks", "k8s_cluster_name": "harness",
        "aws_profile": "quirk-harness-no-such-profile",
    }})
    assert phases["k8s_scanning"]["status"] == "ran"
    unanswered = [e for e in eps if e["category"] == "target_unanswered"]
    assert len(unanswered) == 1
    assert "missing_credentials" in unanswered[0]["error"], unanswered[0]["error"]
