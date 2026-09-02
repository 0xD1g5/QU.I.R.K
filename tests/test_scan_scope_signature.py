"""Phase 179 Plan 04: scan scope signature + positively-asserted probe health.

Covers `build_scope_signature`, `compute_signature_digest`,
`assess_probe_health`, and `persist_scope_signature` — the substrate Phase
180 reads to hard-refuse closure across incomparable scans. See
`quirk/intelligence/scope_signature.py`'s module docstring for the full
threat model this guards against (a `--profile quick` re-engagement run
auto-generating dozens of false closures) and the TRIAGE-176-03 precedent
`test_probe_health_positive_assertion` reproduces exactly.
"""
from __future__ import annotations

import copy
import inspect
from datetime import datetime, timezone

import pytest

from quirk.config import config_from_dict
from quirk.db import get_session, init_db
from quirk.intelligence.scope_signature import (
    _FAMILY_SPEC,
    assess_probe_health,
    build_scope_signature,
    compute_signature_digest,
    persist_scope_signature,
)
from quirk.models import CryptoEndpoint, ScanScopeSignature, Sensor

SCAN_RUN_ID = "2026-09-02T00:00:00Z"


_MINIMAL_RAW = {
    "assessment": {
        "name": "test",
        "data_classification": "internal",
        "report_owner": "tester",
        "timezone": "UTC",
    },
    "scan": {
        "timeout_seconds": 5,
        "concurrency": 200,
        "ports_tls": [443, 8443],
    },
    "targets": {
        "fqdns": [],
        "cidrs": [],
        "include_ips": [],
        "exclude_ips": [],
    },
    "output": {
        "directory": "/tmp/quirk-test",
        "db_path": "/tmp/quirk-test.db",
    },
}


def _cfg(**overrides):
    raw = copy.deepcopy(_MINIMAL_RAW)
    raw.update(overrides)
    return config_from_dict(raw)


# ---------------------------------------------------------------------------
# Task 1: build_scope_signature / compute_signature_digest
# ---------------------------------------------------------------------------


def test_build_scope_signature_port_scope_falls_back_to_sorted_ports_tls():
    cfg = _cfg()
    sig = build_scope_signature(cfg)
    assert sig["port_scope"] == "443,8443"


def test_build_scope_signature_uses_nmap_port_scope_when_set():
    cfg = _cfg()
    cfg.scan.nmap_port_scope = "top1000"
    sig = build_scope_signature(cfg)
    assert sig["port_scope"] == "top1000"


def test_build_scope_signature_profile_and_lists_are_sorted():
    cfg = _cfg()
    sig = build_scope_signature(cfg)
    assert sig["profile"] == "balanced"
    assert sig["extras_present"] == sorted(sig["extras_present"])
    assert sig["credentials_present"] == sorted(sig["credentials_present"])
    assert sig["sensor_set"] == []


def test_build_scope_signature_credentials_present_labels_only():
    cfg = _cfg()
    cfg.connectors.pg_scanner_user = "scanner"
    cfg.connectors.aws_profile = "prod"
    sig = build_scope_signature(cfg)
    assert sig["credentials_present"] == ["aws", "postgres"]


def test_build_scope_signature_never_stores_credential_values(tmp_path):
    """T-179-05: only KIND labels, never the underlying value."""
    cfg = _cfg()
    cfg.connectors.pg_scanner_user = "super-secret-username"
    cfg.connectors.aws_profile = "super-secret-profile"
    sig = build_scope_signature(cfg)
    flat = str(sig)
    assert "super-secret-username" not in flat
    assert "super-secret-profile" not in flat


def test_build_scope_signature_sensor_set_reads_enrolled_fleet(tmp_path):
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    cfg = _cfg()
    with get_session(db_path) as session:
        now = datetime.now(timezone.utc)
        session.add(
            Sensor(
                sensor_id="11111111-1111-1111-1111-111111111111",
                segment="segment-a",
                engagement="eng-1",
                enrolled_at=now,
                expected_cadence_minutes=60,
            )
        )
        session.add(
            Sensor(
                sensor_id="00000000-0000-0000-0000-000000000000",
                segment="segment-b",
                engagement="eng-1",
                enrolled_at=now,
                expected_cadence_minutes=60,
            )
        )
        session.commit()
        sig = build_scope_signature(cfg, session)
    assert sig["sensor_set"] == [
        "00000000-0000-0000-0000-000000000000",
        "11111111-1111-1111-1111-111111111111",
    ]


def test_digest_is_64_char_hex_and_stable_across_key_order():
    sig = {
        "signature_version": "1.0.0",
        "port_scope": "443",
        "profile": "balanced",
        "extras_present": [],
        "credentials_present": [],
        "sensor_set": [],
    }
    h1 = compute_signature_digest(sig)
    h2 = compute_signature_digest(dict(reversed(list(sig.items()))))
    assert len(h1) == 64
    assert h1 == h2


def test_digest_two_independent_identical_signatures_match():
    cfg_a = _cfg()
    cfg_b = _cfg()
    sig_a = build_scope_signature(cfg_a)
    sig_b = build_scope_signature(cfg_b)
    assert compute_signature_digest(sig_a) == compute_signature_digest(sig_b)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda cfg: setattr(cfg.intelligence, "profile", "strict"),
        lambda cfg: setattr(cfg.scan, "nmap_port_scope", "top1000"),
        lambda cfg: setattr(cfg.connectors, "pg_scanner_user", "scanner"),
    ],
    ids=["profile", "port_scope", "credentials_present"],
)
def test_digest_sensitivity_matrix_cfg_mutations(mutate):
    baseline_cfg = _cfg()
    baseline_digest = compute_signature_digest(build_scope_signature(baseline_cfg))

    mutated_cfg = _cfg()
    mutate(mutated_cfg)
    mutated_digest = compute_signature_digest(build_scope_signature(mutated_cfg))

    assert mutated_digest != baseline_digest


def test_digest_sensitivity_extras_present():
    baseline = {
        "signature_version": "1.0.0",
        "port_scope": "443",
        "profile": "balanced",
        "extras_present": ["db"],
        "credentials_present": [],
        "sensor_set": [],
    }
    mutated = dict(baseline, extras_present=["db", "cloud"])
    assert compute_signature_digest(baseline) != compute_signature_digest(mutated)


def test_digest_sensitivity_sensor_set():
    baseline = {
        "signature_version": "1.0.0",
        "port_scope": "443",
        "profile": "balanced",
        "extras_present": [],
        "credentials_present": [],
        "sensor_set": ["sensor-a"],
    }
    mutated = dict(baseline, sensor_set=["sensor-a", "sensor-b"])
    assert compute_signature_digest(baseline) != compute_signature_digest(mutated)


def test_digest_insensitive_to_probe_health():
    """probe_health_json is NOT an input to the digest — it varies run to run."""
    sig = {
        "signature_version": "1.0.0",
        "port_scope": "443",
        "profile": "balanced",
        "extras_present": [],
        "credentials_present": [],
        "sensor_set": [],
    }
    digest_before = compute_signature_digest(sig)

    sig_with_health = dict(sig)
    sig_with_health["probe_health_json"] = {"ssh": {"status": "unhealthy"}}
    digest_after = compute_signature_digest(sig_with_health)

    assert digest_before == digest_after


def test_module_never_imports_scoring():
    import quirk.intelligence.scope_signature as mod

    source = inspect.getsource(mod)
    assert "scoring" not in source


# ---------------------------------------------------------------------------
# Phase 180 (D-13): estate separation
#
# build_scope_signature captured scan CONFIGURATION only (signature_version,
# port_scope, profile, extras_present, credentials_present, sensor_set) —
# nothing identifying WHICH ESTATE was scanned. Two different clients
# scanned with the same profile produced an IDENTICAL digest, so an absent
# finding in client B's scan would read as client A's closure. These tests
# prove that hole RED before quirk/intelligence/scope_signature.py is
# touched (Task 2 fixes it). See 180-CONTEXT.md's addendum and D-13a/b/c.
# ---------------------------------------------------------------------------


def _cfg_with_targets(**targets_overrides):
    raw = copy.deepcopy(_MINIMAL_RAW)
    raw["targets"] = dict(raw["targets"], **targets_overrides)
    return config_from_dict(raw)


def test_estate_separation_different_targets_produce_different_digests():
    cfg_a = _cfg_with_targets(fqdns=["a.example.com"])
    cfg_b = _cfg_with_targets(fqdns=["b.example.net"])

    digest_a = compute_signature_digest(build_scope_signature(cfg_a))
    digest_b = compute_signature_digest(build_scope_signature(cfg_b))

    assert digest_a != digest_b


def test_estate_separation_holds_for_cidrs_and_include_ips():
    cfg_cidr_a = _cfg_with_targets(cidrs=["10.0.0.0/24"])
    cfg_cidr_b = _cfg_with_targets(cidrs=["192.168.7.0/24"])
    assert compute_signature_digest(
        build_scope_signature(cfg_cidr_a)
    ) != compute_signature_digest(build_scope_signature(cfg_cidr_b))

    cfg_ip_a = _cfg_with_targets(include_ips=["10.0.0.5"])
    cfg_ip_b = _cfg_with_targets(include_ips=["192.168.7.5"])
    assert compute_signature_digest(
        build_scope_signature(cfg_ip_a)
    ) != compute_signature_digest(build_scope_signature(cfg_ip_b))


def test_same_estate_rescan_produces_identical_digest():
    """Stability half of D-13a: same estate, different order/case/whitespace
    of the target lists, must still produce the SAME digest — otherwise
    nothing could ever close."""
    cfg_1 = _cfg_with_targets(
        fqdns=[" A.Example.com ", "b.example.net"],
        cidrs=["10.0.0.0/24", " 192.168.7.0/24 "],
    )
    cfg_2 = _cfg_with_targets(
        fqdns=["b.example.net", "a.example.com"],
        cidrs=["192.168.7.0/24", "10.0.0.0/24"],
    )

    digest_1 = compute_signature_digest(build_scope_signature(cfg_1))
    digest_2 = compute_signature_digest(build_scope_signature(cfg_2))

    assert digest_1 == digest_2


def test_target_set_digest_stores_no_host_literals():
    literal_fqdn = "secret-client-host.example.com"
    literal_cidr = "10.55.0.0/24"
    literal_ip = "10.55.0.9"
    cfg = _cfg_with_targets(
        fqdns=[literal_fqdn], cidrs=[literal_cidr], include_ips=[literal_ip]
    )

    sig = build_scope_signature(cfg)
    flat = str(sig)

    assert literal_fqdn not in flat
    assert literal_cidr not in flat
    assert literal_ip not in flat


def test_signature_version_is_two_zero_zero():
    import quirk.intelligence.scope_signature as mod

    assert mod.SCOPE_SIGNATURE_VERSION == "2.0.0"
    assert "target_set_digest" in mod._DIGEST_FIELDS


# ---------------------------------------------------------------------------
# Task 2: assess_probe_health — positive assertion per family
# ---------------------------------------------------------------------------


def _run_stats_with_timing(*keys: str) -> dict:
    return {"timings_sec": {k: 0.1 for k in keys}}


def test_family_spec_covers_at_least_thirteen_families():
    assert "ssh" in _FAMILY_SPEC
    assert "broker" in _FAMILY_SPEC
    assert len(_FAMILY_SPEC) >= 13


def test_probe_health_positive_assertion() -> None:
    """THE degraded-probe guard — TRIAGE-176-03's exact shape.

    Three SSH endpoints, enabled, timing key present, every endpoint has
    ssh_audit_json is None AND scan_error is None. This is exactly the
    ssh-audit exit-2/empty-stdout defect: the scan exited 0 and scan_error
    stayed NULL, yet no evidence was ever produced. Must record UNHEALTHY.
    """
    cfg = _cfg()
    cfg.connectors.enable_kerberos = True  # unrelated; keep default off elsewhere
    endpoints = [
        CryptoEndpoint(
            host=f"host{i}.example.com",
            port=22,
            protocol="SSH",
            ssh_audit_json=None,
            scan_error=None,
        )
        for i in range(3)
    ]
    run_stats = _run_stats_with_timing("ssh_scanning")

    health = assess_probe_health(cfg, endpoints, run_stats)

    assert health["ssh"]["status"] == "unhealthy"
    assert health["ssh"]["endpoints_seen"] == 3
    assert health["ssh"]["endpoints_with_evidence"] == 0


def test_probe_health_positive_control_ssh_healthy_with_evidence():
    cfg = _cfg()
    endpoints = [
        CryptoEndpoint(host="h1", port=22, protocol="SSH", ssh_audit_json=None),
        CryptoEndpoint(
            host="h2", port=22, protocol="SSH", ssh_audit_json='{"algo": "mlkem768"}'
        ),
    ]
    run_stats = _run_stats_with_timing("ssh_scanning")

    health = assess_probe_health(cfg, endpoints, run_stats)

    assert health["ssh"]["status"] == "healthy"
    assert health["ssh"]["endpoints_with_evidence"] == 1


def test_probe_health_scan_error_none_alone_never_produces_healthy():
    cfg = _cfg()
    endpoints = [
        CryptoEndpoint(host="h1", port=22, protocol="SSH", ssh_audit_json=None, scan_error=None)
    ]
    run_stats = _run_stats_with_timing("ssh_scanning")

    health = assess_probe_health(cfg, endpoints, run_stats)

    assert health["ssh"]["status"] == "unhealthy"


def test_probe_health_no_targets_distinguished_from_unhealthy():
    cfg = _cfg()
    endpoints: list = []
    run_stats = _run_stats_with_timing("ssh_scanning")

    health = assess_probe_health(cfg, endpoints, run_stats)

    assert health["ssh"]["status"] == "no_targets"
    assert health["ssh"]["endpoints_seen"] == 0


def test_probe_health_family_disabled_in_cfg_is_not_run():
    cfg = _cfg()
    assert cfg.connectors.enable_jwt is False
    endpoints = [CryptoEndpoint(host="h1", port=443, protocol="JWT", jwt_scan_json="{}")]
    run_stats = _run_stats_with_timing("jwt_scanning")

    health = assess_probe_health(cfg, endpoints, run_stats)

    assert health["jwt"]["status"] == "not_run"


def test_probe_health_timing_key_absent_is_not_run_even_if_enabled():
    cfg = _cfg()
    cfg.connectors.enable_jwt = True
    endpoints = [CryptoEndpoint(host="h1", port=443, protocol="JWT", jwt_scan_json='{"kid": "1"}')]
    run_stats = {"timings_sec": {}}

    health = assess_probe_health(cfg, endpoints, run_stats)

    assert health["jwt"]["status"] == "not_run"


def test_probe_health_stale_timing_key_never_upgrades_to_healthy():
    """Phase 173 precedent: a stale broker_scanning key with zero broker
    endpoints and no evidence must not read healthy."""
    cfg = _cfg()
    cfg.connectors.enable_broker = True
    endpoints: list = []
    run_stats = _run_stats_with_timing("broker_scanning")

    health = assess_probe_health(cfg, endpoints, run_stats)

    assert health["broker"]["status"] == "no_targets"


@pytest.mark.parametrize("empty_value", ["", "   ", "null", "{}", "[]"])
def test_probe_health_empty_json_containers_count_as_no_evidence(empty_value):
    cfg = _cfg()
    endpoints = [
        CryptoEndpoint(host="h1", port=22, protocol="SSH", ssh_audit_json=empty_value)
    ]
    run_stats = _run_stats_with_timing("ssh_scanning")

    health = assess_probe_health(cfg, endpoints, run_stats)

    assert health["ssh"]["status"] == "unhealthy"


def test_probe_health_non_deep_tls_is_not_run():
    cfg = _cfg()
    assert cfg.scan.tls_enum_mode == "fast"
    endpoints = [CryptoEndpoint(host="h1", port=443, protocol="TLS")]
    run_stats = _run_stats_with_timing("tls_scanning")

    health = assess_probe_health(cfg, endpoints, run_stats)

    assert health["tls"]["status"] == "not_run"


def test_probe_health_grep_no_exit_status_or_scan_error_signal():
    import quirk.intelligence.scope_signature as mod

    source = inspect.getsource(mod)
    assert "scan_error is None" not in source
    assert "returncode == 0" not in source
    assert "exit_code" not in source


# ---------------------------------------------------------------------------
# Task 3: persist_scope_signature
# ---------------------------------------------------------------------------


def test_persist_scope_signature_round_trip_digest_matches(tmp_path):
    import json

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    cfg = _cfg()
    endpoints = [CryptoEndpoint(host="h1", port=22, protocol="SSH", ssh_audit_json=None)]
    run_stats = _run_stats_with_timing("ssh_scanning")

    written_digest = persist_scope_signature(db_path, SCAN_RUN_ID, cfg, endpoints, run_stats)
    assert written_digest is not None

    with get_session(db_path) as session:
        row = (
            session.query(ScanScopeSignature)
            .filter(ScanScopeSignature.scan_run_id == SCAN_RUN_ID)
            .one()
        )
        recomputed_sig = {
            "signature_version": row.signature_version,
            "port_scope": row.port_scope,
            "profile": row.profile,
            "extras_present": json.loads(row.extras_present),
            "credentials_present": json.loads(row.credentials_present),
            "sensor_set": json.loads(row.sensor_set),
        }
        recomputed_digest = compute_signature_digest(recomputed_sig)
        assert recomputed_digest == row.digest
        assert recomputed_digest == written_digest


def test_persist_scope_signature_idempotent_under_resume(tmp_path):
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    cfg = _cfg()
    endpoints = [CryptoEndpoint(host="h1", port=22, protocol="SSH")]
    run_stats = _run_stats_with_timing("ssh_scanning")

    persist_scope_signature(db_path, SCAN_RUN_ID, cfg, endpoints, run_stats)
    persist_scope_signature(db_path, SCAN_RUN_ID, cfg, endpoints, run_stats)

    with get_session(db_path) as session:
        rows = (
            session.query(ScanScopeSignature)
            .filter(ScanScopeSignature.scan_run_id == SCAN_RUN_ID)
            .all()
        )
    assert len(rows) == 1


def test_persist_scope_signature_skips_without_scan_run_id_or_db_path(tmp_path):
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    cfg = _cfg()
    assert persist_scope_signature(db_path, "", cfg, [], {}) is None
    assert persist_scope_signature("", SCAN_RUN_ID, cfg, [], {}) is None


def test_persist_scope_signature_docstring_mentions_scan_run_id_and_sensor():
    import quirk.intelligence.scope_signature as mod

    doc = mod.persist_scope_signature.__doc__ or ""
    assert "scan_run_id" in doc
    assert "sensor" in doc


def test_run_scan_call_site_ordering_remediation_persist_then_scope_signature_then_reporting():
    import run_scan

    source = inspect.getsource(run_scan.main)
    assert source.index("remediation_persist") < source.index("scope_signature") < source.index('"reporting"')
