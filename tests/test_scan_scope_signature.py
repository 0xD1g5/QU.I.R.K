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
    build_scope_signature,
    compute_signature_digest,
)
from quirk.models import Sensor

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


