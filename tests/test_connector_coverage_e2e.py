"""Phase 235.3 plan 21: in-process e2e proof of the D-03 coverage rule.

Real ``run_scan.main()`` runs (via ``tests/connector_coverage_harness.py``)
reproduce the 2026-11-05 findings: a connector that saw nothing records
``skipped`` with a named reason plus one ADVISORY row; an answered-empty
connector stays ``ran`` with no phantom row; a partial run stays ``ran`` with
exactly one per-target ``target_unanswered`` ERROR row.

Plan 14 owns the paired-score proof and plan 15 the source-derived backstop;
this module covers the concrete repros only. Loopback stubs, dummy credentials
and a scrubbed cloud env keep every run hermetic.
"""
from __future__ import annotations

from typing import Dict, List

import pytest

from quirk.config import load_config
from quirk.db import get_session
from quirk.models import CryptoEndpoint
from tests import connector_coverage_harness as h

pytestmark = pytest.mark.slow

_DUMMY_AWS = {"AWS_ACCESS_KEY_ID": "AKIAHARNESSDUMMY", "AWS_SECRET_ACCESS_KEY": "dummy-secret"}


def _scan(tmp_path, monkeypatch, overrides, env=None):
    """Run one scan; return (phase rows by name, CryptoEndpoint row dicts)."""
    h.scrub_cloud_env(monkeypatch)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    cfg_path = h.build_config(tmp_path, overrides)
    cfg = load_config(cfg_path)
    before = h.quirk_output_snapshot()
    h.run_scan_in_process(cfg_path, cfg.output.db_path)
    assert h.quirk_output_snapshot() == before, "scan wrote into the repo's quirk-output"
    phases = {r["phase_name"]: r for r in h.phase_rows(cfg.output.db_path)}
    with get_session(cfg.output.db_path) as session:
        eps = [
            {"host": e.host, "protocol": e.protocol, "category": e.scan_error_category,
             "error": e.scan_error}
            for e in session.query(CryptoEndpoint).all()
        ]
    return phases, eps


def _rows(eps: List[Dict], protocol: str, host: str = None) -> List[Dict]:
    return [e for e in eps if e["protocol"] == protocol and (host is None or e["host"] == host)]


# ---------------------------------------------------------------- Task 1 (SC1)

@pytest.fixture(scope="module")
def refused_scan(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("refused")
    mp = pytest.MonkeyPatch()
    try:
        return _scan(tmp, mp, {
            "connectors": {
                "enable_jwt": True, "jwt_targets": ["http://127.0.0.1:1"],
                "enable_saml": True,
                "saml_targets": ["http://127.0.0.1:1/simplesaml/saml2/idp/metadata.php"],
            },
            "security": {"allow_internal_targets": False},
        })
    finally:
        mp.undo()


@pytest.mark.parametrize("phase,label", [
    ("jwt_scanning", "jwt_scanner"), ("saml_scanning", "saml_scanner"),
])
def test_refused_targets_skip_with_internal_target_refused(refused_scan, phase, label):
    phases, eps = refused_scan
    assert phases[phase]["status"] == "skipped"
    assert phases[phase]["reason"] == "internal-target-refused"
    assert "security.allow_internal_targets" in phases[phase]["detail"]
    adv = _rows(eps, "ADVISORY", label)
    assert len(adv) == 1
    assert adv[0]["category"] == "internal_target_refused"
    assert "security.allow_internal_targets" in adv[0]["error"]


def test_s3_without_credentials_skips_missing_credentials(tmp_path, monkeypatch):
    phases, eps = _scan(tmp_path, monkeypatch, {"connectors": {"enable_s3": True}})
    assert phases["s3_scanning"]["status"] == "skipped"
    assert phases["s3_scanning"]["reason"] == "missing-credentials"
    adv = _rows(eps, "ADVISORY", "s3_connector")
    assert len(adv) == 1 and adv[0]["category"] == "missing_credentials"


def test_s3_rejected_credentials_skip_auth_failed(tmp_path, monkeypatch):
    with h.s3_stub(status=403, code="InvalidAccessKeyId") as url:
        phases, eps = _scan(
            tmp_path, monkeypatch,
            {"connectors": {"enable_s3": True, "aws_endpoint_url": url}},
            env=_DUMMY_AWS,
        )
    assert phases["s3_scanning"]["status"] == "skipped"
    assert phases["s3_scanning"]["reason"] == "auth-failed"
    adv = _rows(eps, "ADVISORY", "s3_connector")
    assert len(adv) == 1 and adv[0]["category"] == "auth_failed"


def test_unreachable_jwt_target_skips_failed(tmp_path, monkeypatch):
    url = f"http://127.0.0.1:{h.closed_port()}"
    phases, eps = _scan(tmp_path, monkeypatch, {
        "connectors": {"enable_jwt": True, "jwt_targets": [url]},
        "security": {"allow_internal_targets": True},
    })
    assert phases["jwt_scanning"]["status"] == "skipped"
    assert phases["jwt_scanning"]["reason"] == "failed"
    adv = _rows(eps, "ADVISORY", "jwt_scanner")
    assert len(adv) == 1 and adv[0]["category"] == "targets_unreachable"


# ------------------------------------------------------- Task 2 (D-03 / SC2)

def test_jwt_answered_empty_stays_ran_with_no_phantom_row(tmp_path, monkeypatch):
    with h.jwks_stub('{"keys": []}') as base:
        phases, eps = _scan(tmp_path, monkeypatch, {
            "connectors": {"enable_jwt": True, "jwt_targets": [base]},
            "security": {"allow_internal_targets": True},
        })
    assert phases["jwt_scanning"]["status"] == "ran"
    assert _rows(eps, "JWT") == []
    assert _rows(eps, "ERROR", base) == []
    assert [e for e in eps if e["category"] == "target_unanswered"] == []
    assert _rows(eps, "ADVISORY", "jwt_scanner") == []


def test_s3_answered_empty_stays_ran_with_no_target_unanswered_row(tmp_path, monkeypatch):
    with h.s3_stub() as url:
        phases, eps = _scan(
            tmp_path, monkeypatch,
            {"connectors": {"enable_s3": True, "aws_endpoint_url": url}},
            env=_DUMMY_AWS,
        )
    assert phases["s3_scanning"]["status"] == "ran"
    # A closure/scanner label mismatch would surface here as a phantom row.
    assert [e for e in eps if e["category"] == "target_unanswered"] == []
    assert _rows(eps, "ADVISORY", "s3_connector") == []
    assert [e for e in eps if e["protocol"] in ("S3", "s3")] == []


def test_partial_jwt_run_adds_one_target_unanswered_row(tmp_path, monkeypatch):
    dead = f"http://127.0.0.1:{h.closed_port()}"
    with h.jwks_stub('{"keys": []}') as live:
        phases, eps = _scan(tmp_path, monkeypatch, {
            "connectors": {"enable_jwt": True, "jwt_targets": [live, dead]},
            "security": {"allow_internal_targets": True},
        })
    assert phases["jwt_scanning"]["status"] == "ran"
    unanswered = [e for e in eps if e["category"] == "target_unanswered"]
    assert len(unanswered) == 1
    assert unanswered[0]["protocol"] == "ERROR"
    assert dead in unanswered[0]["host"]
    assert live not in unanswered[0]["host"]
