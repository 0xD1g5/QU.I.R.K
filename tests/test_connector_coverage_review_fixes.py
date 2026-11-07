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
