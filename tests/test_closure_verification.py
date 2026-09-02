"""Phase 180 Plan 04 (CLOSE-01): the two-sided, machine-observed closure test suite.

Every design tension in this file resolves toward under-claiming. The failure being
prevented is a client attestation claiming remediation that never happened. An item
closes ONLY when BOTH sides hold: (a) the fingerprint was present in a comparable
PRIOR scan, AND (b) the CURRENT scan positively rechecked that item's host:port with a
HEALTHY probe and did not find it. Absence alone is NEVER sufficient — a vanished host,
a curtailed scan, or a shrunk target list must never read as a closure.

Each test below isolates exactly ONE refusal path (D-24: every refusal resolves to
`not_observed` — there is no `refused`/`incomparable`/`unknown` state) so a regression
in this suite names itself precisely: comparability ladder order (D-25), the probe
health gate (T-179's positive-evidence-only rule, TRIAGE-176-03), the absent-endpoint
guardrail (the Qualys precedent CLOSE-01 copies), item-level rollup (D-27), and the
mechanical absence of any human-assert affordance (D-28).

`resurfaced` detection is Plan 05's responsibility, NOT this file's. Pipeline wiring
into run_scan.py is Plan 06's responsibility, NOT this file's.
"""
from __future__ import annotations

import inspect
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from quirk.db import get_session, init_db
from quirk.models import (
    CryptoEndpoint,
    RemediationClosureEvent,
    RemediationItem,
    RemediationItemFingerprint,
    ScanScopeSignature,
)

PRIOR_SCAN_ID = "scan-prior-0001"
CURRENT_SCAN_ID = "scan-current-0002"
SLUG = "plaintext-http-exposure"
FINGERPRINT = "fp-aaaa1111"
HOST = "10.0.0.5"
PORT = 443
PROTOCOL = "TLS"
HEALTHY_TLS = {"tls": {"status": "healthy", "evidence_field": "tls_capabilities_json", "endpoints_seen": 1, "endpoints_with_evidence": 1}}


# ---------------------------------------------------------------------------
# Reusable fixture helper — every test below varies exactly ONE input.
# ---------------------------------------------------------------------------
def _seed_two_scans(
    tmp_path,
    *,
    include_prior_signature=True,
    prior_signature_version="2.0.0",
    prior_target_set_digest="tsd-a",
    prior_digest="digest-a",
    current_signature_version="2.0.0",
    current_target_set_digest="tsd-a",
    current_digest="digest-a",
    current_probe_health=None,
    include_prior_fingerprint=True,
    prior_fingerprint_state="open",
    include_current_endpoint=True,
    include_current_fingerprint=False,
    include_items=False,
    extra_prior_fingerprints=(),
    prior_created_at=None,
):
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    now = datetime.now(timezone.utc)
    p_created = prior_created_at if prior_created_at is not None else (now - timedelta(days=1))

    with get_session(db_path) as session:
        if include_prior_signature:
            session.add(
                ScanScopeSignature(
                    scan_run_id=PRIOR_SCAN_ID,
                    signature_version=prior_signature_version,
                    digest=prior_digest,
                    target_set_digest=prior_target_set_digest,
                    probe_health_json=json.dumps({}),
                    created_at=p_created,
                )
            )
        session.add(
            ScanScopeSignature(
                scan_run_id=CURRENT_SCAN_ID,
                signature_version=current_signature_version,
                digest=current_digest,
                target_set_digest=current_target_set_digest,
                probe_health_json=json.dumps(current_probe_health if current_probe_health is not None else HEALTHY_TLS),
                created_at=now,
            )
        )

        if include_prior_fingerprint:
            session.add(
                RemediationItemFingerprint(
                    remediation_item_id=None,
                    slug=SLUG,
                    scan_run_id=PRIOR_SCAN_ID,
                    finding_fingerprint=FINGERPRINT,
                    host=HOST,
                    port=PORT,
                    finding_title="Plaintext HTTP service detected",
                    state=prior_fingerprint_state,
                    observed_at=p_created,
                )
            )
        for extra in extra_prior_fingerprints:
            session.add(RemediationItemFingerprint(**extra))

        if include_current_endpoint:
            session.add(CryptoEndpoint(host=HOST, port=PORT, protocol=PROTOCOL, scan_run_id=CURRENT_SCAN_ID))

        if include_current_fingerprint:
            session.add(
                RemediationItemFingerprint(
                    remediation_item_id=None,
                    slug=SLUG,
                    scan_run_id=CURRENT_SCAN_ID,
                    finding_fingerprint=FINGERPRINT,
                    host=HOST,
                    port=PORT,
                    finding_title="Plaintext HTTP service detected",
                    state="not_observed",
                    observed_at=now,
                )
            )

        if include_items:
            session.add(
                RemediationItem(
                    slug=SLUG,
                    scan_run_id=PRIOR_SCAN_ID,
                    title="Remove plaintext HTTP exposure",
                    phase="NOW",
                    priority=10,
                    constituency="fingerprint",
                    state="open",
                    first_seen_scan_run_id=PRIOR_SCAN_ID,
                    created_at=p_created,
                )
            )

        session.commit()

    return db_path


def _fp_row(session, *, scan_run_id=PRIOR_SCAN_ID, slug=SLUG, finding_fingerprint=FINGERPRINT):
    return (
        session.query(RemediationItemFingerprint)
        .filter(
            RemediationItemFingerprint.scan_run_id == scan_run_id,
            RemediationItemFingerprint.slug == slug,
            RemediationItemFingerprint.finding_fingerprint == finding_fingerprint,
        )
        .one()
    )


def _events(session, **filters):
    q = session.query(RemediationClosureEvent)
    for key, value in filters.items():
        q = q.filter(getattr(RemediationClosureEvent, key) == value)
    return q.all()


# ---------------------------------------------------------------------------
# The two-sided condition
# ---------------------------------------------------------------------------
def test_two_sided_condition(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(tmp_path, include_current_fingerprint=False)
    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["closed"] == 1
    with get_session(db_path) as session:
        row = _fp_row(session)
        assert row.state == "closed"
        events = _events(session, scan_run_id=CURRENT_SCAN_ID, event_type="closed")
        assert len(events) == 1
        assert events[0].prior_scan_run_id == PRIOR_SCAN_ID


def test_unrechecked_never_closes(tmp_path):
    from quirk.intelligence.closure import compute_closure

    for status in ("no_targets", "not_run", "unhealthy"):
        health = {"tls": {"status": status, "evidence_field": "tls_capabilities_json", "endpoints_seen": 0, "endpoints_with_evidence": 0}}
        db_path = _seed_two_scans(tmp_path / status, current_probe_health=health)
        counters = compute_closure(db_path, CURRENT_SCAN_ID)

        assert counters["closed"] == 0
        assert counters["refused_probe"] == 1
        with get_session(db_path) as session:
            row = _fp_row(session)
            assert row.state != "closed"
            assert _events(session, event_type="closed") == []


def test_absent_endpoint_never_closes(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(tmp_path, include_current_endpoint=False)
    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["closed"] == 0
    assert counters["refused_absent_endpoint"] == 1
    with get_session(db_path) as session:
        row = _fp_row(session)
        assert row.state != "closed"


def test_digest_mismatch_refuses(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(tmp_path, current_digest="digest-b")
    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["closed"] == 0
    assert counters["refused_scope_mismatch"] == 1
    with get_session(db_path) as session:
        assert _events(session) == []


def test_missing_signature_is_not_comparable(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(tmp_path, include_prior_signature=False)
    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["closed"] == 0
    assert counters["refused_missing_signature"] == 1
    with get_session(db_path) as session:
        assert _events(session) == []


def test_null_target_set_digest_is_not_comparable(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(
        tmp_path,
        prior_signature_version="1.0.0",
        prior_target_set_digest=None,
    )
    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["closed"] == 0
    # D-25: signature_version_gap is checked BEFORE missing_target_set_digest.
    assert counters["refused_signature_version_gap"] == 1
    assert counters["refused_missing_target_set_digest"] == 0


def test_no_prior_scan_refuses(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    now = datetime.now(timezone.utc)
    with get_session(db_path) as session:
        session.add(
            ScanScopeSignature(
                scan_run_id=CURRENT_SCAN_ID,
                signature_version="2.0.0",
                digest="digest-a",
                target_set_digest="tsd-a",
                probe_health_json=json.dumps(HEALTHY_TLS),
                created_at=now,
            )
        )
        session.commit()

    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["closed"] == 0
    assert counters["refused_no_prior"] == 1
    with get_session(db_path) as session:
        assert _events(session) == []


def test_prior_scan_selection_orders_by_created_at_desc(tmp_path):
    from quirk.intelligence.closure import select_prior_scan_run_id

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    now = datetime.now(timezone.utc)

    with get_session(db_path) as session:
        session.add(ScanScopeSignature(scan_run_id="oldest", signature_version="2.0.0", digest="d", target_set_digest="t", created_at=now - timedelta(days=10)))
        session.add(ScanScopeSignature(scan_run_id="middle", signature_version="2.0.0", digest="d", target_set_digest="t", created_at=now - timedelta(days=5)))
        session.add(ScanScopeSignature(scan_run_id="latest", signature_version="2.0.0", digest="d", target_set_digest="t", created_at=now - timedelta(days=1)))
        session.add(ScanScopeSignature(scan_run_id="current", signature_version="2.0.0", digest="d", target_set_digest="t", created_at=now))
        session.commit()

        selected = select_prior_scan_run_id(session, current_scan_run_id="current")

    assert selected == "latest"


def test_prior_scan_selection_does_not_use_trends_helper():
    source = Path("quirk/intelligence/closure.py").read_text(encoding="utf-8")
    assert "from quirk.dashboard.api.routes.trends" not in source
    assert "_list_session_timestamps" not in source


def test_item_state_requires_all_fingerprints_closed(tmp_path):
    from quirk.intelligence.closure import compute_closure

    other_fp = "fp-bbbb2222"
    other_host, other_port = "10.0.0.6", 443
    db_path = _seed_two_scans(
        tmp_path,
        include_items=True,
        extra_prior_fingerprints=[
            dict(
                remediation_item_id=None,
                slug=SLUG,
                scan_run_id=PRIOR_SCAN_ID,
                finding_fingerprint=other_fp,
                host=other_host,
                port=other_port,
                finding_title="Plaintext HTTP service detected",
                state="open",
                observed_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        ],
    )
    # Second endpoint is still present (and thus still detected) in the current scan.
    with get_session(db_path) as session:
        session.add(CryptoEndpoint(host=other_host, port=other_port, protocol=PROTOCOL, scan_run_id=CURRENT_SCAN_ID))
        session.add(
            RemediationItemFingerprint(
                remediation_item_id=None,
                slug=SLUG,
                scan_run_id=CURRENT_SCAN_ID,
                finding_fingerprint=other_fp,
                host=other_host,
                port=other_port,
                finding_title="Plaintext HTTP service detected",
                state="not_observed",
                observed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["closed"] == 1  # only the FINGERPRINT constant closes
    assert counters["items_closed"] == 0
    with get_session(db_path) as session:
        item = session.query(RemediationItem).filter_by(slug=SLUG, scan_run_id=PRIOR_SCAN_ID).one()
        assert item.state != "closed"


def test_evidence_only_items_stay_not_observed(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    now = datetime.now(timezone.utc)
    p_created = now - timedelta(days=1)

    with get_session(db_path) as session:
        session.add(ScanScopeSignature(scan_run_id=PRIOR_SCAN_ID, signature_version="2.0.0", digest="digest-a", target_set_digest="tsd-a", probe_health_json=json.dumps({}), created_at=p_created))
        session.add(ScanScopeSignature(scan_run_id=CURRENT_SCAN_ID, signature_version="2.0.0", digest="digest-a", target_set_digest="tsd-a", probe_health_json=json.dumps(HEALTHY_TLS), created_at=now))
        session.add(
            RemediationItem(
                slug="scan-reliability",
                scan_run_id=PRIOR_SCAN_ID,
                title="Stabilize scan reliability",
                phase="NOW",
                priority=40,
                constituency="evidence_only",
                state="open",
                first_seen_scan_run_id=PRIOR_SCAN_ID,
                created_at=p_created,
            )
        )
        session.commit()

    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["items_closed"] == 0
    with get_session(db_path) as session:
        item = session.query(RemediationItem).filter_by(slug="scan-reliability", scan_run_id=PRIOR_SCAN_ID).one()
        assert item.state != "closed"


def test_compute_closure_is_idempotent(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(tmp_path)
    first = compute_closure(db_path, CURRENT_SCAN_ID)
    with get_session(db_path) as session:
        first_states = {row.id: row.state for row in session.query(RemediationItemFingerprint).all()}
        first_event_count = session.query(RemediationClosureEvent).count()

    second = compute_closure(db_path, CURRENT_SCAN_ID)
    with get_session(db_path) as session:
        second_states = {row.id: row.state for row in session.query(RemediationItemFingerprint).all()}
        second_event_count = session.query(RemediationClosureEvent).count()

    assert first["closed"] == 1
    assert first_states == second_states
    assert first_event_count == second_event_count == 1
    assert second["closed"] == 0  # already closed — idempotent re-run writes nothing new

