"""Phase 192 Plan 07 (OBS-02) — coverage loader + Scan Coverage report sections.

Locks D-13 (placement), D-15 (honest absence, no backfill), and the
always-renders contract shared with Phase 191's key_reuse precedent.
"""
from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest

from quirk.db import get_session, init_db
from quirk.models import ScanPhaseRecord
from quirk.reports.coverage import (
    COVERAGE_NOT_RECORDED_NOTICE,
    PHASE_LABELS,
    format_skip_note,
    load_scan_coverage,
)
from quirk.reports.content_model import ExecContent
from quirk.reports.executive import build_exec_markdown
from quirk.reports.technical import build_tech_markdown


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _seed_db(tmp_path, scan_run_id="run-1"):
    db_path = tmp_path / "coverage.db"
    init_db(str(db_path))
    with get_session(str(db_path)) as session:
        session.add_all(
            [
                ScanPhaseRecord(
                    scan_run_id=scan_run_id,
                    phase_name="tls_scanning",
                    status="ran",
                    duration_sec=1.5,
                    recorded_at=_now(),
                ),
                ScanPhaseRecord(
                    scan_run_id=scan_run_id,
                    phase_name="ssh_scanning",
                    status="ran",
                    duration_sec=0.8,
                    recorded_at=_now(),
                ),
                ScanPhaseRecord(
                    scan_run_id=scan_run_id,
                    phase_name="jwt_scanning",
                    status="ran",
                    duration_sec=0.3,
                    recorded_at=_now(),
                ),
                ScanPhaseRecord(
                    scan_run_id=scan_run_id,
                    phase_name="vault_scanning",
                    status="skipped",
                    reason="missing-credentials",
                    detail="VAULT_TOKEN not set",
                    recorded_at=_now(),
                ),
                ScanPhaseRecord(
                    scan_run_id=scan_run_id,
                    phase_name="broker_scanning",
                    status="skipped",
                    reason="disabled-by-config",
                    detail="connectors.enable_broker=false",
                    recorded_at=_now(),
                ),
            ]
        )
    return str(db_path)


# ---------------------------------------------------------------------------
# Task 1: load_scan_coverage
# ---------------------------------------------------------------------------


def test_loader_returns_recorded_payload_with_five_entries_sorted(tmp_path):
    db_path = _seed_db(tmp_path)
    payload = load_scan_coverage(db_path, "run-1")
    assert payload["recorded"] is True
    assert payload["ran"] == 3
    assert payload["skipped"] == 2
    assert len(payload["phases"]) == 5
    names = [p["phase_name"] for p in payload["phases"]]
    assert names == sorted(names)


def test_loader_falsy_db_path_returns_not_recorded():
    payload = load_scan_coverage(None, "run-1")
    assert payload == {"recorded": False, "ran": 0, "skipped": 0, "phases": []}


def test_loader_falsy_scan_run_id_returns_not_recorded(tmp_path):
    db_path = _seed_db(tmp_path)
    payload = load_scan_coverage(db_path, None)
    assert payload == {"recorded": False, "ran": 0, "skipped": 0, "phases": []}


def test_loader_zero_matching_rows_returns_not_recorded(tmp_path):
    db_path = _seed_db(tmp_path)
    payload = load_scan_coverage(db_path, "no-such-run")
    assert payload == {"recorded": False, "ran": 0, "skipped": 0, "phases": []}


def test_loader_never_raises_for_corrupt_or_absent_db_path(tmp_path):
    bogus = str(tmp_path / "does-not-exist" / "nope.db")
    payload = load_scan_coverage(bogus, "run-1")
    assert payload["recorded"] is False


def test_phase_labels_known_and_unmapped_fallback(tmp_path):
    db_path = tmp_path / "labels.db"
    init_db(str(db_path))
    with get_session(str(db_path)) as session:
        session.add_all(
            [
                ScanPhaseRecord(
                    scan_run_id="run-2",
                    phase_name="tls_scanning",
                    status="ran",
                    duration_sec=1.0,
                    recorded_at=_now(),
                ),
                ScanPhaseRecord(
                    scan_run_id="run-2",
                    phase_name="future_scanning",
                    status="ran",
                    duration_sec=1.0,
                    recorded_at=_now(),
                ),
            ]
        )
    payload = load_scan_coverage(str(db_path), "run-2")
    labels = {p["phase_name"]: p["label"] for p in payload["phases"]}
    assert labels["tls_scanning"] == "TLS"
    assert labels["future_scanning"] == "Future Scanning"
    assert PHASE_LABELS["tls_scanning"] == "TLS"


def test_exec_content_coverage_defaults_to_empty_dict():
    content = ExecContent(
        narrative_lead="",
        narrative_drivers=[],
        top_risks=[],
        roadmap_items=[],
        score_total=0,
        score_band="LOW",
        subscores={},
        raw_sum=0,
        sev_counts={},
    )
    assert content.coverage == {}


def test_format_skip_note_with_and_without_detail():
    assert format_skip_note({"reason": "missing-credentials", "detail": "VAULT_TOKEN not set"}) == (
        "Not assessed — skipped: missing-credentials (VAULT_TOKEN not set)"
    )
    assert format_skip_note({"reason": "disabled-by-config", "detail": None}) == (
        "Not assessed — skipped: disabled-by-config"
    )


def test_write_reports_calls_loader_once_and_shares_payload(tmp_path, monkeypatch):
    """write_reports calls load_scan_coverage exactly once; the same payload
    reaches both build_tech_markdown(coverage=...) and exec_content.coverage.
    """
    import quirk.reports.writer as writer_mod

    calls = []
    real_loader = writer_mod.load_scan_coverage

    def _counting_loader(db_path, scan_run_id):
        calls.append((db_path, scan_run_id))
        return real_loader(db_path, scan_run_id)

    monkeypatch.setattr(writer_mod, "load_scan_coverage", _counting_loader)

    db_path = _seed_db(tmp_path, scan_run_id="write-reports-run")

    cfg = SimpleNamespace(
        assessment=SimpleNamespace(
            name="Coverage Wiring Org",
            report_owner="Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory=str(tmp_path / "out"), db_path=db_path),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides=None),
    )

    # Empty endpoints list — write_reports derives _scan_run_id from
    # run_stats["started_utc"] when no endpoint carries a scan_run_id
    # (exercised directly by the fallback test below too).
    writer_mod.write_reports(cfg, [], [], run_stats={"started_utc": "write-reports-run"})

    assert len(calls) == 1
    assert calls[0] == (db_path, "write-reports-run")


def test_write_reports_falls_back_to_started_utc_when_no_endpoint_scan_run_id(tmp_path, monkeypatch):
    import quirk.reports.writer as writer_mod

    calls = []
    real_loader = writer_mod.load_scan_coverage

    def _counting_loader(db_path, scan_run_id):
        calls.append((db_path, scan_run_id))
        return real_loader(db_path, scan_run_id)

    monkeypatch.setattr(writer_mod, "load_scan_coverage", _counting_loader)

    db_path = _seed_db(tmp_path, scan_run_id="fallback-run")

    cfg = SimpleNamespace(
        assessment=SimpleNamespace(
            name="Fallback Org",
            report_owner="Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory=str(tmp_path / "out2"), db_path=db_path),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides=None),
    )

    writer_mod.write_reports(cfg, [], [], run_stats={"started_utc": "fallback-run"})

    assert len(calls) == 1
    assert calls[0] == (db_path, "fallback-run")

