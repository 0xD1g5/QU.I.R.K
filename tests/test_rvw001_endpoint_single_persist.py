"""RVW-001: a scanned endpoint must persist exactly once per scan session.

`_flush_stage_endpoints()` (run_scan.py, Phase 67 RESUME-01) writes each stage's
rows as the stage completes; the final ``db_persist`` block re-persists the whole
endpoint list. The second write was intended to UPDATE the already-flushed rows
(see its CR-03 comment), but ``session.merge()`` returns a *new* persistent
instance and never assigns the PK back onto the object passed in — so the
endpoints arrive at the final persist with ``id is None`` and are INSERTed again.

Result: doubled certificate inventory, doubled Data-in-Motion rows, and a doubled
endpoint count on the consultant's deliverable.
"""
import datetime
import os
import tempfile

from quirk.db import get_session, init_db
from quirk.models import CryptoEndpoint

import run_scan


def _fresh_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    init_db(tmp.name)
    return tmp.name


def _persist_like_a_scan(db_path, endpoints):
    """Reproduce the two writes a real scan performs against the same objects."""
    run_scan._flush_stage_endpoints(db_path, endpoints)   # stage flush
    with get_session(db_path) as session:                  # final db_persist
        for ep in endpoints:
            session.merge(ep)
        session.commit()


def test_stage_flush_assigns_primary_key():
    """_flush_stage_endpoints must write the PK back onto the passed object.

    Without this the object stays transient and the final persist INSERTs again.
    """
    db_path = _fresh_db()
    try:
        ep = CryptoEndpoint(
            host="10.0.0.1", port=443, protocol="TLS",
            scanned_at=datetime.datetime.now(),
        )
        run_scan._flush_stage_endpoints(db_path, [ep])
        assert ep.id is not None, (
            "RVW-001: _flush_stage_endpoints left ep.id unset — the final "
            "db_persist will INSERT a duplicate row instead of UPDATE'ing"
        )
    finally:
        os.unlink(db_path)


def test_single_host_scan_yields_no_duplicate_rows():
    """A one-host scan must not produce two rows differing only in `id`."""
    db_path = _fresh_db()
    try:
        endpoints = [
            CryptoEndpoint(host="10.0.0.1", port=443, protocol="TLS",
                           scanned_at=datetime.datetime.now()),
            CryptoEndpoint(host="10.0.0.1", port=22, protocol="SSH",
                           scanned_at=datetime.datetime.now()),
        ]
        _persist_like_a_scan(db_path, endpoints)

        with get_session(db_path) as session:
            rows = session.query(CryptoEndpoint).all()
            natural_keys = [(r.host, r.port, r.protocol) for r in rows]

        assert len(rows) == len(endpoints), (
            f"RVW-001: {len(endpoints)} endpoints scanned but {len(rows)} rows "
            f"persisted — {natural_keys}"
        )
        assert len(set(natural_keys)) == len(natural_keys), (
            f"RVW-001: duplicate (host, port, protocol) rows persisted: {natural_keys}"
        )
    finally:
        os.unlink(db_path)


def test_repeated_stage_flush_is_idempotent():
    """Two flushes of the same objects (resume path) must not duplicate rows."""
    db_path = _fresh_db()
    try:
        ep = CryptoEndpoint(host="10.0.0.2", port=443, protocol="TLS",
                            scanned_at=datetime.datetime.now())
        run_scan._flush_stage_endpoints(db_path, [ep])
        run_scan._flush_stage_endpoints(db_path, [ep])

        with get_session(db_path) as session:
            assert session.query(CryptoEndpoint).count() == 1, (
                "RVW-001: re-flushing the same endpoint object INSERTed a second row"
            )
    finally:
        os.unlink(db_path)
