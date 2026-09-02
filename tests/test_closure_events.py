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

from sqlalchemy import inspect as sa_inspect

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
