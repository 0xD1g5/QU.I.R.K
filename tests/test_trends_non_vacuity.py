"""IDENT-02 non-vacuity + severity-transition guards for compute_trend_report().

Phase 178 Plan 02 (Wave 1): these tests are written and run RED, BEFORE any change to
`quirk/intelligence/trends.py`. Plan 178-05 (Wave 2) owns the fix and is bound to make
these tests pass (the xfail(strict=True) markers force removal at that point).

Measured production condition that motivates this file: `output/quirk.db`
`crypto_endpoints` has 30 rows, 0 non-NULL severity. `compute_trend_report`'s match key
is `(host, port, protocol, severity)` AND both `current_keys`/`previous_keys` filter on
`severity is not None` — so on real data the filter empties both sets before the key is
ever consulted, and the delta is empty by construction on every scan. The existing 10
tests in `tests/test_intelligence_trends.py` all pass because every one of them supplies
a non-NULL `severity` string — a condition that does not occur in production. A test
that cannot fail on vacuity is the real defect being closed here.

IMPORTANT: a bare non-emptiness check on the delta is explicitly NOT an acceptable
assertion anywhere in this file (e.g. asserting the delta's length is nonzero). A test
that only checks non-emptiness cannot distinguish a correct delta from a wrong one.
Every assertion below names the specific expected endpoint(s) or transition.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, CryptoEndpoint
from quirk.intelligence.trends import compute_trend_report


@pytest.fixture
def db():
    """In-memory SQLite session for trend unit tests (copied from
    tests/test_intelligence_trends.py's db fixture)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_ep(
    db,
    host: str,
    port: int,
    protocol: str,
    scanned_at: Optional[datetime] = None,
    scan_error: Optional[str] = None,
    severity: Optional[str] = None,
) -> CryptoEndpoint:
    """Create and persist a CryptoEndpoint. Unlike
    tests/test_intelligence_trends.py's `_make_ep`, `severity` here is a KEYWORD
    argument defaulting to None — severity-NULL is the default posture of this file,
    and severity-bearing rows are the explicit exception (the reverse of the existing
    suite, which requires a severity string at every call site and therefore never
    exercises the production-real NULL condition)."""
    ep = CryptoEndpoint(
        host=host,
        port=port,
        protocol=protocol,
        severity=severity,
        scanned_at=scanned_at,
        scan_error=scan_error,
    )
    db.add(ep)
    db.commit()
    return ep


T1 = datetime(2026, 9, 1, 10, 0, 0)
T2 = datetime(2026, 9, 2, 10, 0, 0)


@pytest.mark.xfail(
    reason=(
        "IDENT-02 RED: compute_trend_report filters severity is not None on both "
        "sides, so the delta is empty by construction; Plan 178-05 removes this marker"
    ),
    strict=True,
)
def test_all_null_severity_delta_is_not_vacuous(db):
    """Session A (T1) seeds a.example:443/TLS and b.example:22/SSH. Session B (T2)
    seeds a.example:443/TLS (unchanged) and c.example:8443/TLS (new). EVERY row has
    severity=None and scan_error=None — the production-real condition.

    c.example:8443 must be named as NEW; b.example:22 must be named as RESOLVED;
    a.example must appear in NEITHER list (it is unchanged across sessions).

    RED today: current_keys and previous_keys are both built with a
    `severity is not None` filter, so both sets are empty regardless of what rows
    exist, and new_findings_sample / resolved_findings_sample are both [].
    """
    _make_ep(db, "a.example", 443, "TLS", scanned_at=T1, severity=None)
    _make_ep(db, "b.example", 22, "SSH", scanned_at=T1, severity=None)
    _make_ep(db, "a.example", 443, "TLS", scanned_at=T2, severity=None)
    _make_ep(db, "c.example", 8443, "TLS", scanned_at=T2, severity=None)

    report = compute_trend_report(T2, T1, db)

    new_hosts_ports = {(s.host, s.port) for s in report.new_findings_sample}
    resolved_hosts_ports = {(s.host, s.port) for s in report.resolved_findings_sample}

    assert ("c.example", 8443) in new_hosts_ports, (
        f"expected c.example:8443 in new_findings_sample, got {new_hosts_ports}"
    )
    assert ("b.example", 22) in resolved_hosts_ports, (
        f"expected b.example:22 in resolved_findings_sample, got {resolved_hosts_ports}"
    )
    assert ("a.example", 443) not in new_hosts_ports
    assert ("a.example", 443) not in resolved_hosts_ports


@pytest.mark.xfail(
    reason=(
        "IDENT-02 RED: compute_trend_report filters severity is not None on both "
        "sides, so the delta is empty by construction; Plan 178-05 removes this marker"
    ),
    strict=True,
)
def test_all_null_severity_counts_are_reported_not_silently_zero(db):
    """Same fixture as test_all_null_severity_delta_is_not_vacuous. The report must
    expose a severity-agnostic count of new and resolved findings equal to 1 and 1
    respectively — a field that does not exist yet (Plan 178-05 adds it).

    RED today by AttributeError (TrendReport has no severity-agnostic total field),
    which is the correct RED shape: the field itself is part of the fix's contract.
    """
    _make_ep(db, "a.example", 443, "TLS", scanned_at=T1, severity=None)
    _make_ep(db, "b.example", 22, "SSH", scanned_at=T1, severity=None)
    _make_ep(db, "a.example", 443, "TLS", scanned_at=T2, severity=None)
    _make_ep(db, "c.example", 8443, "TLS", scanned_at=T2, severity=None)

    report = compute_trend_report(T2, T1, db)

    assert report.new_total == 1
    assert report.resolved_total == 1


@pytest.mark.xfail(
    reason=(
        "IDENT-02 RED: compute_trend_report filters severity is not None on both "
        "sides, so the delta is empty by construction; Plan 178-05 removes this marker"
    ),
    strict=True,
)
def test_protocol_null_does_not_reintroduce_vacuity(db):
    """Closes RESEARCH.md Assumption A1: dropping severity from the match key must
    not simply move the vacuity one field to the right if `protocol` is also NULL on
    real data. Every row here has BOTH severity=None and protocol=None.

    Session A (T1): a.example:443 and b.example:22, protocol=None throughout.
    Session B (T2): a.example:443 (unchanged) and c.example:8443 (new).

    c.example:8443 must be named as NEW; b.example:22 must be named as RESOLVED,
    even with protocol=None on every row. RED today for the same reason as above:
    severity is not None empties both key sets before protocol is ever consulted.
    """
    _make_ep(db, "a.example", 443, None, scanned_at=T1, severity=None)
    _make_ep(db, "b.example", 22, None, scanned_at=T1, severity=None)
    _make_ep(db, "a.example", 443, None, scanned_at=T2, severity=None)
    _make_ep(db, "c.example", 8443, None, scanned_at=T2, severity=None)

    report = compute_trend_report(T2, T1, db)

    new_hosts_ports = {(s.host, s.port) for s in report.new_findings_sample}
    resolved_hosts_ports = {(s.host, s.port) for s in report.resolved_findings_sample}

    assert ("c.example", 8443) in new_hosts_ports
    assert ("b.example", 22) in resolved_hosts_ports
    assert ("a.example", 443) not in new_hosts_ports
    assert ("a.example", 443) not in resolved_hosts_ports


# ---------------------------------------------------------------------------
# Severity-transition guard (Task 2)
#
# D-03 (documented in trends.py's compute_trend_report docstring) intentionally
# included severity in the match key so a HIGH->MEDIUM transition surfaces as
# "1 HIGH resolved + 1 MEDIUM new". Dropping severity from the identity key (per
# 178-CONTEXT.md's "Drop severity from the match key; report severity transitions
# separately") REPLACES this encoding, it does not abandon it: the partial-
# remediation signal must still be visible, just as an explicit transition record
# rather than as a finding-identity change. These two tests pin that replacement
# contract before Plan 178-05 implements it.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "IDENT-02 RED: TrendReport has no severity_transitions field yet; "
        "Plan 178-05 adds it and removes this marker"
    ),
    strict=True,
)
def test_severity_transition_reported_once_not_as_new_plus_resolved(db):
    """a.example:443/TLS is present in BOTH sessions: severity=HIGH in session A,
    severity=MEDIUM in session B (same host/port/protocol — unchanged endpoint,
    partial remediation). The report must expose exactly one severity transition
    naming (a.example, 443, TLS, previous="HIGH", current="MEDIUM"), and a.example
    must NOT appear in new_findings_sample nor resolved_findings_sample (it is a
    transition, not a new-plus-resolved pair).

    RED today by AttributeError: report.severity_transitions does not exist yet.
    """
    _make_ep(db, "a.example", 443, "TLS", scanned_at=T1, severity="HIGH")
    _make_ep(db, "a.example", 443, "TLS", scanned_at=T2, severity="MEDIUM")

    report = compute_trend_report(T2, T1, db)

    transitions = report.severity_transitions
    matching = [
        t
        for t in transitions
        if t.host == "a.example"
        and t.port == 443
        and t.protocol == "TLS"
        and t.previous_severity == "HIGH"
        and t.current_severity == "MEDIUM"
    ]
    assert len(matching) == 1, (
        f"expected exactly one HIGH->MEDIUM transition for a.example:443, "
        f"got {transitions}"
    )

    new_hosts_ports = {(s.host, s.port) for s in report.new_findings_sample}
    resolved_hosts_ports = {(s.host, s.port) for s in report.resolved_findings_sample}
    assert ("a.example", 443) not in new_hosts_ports
    assert ("a.example", 443) not in resolved_hosts_ports


def test_severity_bucket_counts_still_work_when_severity_is_populated(db):
    """Green regression guard: a mixed scenario with real severity strings on every
    row must keep producing the same new_high/resolved_low etc. bucket counts the
    existing suite expects. This test is NOT marked xfail — it must stay green
    through Plan 178-05's change, guarding against a regression of D-05 bucketing
    while the match key is being fixed.
    """
    _make_ep(db, "a.example", 443, "TLS", scanned_at=T1, severity="HIGH")
    _make_ep(db, "b.example", 443, "TLS", scanned_at=T1, severity="LOW")
    _make_ep(db, "c.example", 22, "SSH", scanned_at=T1, severity="MEDIUM")

    _make_ep(db, "d.example", 8443, "TLS", scanned_at=T2, severity="HIGH")
    _make_ep(db, "c.example", 22, "SSH", scanned_at=T2, severity="MEDIUM")

    report = compute_trend_report(T2, T1, db)

    assert report.new_high == 1
    assert report.new_medium == 0
    assert report.new_low == 0
    assert report.resolved_high == 1
    assert report.resolved_medium == 0
    assert report.resolved_low == 1
