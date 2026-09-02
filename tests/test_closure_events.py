"""Phase 180 Plan 03: closure-event VOCABULARY and SCHEMA guard tests.

This file guards SCHEMA and VOCABULARY only — no closure decision is made or
asserted in Plan 03. That is Plans 04/05's job. Specifically this file pins:

- `CLOSURE_EVENT_TYPES`, the write-site allowlist for `RemediationClosureEvent.event_type`
  (D-22, mirroring T-155-03's rule that the allowlist lives in the writer module, not the model).
- `remediation_closure_events`, an append-only event table created by `init_db`.
- D-19's decision that resurface history lives in a DEDICATED EVENT TABLE, not a counter
  column on `RemediationItemFingerprint` — a counter records *how many* but not *when* or
  *against which prior scan*, which collapses history into a scalar the same way folding
  `resurfaced` into `closed` would. The event table was chosen, not defaulted into.
- D-23: the event table stores NO host/port — those already live on the joinable
  `remediation_item_fingerprints` row.
"""
from __future__ import annotations

import datetime
import pathlib

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import sessionmaker

from quirk.db import init_db


def test_closure_event_types_allowlist() -> None:
    from quirk.intelligence.remediation import CLOSURE_EVENT_TYPES

    assert CLOSURE_EVENT_TYPES == ("closed", "resurfaced", "reclosed")


def test_remediation_closure_events_table_created_by_init_db(tmp_path) -> None:
    db_path = tmp_path / "closure_events.db"

    engine = init_db(str(db_path))
    inspector = sa_inspect(engine)
    assert "remediation_closure_events" in inspector.get_table_names()

    # Second init_db call on the same path must be a no-op (idempotent) —
    # must not raise "table already exists" or any other error.
    engine2 = init_db(str(db_path))
    inspector2 = sa_inspect(engine2)
    assert "remediation_closure_events" in inspector2.get_table_names()


def test_remediation_closure_event_columns(tmp_path) -> None:
    db_path = tmp_path / "closure_columns.db"
    engine = init_db(str(db_path))
    inspector = sa_inspect(engine)

    columns = {col["name"] for col in inspector.get_columns("remediation_closure_events")}
    assert columns == {
        "id",
        "slug",
        "finding_fingerprint",
        "scan_run_id",
        "prior_scan_run_id",
        "event_type",
        "from_state",
        "to_state",
        "reason",
        "observed_at",
    }


def test_remediation_closure_event_stores_no_host_or_port(tmp_path) -> None:
    db_path = tmp_path / "closure_no_host_port.db"
    engine = init_db(str(db_path))
    inspector = sa_inspect(engine)

    columns = {col["name"] for col in inspector.get_columns("remediation_closure_events")}
    assert "host" not in columns
    assert "port" not in columns


def test_item_progress_does_not_count_resurfaced_as_closed(tmp_path) -> None:
    """The single most damaging possible mis-read of the new state: a naive
    `item_progress` implementation could conflate `resurfaced` with
    `closed` (both "not currently open" in a lazy binary read). Pin that it
    does not.
    """
    from quirk.models import RemediationItemFingerprint
    from quirk.intelligence.remediation import item_progress

    db_path = tmp_path / "progress_resurfaced.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        scan_run_id = "run-resurfaced-1"
        slug = "plaintext-http-exposure"
        states = ["closed", "resurfaced", "open", "not_observed"]
        for i, state in enumerate(states):
            session.add(
                RemediationItemFingerprint(
                    slug=slug,
                    scan_run_id=scan_run_id,
                    finding_fingerprint=f"fp-{i}",
                    host=f"host{i}.example.com",
                    port=80,
                    finding_title="Plaintext HTTP service detected",
                    state=state,
                    observed_at=datetime.datetime.utcnow(),
                )
            )
        session.commit()

        result = item_progress(session, scan_run_id=scan_run_id, slug=slug)
        assert result == (1, 4)
    finally:
        session.close()


def test_closure_events_are_append_only_in_source() -> None:
    """Mechanically enforce D-19's retention property: no module under
    `quirk/` issues an UPDATE or DELETE against `RemediationClosureEvent`.

    Includes a NEGATIVE CONTROL (Phase 179 `_SLUG_PRIORITY` /
    `test_remediation_advisory_guard.py` precedent): a guard that can only
    pass is not a guard, so this test also proves the check can detect a
    violation.
    """

    def _violations(source: str) -> list:
        hits = []
        for needle in (
            "query(RemediationClosureEvent).delete",
            "query(RemediationClosureEvent).update",
        ):
            if needle in source:
                hits.append(needle)
        if "session.delete(" in source and "RemediationClosureEvent" in source:
            hits.append("session.delete(...) near RemediationClosureEvent")
        return hits

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    quirk_dir = repo_root / "quirk"
    for path in quirk_dir.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        violations = _violations(source)
        assert not violations, f"{path}: {violations}"

    # Negative control: prove the checker itself can fail.
    fixture_source = (
        "def bad():\n"
        "    session.query(RemediationClosureEvent).delete()\n"
    )
    assert _violations(fixture_source) == ["query(RemediationClosureEvent).delete"]
