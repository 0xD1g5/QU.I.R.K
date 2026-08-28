"""Phase 171 (RESUME-06, D-02, locked): tests for --list-resumable's Target
column derivation.

`_handle_list_resumable()` currently recovers the Target column exclusively
via a `ScanJob` join. `ScanJob` rows only exist for dashboard-initiated
`--job-id` runs — a `--targets-file` CLI run never creates one, so every such
row's Target column renders as `"—"`, indistinguishable from "we have no idea
what this scan targeted" (verified by manual reproduction against a seeded
sqlite DB with CryptoEndpoint rows but no ScanJob row for the scan_run_id;
see 171-02-SUMMARY.md).

Per D-02 (locked): keep the ScanJob join as PRIMARY (a --job-id run's literal
target string is more faithful than a derived summary). Add a FALLBACK: when
no ScanJob row exists, derive a summary from that scan_run_id's
CryptoEndpoint.host rows. A scan_run_id with neither must show an honest
placeholder, never a fabricated target.

Tests 1-4 exercise the pure `_derive_target_summary()` helper.
Tests 5-7 exercise `_resolve_target_for_row()` against a real in-memory
sqlite session (mirrors tests/test_rvw003_scan_session_identity.py's fixture
pattern).
Test 8 is structural (parses the real run_scan.py source) so a passing
mirror test can never mask an unwired call site.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import run_scan
from quirk.models import Base, CryptoEndpoint, ScanJob

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUN_SCAN_PATH = _REPO_ROOT / "run_scan.py"


@pytest.fixture
def db():
    """An isolated in-memory database per test.

    Deliberately does NOT reuse the shared `dashboard_client` engine, whose
    process-wide `cache=shared` name is the subject of RVW-017.
    """
    engine = create_engine(
        f"sqlite:///file:resume171_{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# --- _derive_target_summary() -------------------------------------------


def test_derive_target_summary_truncates_with_more_suffix():
    result = run_scan._derive_target_summary(
        ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4", "10.0.0.5"]
    )
    assert result == "10.0.0.1, 10.0.0.2 (+3 more)"


def test_derive_target_summary_no_suffix_when_two_or_fewer():
    result = run_scan._derive_target_summary(["10.0.0.1", "10.0.0.2"])
    assert result == "10.0.0.1, 10.0.0.2"


def test_derive_target_summary_empty_list_is_honest_placeholder():
    result = run_scan._derive_target_summary([])
    assert result != "—", (
        "empty-derivation placeholder must be distinguishable from the "
        "existing job-row-missing dash"
    )
    assert "no target" in result.lower()


def test_derive_target_summary_deduplicates_hosts():
    result = run_scan._derive_target_summary(["10.0.0.1", "10.0.0.1", "10.0.0.2"])
    assert result == "10.0.0.1, 10.0.0.2"


# --- _resolve_target_for_row() -------------------------------------------


def test_resolve_target_for_row_prefers_job_row(db):
    job = ScanJob(
        job_id=str(uuid.uuid4()),
        status="completed",
        target="10.1.1.1/24",
        profile="standard",
        calibration="balanced",
        scan_run_id="run-a",
    )
    db.add(job)
    db.commit()

    job_row = db.query(ScanJob).filter(ScanJob.scan_run_id == "run-a").first()
    result = run_scan._resolve_target_for_row(db, "run-a", job_row)
    assert result == "10.1.1.1/24"


def test_resolve_target_for_row_falls_back_to_endpoints(db):
    for host in ("10.2.2.1", "10.2.2.2", "10.2.2.3"):
        db.add(CryptoEndpoint(host=host, port=443, protocol="TLS", scan_run_id="run-b"))
    db.commit()

    result = run_scan._resolve_target_for_row(db, "run-b", None)
    hosts = [
        row[0]
        for row in db.query(CryptoEndpoint.host)
        .filter(CryptoEndpoint.scan_run_id == "run-b")
        .order_by(CryptoEndpoint.id.asc())
        .all()
    ]
    assert result == run_scan._derive_target_summary(hosts)
    assert result == "10.2.2.1, 10.2.2.2 (+1 more)"


def test_resolve_target_for_row_no_data_shows_honest_placeholder(db):
    result = run_scan._resolve_target_for_row(db, "run-c", None)
    assert result == run_scan._derive_target_summary([])
    assert "no target" in result.lower()


# --- structural: call site actually wired --------------------------------


def test_handle_list_resumable_calls_resolve_target_for_row():
    source = _RUN_SCAN_PATH.read_text()
    start = source.index("def _handle_list_resumable")
    end = source.index("\ndef ", start + 1)
    body = source[start:end]
    assert "_resolve_target_for_row(" in body, (
        "_handle_list_resumable must call _resolve_target_for_row() to "
        "resolve the Target column"
    )
    assert 'getattr(job_row, "target", "—") if job_row else "—"' not in body, (
        "old inline dash-on-missing-job-row pattern must be replaced, not "
        "merely supplemented"
    )
