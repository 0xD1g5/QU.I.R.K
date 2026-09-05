"""Route-level proof for serialization path (b) — SCORE-03 / D-03b (Phase 184.3-03).

RESEARCH.md names two independent timestamp-serialization paths in the dashboard API:

  (a) Pydantic-typed `datetime` response fields, closed by plan 184.3-02's `UTCDateTime`
      Annotated type. Covered by `tests/test_dashboard_api.py`.
  (b) hand-rolled `.isoformat()` calls that write an instant directly into a `str`-typed
      response field, bypassing Pydantic (and therefore `UTCDateTime`) entirely. This is
      what plan 184.3-03 closes by routing those call sites through
      `quirk.dashboard.api._timestamp_utils.stamp_utc_iso`.

`test_dashboard_api.py` never reaches path (b) — none of its assertions inspect the raw
JSON text of a hand-rolled `.isoformat()` field. This file exists to close that gap.

Also asserts the D-05 identity-key invariant: `scan.py:1350`'s prefix-LIKE key and
`scan.py:1671`'s `response_scan_id` must NEVER gain a `+00:00` suffix, because both are
matched against already-stored strings — an offset change there produces a silent EMPTY
RESULT SET (RESEARCH.md Pitfall 2), not an exception. The `scan_id` round-trip test below
is the mechanical guard for that failure mode: it asserts a filtered follow-up request
returns a NON-EMPTY (row count > 0) result, not merely "no exception raised".
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, CryptoEndpoint, ScanJob, ScheduledScan


def _client_and_session():
    """Fresh in-memory SQLite DB + TestClient per test — mirrors
    `tests/test_dashboard_api.py::_drift_client_and_session`'s pattern (not
    reused directly since it is module-private to that file)."""
    db_name = f"test_ts_route_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app, headers={"X-Quirk-Request": "1"}), TestingSession


def _seed_job(TestingSession, **kwargs):
    db = TestingSession()
    try:
        defaults = dict(
            job_id="job-1",
            status="completed",
            target="10.0.0.1",
            profile="quick",
            calibration="balanced",
        )
        defaults.update(kwargs)
        db.add(ScanJob(**defaults))
        db.commit()
    finally:
        db.close()


def _seed_crypto_endpoint(TestingSession, scanned_at, **kwargs):
    db = TestingSession()
    try:
        defaults = dict(host="10.0.0.1", port=443, protocol="TLS", severity="LOW")
        defaults.update(kwargs)
        db.add(CryptoEndpoint(scanned_at=scanned_at, **defaults))
        db.commit()
    finally:
        db.close()


def test_jobs_route_timestamps_carry_offset_and_leading_digits_unchanged():
    """jobs.py:175-176 — started_at/completed_at now route through
    stamp_utc_iso. Assert on the RAW JSON text (not a re-parsed object) that
    both fields end with the literal +00:00 and that the seeded naive digits
    are unchanged (attached, not converted)."""
    seeded_started = datetime(2026, 9, 4, 10, 0, 0)
    seeded_completed = datetime(2026, 9, 4, 10, 5, 30)

    client, TestingSession = _client_and_session()
    _seed_job(
        TestingSession,
        job_id="job-offset",
        started_at=seeded_started,
        completed_at=seeded_completed,
    )

    resp = client.get("/api/jobs/job-offset")
    assert resp.status_code == 200
    raw_text = resp.text

    assert '"2026-09-04T10:00:00+00:00"' in raw_text
    assert '"2026-09-04T10:05:30+00:00"' in raw_text

    body = resp.json()
    assert body["started_at"] == "2026-09-04T10:00:00+00:00"
    assert body["completed_at"] == "2026-09-04T10:05:30+00:00"


def test_jobs_route_none_timestamps_serialize_as_json_null():
    """Regression case for the delegated None-guard: a still-running job has
    completed_at=None, which must reach the wire as JSON null, never the
    string "None"."""
    client, TestingSession = _client_and_session()
    _seed_job(
        TestingSession,
        job_id="job-running",
        status="running",
        started_at=datetime(2026, 9, 4, 10, 0, 0),
        completed_at=None,
    )

    resp = client.get("/api/jobs/job-running")
    assert resp.status_code == 200
    raw_text = resp.text

    assert '"completed_at":null' in raw_text.replace('", "', '","').replace(
        '": ', '":'
    ) or '"completed_at": null' in raw_text
    assert '"completed_at":"None"' not in raw_text
    assert '"completed_at": "None"' not in raw_text

    body = resp.json()
    assert body["completed_at"] is None


def test_schedules_route_timestamps_carry_offset():
    """schedules.py:83 (_iso) — last_run_at/created_at now route through
    stamp_utc_iso. next_run_at is excluded here since it is computed
    on-the-fly from croniter against "now" (D-06, never stored), which
    cannot be pinned to a literal expected string in this test."""
    seeded_last_run = datetime(2026, 9, 3, 8, 15, 0)
    seeded_created = datetime(2026, 9, 1, 0, 0, 0)

    client, TestingSession = _client_and_session()
    db = TestingSession()
    try:
        db.add(
            ScheduledScan(
                name="nightly",
                cron_expr="0 2 * * *",
                target="10.0.0.0/24",
                enabled=True,
                last_run_at=seeded_last_run,
                created_at=seeded_created,
            )
        )
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/schedules")
    assert resp.status_code == 200
    raw_text = resp.text

    assert '"2026-09-03T08:15:00+00:00"' in raw_text
    assert '"2026-09-01T00:00:00+00:00"' in raw_text

    body = resp.json()
    schedule = body["schedules"][0]
    assert schedule["last_run_at"] == "2026-09-03T08:15:00+00:00"
    assert schedule["created_at"] == "2026-09-01T00:00:00+00:00"


def test_scan_latest_scan_id_round_trips_to_a_non_empty_result():
    """D-05 / RESEARCH.md Pitfall 2: scan.py:1671's response_scan_id is an
    identity key, left byte-unchanged (no +00:00). Assert the value the
    scan-latest route returns can be fed straight back as ?scan_id=... and
    still resolve a NON-EMPTY endpoint set — a silently reformatted key
    would instead produce an empty result set, not an exception, so this
    test asserts row count > 0 explicitly."""
    seeded_ts = datetime(2026, 9, 4, 12, 30, 0, 500000)

    client, TestingSession = _client_and_session()
    _seed_crypto_endpoint(TestingSession, seeded_ts, scan_run_id=None)

    first = client.get("/api/scan/latest")
    assert first.status_code == 200
    first_body = first.json()
    returned_scan_id = first_body["meta"]["scan_id"]

    # Identity key must be byte-unchanged — no offset attached.
    assert not returned_scan_id.endswith("+00:00")
    assert returned_scan_id == seeded_ts.isoformat()

    second = client.get("/api/scan/latest", params={"scan_id": returned_scan_id})
    assert second.status_code == 200
    second_body = second.json()

    assert second_body["meta"]["total_endpoints"] > 0
