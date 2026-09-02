"""Phase 179 REMED-01/02/03: ORM contract + closed-set + progress tests.

This plan models and persists identity and state. It does NOT compute
closure (Phase 180) and does NOT surface anything (Phase 181).
"""
from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.db import init_db


# ---------------------------------------------------------------------------
# Task 1: schema-contract tests (RemediationItem, RemediationItemFingerprint,
# ScanScopeSignature) + init_db idempotency for the three new tables.
# ---------------------------------------------------------------------------


def test_remediation_item_columns() -> None:
    from quirk.models import RemediationItem

    assert RemediationItem.__tablename__ == "remediation_items"

    col_names = {c.name for c in RemediationItem.__table__.columns}
    required = {
        "id", "slug", "scan_run_id", "title", "phase", "priority",
        "constituency", "state", "first_seen_scan_run_id", "created_at",
    }
    assert required.issubset(col_names), f"missing: {required - col_names}"

    cols = {c.name: c for c in RemediationItem.__table__.columns}
    assert cols["slug"].nullable is False
    assert cols["state"].nullable is False
    # everything else nullable per D-06
    for name in ("scan_run_id", "title", "phase", "priority", "constituency",
                 "first_seen_scan_run_id", "created_at"):
        assert cols[name].nullable is True, f"{name} should be nullable"

    # no ForeignKey — soft references only (D-03)
    assert not cols["scan_run_id"].foreign_keys


def test_remediation_item_fingerprint_columns() -> None:
    from quirk.models import RemediationItemFingerprint

    assert RemediationItemFingerprint.__tablename__ == "remediation_item_fingerprints"

    col_names = {c.name for c in RemediationItemFingerprint.__table__.columns}
    required = {
        "id", "remediation_item_id", "slug", "scan_run_id",
        "finding_fingerprint", "host", "port", "finding_title", "state",
        "observed_at",
    }
    assert required.issubset(col_names), f"missing: {required - col_names}"

    cols = {c.name: c for c in RemediationItemFingerprint.__table__.columns}
    assert cols["finding_fingerprint"].nullable is False
    assert cols["state"].nullable is False
    for name in ("remediation_item_id", "slug", "scan_run_id", "host",
                 "port", "finding_title", "observed_at"):
        assert cols[name].nullable is True, f"{name} should be nullable"

    assert not cols["remediation_item_id"].foreign_keys


def test_scan_scope_signature_columns() -> None:
    from quirk.models import ScanScopeSignature

    assert ScanScopeSignature.__tablename__ == "scan_scope_signatures"

    col_names = {c.name for c in ScanScopeSignature.__table__.columns}
    required = {
        "id", "scan_run_id", "signature_version", "port_scope", "profile",
        "extras_present", "credentials_present", "sensor_set",
        "probe_health_json", "digest", "created_at",
    }
    assert required.issubset(col_names), f"missing: {required - col_names}"

    cols = {c.name: c for c in ScanScopeSignature.__table__.columns}
    assert cols["scan_run_id"].nullable is False
    assert cols["digest"].nullable is False
    for name in ("signature_version", "port_scope", "profile",
                 "extras_present", "credentials_present", "sensor_set",
                 "probe_health_json", "created_at"):
        assert cols[name].nullable is True, f"{name} should be nullable"


def test_init_db_creates_three_new_tables_idempotently(tmp_path) -> None:
    from sqlalchemy import inspect as sa_inspect

    db_path = tmp_path / "remed.db"
    engine1 = init_db(str(db_path))
    names1 = set(sa_inspect(engine1).get_table_names())
    for table in ("remediation_items", "remediation_item_fingerprints", "scan_scope_signatures"):
        assert table in names1, f"{table} missing after first init_db()"

    # Second call must not raise and must leave the three tables present.
    engine2 = init_db(str(db_path))
    names2 = set(sa_inspect(engine2).get_table_names())
    assert names1 == names2


def test_remediation_item_roundtrip(tmp_path) -> None:
    """Create/query round-trip proves state is persisted NOT NULL and defaults honestly."""
    from quirk.models import RemediationItem

    db_path = tmp_path / "roundtrip.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        row = RemediationItem(
            slug="plaintext-http-exposure",
            scan_run_id="2026-09-02T00:00:00Z",
            title="Remove plaintext HTTP exposure",
            phase="NOW",
            priority=10,
            constituency="fingerprint",
            state="not_observed",
            created_at=datetime.datetime.utcnow(),
        )
        session.add(row)
        session.commit()

        fetched = session.query(RemediationItem).filter_by(slug="plaintext-http-exposure").one()
        assert fetched.state == "not_observed"
    finally:
        session.close()


def test_remediation_item_state_not_null(tmp_path) -> None:
    """Attempting to persist a NULL state must fail — state is NOT NULL (T-179-01)."""
    from sqlalchemy.exc import IntegrityError
    from quirk.models import RemediationItem

    db_path = tmp_path / "notnull.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        row = RemediationItem(
            slug="expired-certificates",
            scan_run_id="run-1",
            title="Replace expired certificates",
            state=None,
        )
        session.add(row)
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# Task 2: closed-set guard, not_observed vocabulary, item_progress fraction.
# ---------------------------------------------------------------------------


def _full_evidence() -> dict:
    """Evidence tuned to trigger every non-fallback branch of build_phased_roadmap."""
    return {
        "totals": {"endpoints": 10, "findings": 20},
        "protocol_counts": {"TLS": 5, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 1,
        "mtls_present_count": 1,
        "certificate_observations": {
            "expired_count": 1,
            "expiring_count": 1,
            "self_signed_count": 1,
        },
        "cert_key_type_counts": {"RSA": 5, "ECDSA": 0},
        "scan_error": {"rate": 0.3},
        "finding_severity_counts": {
            "CRITICAL": 0,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 1,
            "INFO": 1,
        },
        "tls_enum_coverage_ratio": 0.5,
    }


def _zero_endpoint_evidence() -> dict:
    """Evidence tuned to trigger the endpoints == 0 fallback branch."""
    return {
        "totals": {"endpoints": 0, "findings": 0},
        "protocol_counts": {},
        "plaintext_http_count": 0,
        "http_on_tls_port_count": 0,
        "mtls_present_count": 0,
        "certificate_observations": {},
        "cert_key_type_counts": {},
        "scan_error": {"rate": 0.0},
        "finding_severity_counts": {},
        "tls_enum_coverage_ratio": 1.0,
    }


def _all_emitted_titles() -> set:
    from quirk.intelligence.roadmap import build_phased_roadmap

    titles: set = set()

    # Force baseline items to also be emitted alongside driver-triggered
    # ones by raising min_items/max_items well above the natural count.
    full = build_phased_roadmap(_full_evidence(), {}, min_items=20, max_items=20)
    titles.update(item["title"] for item in full["items"])

    zero = build_phased_roadmap(_zero_endpoint_evidence(), {}, min_items=6, max_items=12)
    titles.update(item["title"] for item in zero["items"])

    return titles


def test_closed_set_guard_every_emitted_title_is_mapped_or_excluded() -> None:
    from quirk.intelligence.remediation import (
        REMEDIATION_KIND_SLUGS,
        REMEDIATION_EXCLUDED_TITLES,
    )

    emitted = _all_emitted_titles()
    assert emitted, "expected build_phased_roadmap to emit at least one title"

    unmapped = [
        t for t in emitted
        if t not in REMEDIATION_KIND_SLUGS and t not in REMEDIATION_EXCLUDED_TITLES
    ]
    assert not unmapped, f"emitted titles fall through the closed set: {unmapped}"

    # every excluded title must actually have fired at least once (sanity)
    assert REMEDIATION_EXCLUDED_TITLES.issubset(emitted), (
        "expected all 3 zero-endpoint fallback titles to fire; got "
        f"{emitted & REMEDIATION_EXCLUDED_TITLES}"
    )


def test_closed_set_guard_negative_control_can_fail() -> None:
    """Proves the guard actually detects an unmapped title."""
    from quirk.intelligence.remediation import (
        REMEDIATION_KIND_SLUGS,
        REMEDIATION_EXCLUDED_TITLES,
    )

    fabricated = "Totally fabricated title that no one emits"
    assert fabricated not in REMEDIATION_KIND_SLUGS
    assert fabricated not in REMEDIATION_EXCLUDED_TITLES


def test_all_14_titles_mapped_to_unique_slugs() -> None:
    from quirk.intelligence.remediation import REMEDIATION_KIND_SLUGS

    assert len(REMEDIATION_KIND_SLUGS) == 14
    assert len(set(REMEDIATION_KIND_SLUGS.values())) == 14


def test_excluded_titles_are_exactly_three() -> None:
    from quirk.intelligence.remediation import REMEDIATION_EXCLUDED_TITLES

    assert len(REMEDIATION_EXCLUDED_TITLES) == 3
    assert REMEDIATION_EXCLUDED_TITLES == frozenset(
        {
            "Collect initial asset scope",
            "Run baseline discovery and fingerprinting",
            "Establish recurring readiness reporting",
        }
    )


def test_slug_for_title_exact_match_and_none_for_excluded() -> None:
    from quirk.intelligence.remediation import slug_for_title

    assert slug_for_title("Remove plaintext HTTP exposure") == "plaintext-http-exposure"
    assert slug_for_title("Collect initial asset scope") is None
    assert slug_for_title("not a real title") is None


def test_item_states_and_default() -> None:
    from quirk.intelligence.remediation import ITEM_STATES, DEFAULT_ITEM_STATE

    assert ITEM_STATES == ("open", "closed", "not_observed", "resurfaced")
    assert DEFAULT_ITEM_STATE == "not_observed"


def test_open_like_states_includes_resurfaced() -> None:
    from quirk.intelligence.remediation import ITEM_STATES, OPEN_LIKE_STATES

    assert OPEN_LIKE_STATES == ("open", "resurfaced")
    for state in OPEN_LIKE_STATES:
        assert state in ITEM_STATES
    assert "closed" not in OPEN_LIKE_STATES
    assert "not_observed" not in OPEN_LIKE_STATES


def test_item_progress_returns_fraction_not_boolean(tmp_path) -> None:
    from quirk.models import RemediationItemFingerprint
    from quirk.intelligence.remediation import item_progress

    db_path = tmp_path / "progress.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        scan_run_id = "run-progress-1"
        slug = "plaintext-http-exposure"
        for i in range(8):
            state = "closed" if i < 6 else "open"
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
        assert result == (6, 8)
        assert result != (8, 8)
    finally:
        session.close()


def test_item_progress_zero_closed_never_reports_full(tmp_path) -> None:
    from quirk.models import RemediationItemFingerprint
    from quirk.intelligence.remediation import item_progress

    db_path = tmp_path / "progress_zero.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        scan_run_id = "run-progress-2"
        slug = "expired-certificates"
        for i in range(8):
            session.add(
                RemediationItemFingerprint(
                    slug=slug,
                    scan_run_id=scan_run_id,
                    finding_fingerprint=f"exp-{i}",
                    state="open",
                    observed_at=datetime.datetime.utcnow(),
                )
            )
        session.commit()

        result = item_progress(session, scan_run_id=scan_run_id, slug=slug)
        assert result == (0, 8)
        assert result != (8, 8)
    finally:
        session.close()
