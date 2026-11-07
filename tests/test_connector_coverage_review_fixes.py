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
