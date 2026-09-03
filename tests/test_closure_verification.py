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

import ast
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
    include_current_signature=True,
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
        if include_current_signature:
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
    """A MISSING signature is NOT-COMPARABLE, never comparable-by-default.

    Prior-scan selection is drawn from ScanScopeSignature itself (D-25's key link), so a
    prior scan candidate always HAS a signature by construction. The realistic path to
    this refusal is the CURRENT scan's own signature being absent — e.g. scope-signature
    persistence failed independently of remediation persistence (both are advisory
    bookkeeping that can fail without failing the scan).
    """
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(tmp_path, include_current_signature=False)
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
    """closure.py's module docstring MUST explain why trends.py's helper is not used
    (T-180-22) — so this checks for actual IMPORT/CALL usage, not the prose mention.
    """
    source = Path("quirk/intelligence/closure.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(from|import)\s+quirk\.dashboard", source, re.MULTILINE)
    assert "_list_session_timestamps(" not in source
    assert "import quirk.dashboard" not in source
    assert "trends._list_session_timestamps" not in source


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




# ---------------------------------------------------------------------------
# CLOSE-01 (D-28): no human-assert affordance
# ---------------------------------------------------------------------------
_FORBIDDEN_ARG_RE = re.compile(r"(?i)(force|manual|assert|mark|override).*(clos|remediat)")
_ANY_CLOSE_OPTION_RE = re.compile(r"(?i)clos")
_ADD_ARGUMENT_RE = re.compile(r"add_argument\(\s*([^)]*)\)")


def _strip_comments_and_docstrings(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _scan_for_add_argument_violations(text: str):
    cleaned = _strip_comments_and_docstrings(text)
    violations = []
    for match in _ADD_ARGUMENT_RE.finditer(cleaned):
        call_args = match.group(1)
        if _FORBIDDEN_ARG_RE.search(call_args) or _ANY_CLOSE_OPTION_RE.search(call_args):
            violations.append(call_args)
    return violations


def test_no_human_assert_closure_affordance_in_cli():
    files = [Path("run_scan.py")]
    cli_dir = Path("quirk/cli")
    if cli_dir.exists():
        files.extend(sorted(cli_dir.rglob("*.py")))

    violations = []
    for f in files:
        if not f.exists():
            continue
        violations.extend(
            f"{f}: {v}" for v in _scan_for_add_argument_violations(f.read_text(encoding="utf-8"))
        )

    assert violations == [], f"human-assert closure affordance found: {violations}"


def test_no_human_assert_closure_key_in_config():
    config_source = _strip_comments_and_docstrings(Path("quirk/config.py").read_text(encoding="utf-8"))
    attr_pattern = re.compile(r"(?i)\b\w*(clos|resurfac)\w*\b")
    hits = attr_pattern.findall(config_source)
    assert hits == [], f"closure/resurface-named attribute found in quirk/config.py: {hits}"

    env_pattern = re.compile(r"(?i)QUIRK_[A-Z0-9_]*CLOS[A-Z0-9_]*")
    env_hits = []
    for f in sorted(Path("quirk").rglob("*.py")):
        text = _strip_comments_and_docstrings(f.read_text(encoding="utf-8"))
        found = env_pattern.findall(text)
        if found:
            env_hits.extend(f"{f}: {h}" for h in found)
    assert env_hits == [], f"closure-named env var found: {env_hits}"


def test_compute_closure_accepts_no_state_argument():
    from quirk.intelligence.closure import compute_closure

    assert tuple(inspect.signature(compute_closure).parameters) == ("db_path", "scan_run_id")


def test_human_assert_regex_negative_control():
    """A guard that can only pass is not a guard — prove it can fail."""
    fixture_source = (
        'parser.add_argument("--force-closed", dest="force_closed", '
        'help="Manually mark a remediation item as closed")\n'
    )
    violations = _scan_for_add_argument_violations(fixture_source)
    assert violations, "negative control fixture should have tripped the human-assert guard"


# ---------------------------------------------------------------------------
# CLOSE-02 (D-29..D-32): resurfaced
#
# A previously-`closed` fingerprint detected again becomes `resurfaced` — not
# a brand-new finding, not silently folded back into `open`. It can close
# again (a `reclosed` event, state `closed`), and the earlier `resurfaced`
# event row is retained forever (append-only, per test_closure_events.py's
# guard) so "closed once, regressed, closed again" stays legible. A scope
# mismatch refuses resurfacing exactly like it refuses closing — the same
# `scans_are_comparable` gate, never a second one.
# ---------------------------------------------------------------------------


def test_resurfaced_when_previously_closed_item_detected_again(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(
        tmp_path,
        prior_fingerprint_state="closed",
        include_current_fingerprint=True,
    )
    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["resurfaced"] == 1
    with get_session(db_path) as session:
        current_row = _fp_row(session, scan_run_id=CURRENT_SCAN_ID)
        assert current_row.state == "resurfaced"
        assert current_row.state != "open"
        assert current_row.state != "not_observed"

        # The prior row itself is untouched — it stays a record of the
        # ORIGINAL closure, not silently overwritten.
        prior_row = _fp_row(session, scan_run_id=PRIOR_SCAN_ID)
        assert prior_row.state == "closed"

        events = _events(session, event_type="resurfaced")
        assert len(events) == 1
        assert events[0].from_state == "closed"
        assert events[0].to_state == "resurfaced"
        assert events[0].slug == SLUG
        assert events[0].finding_fingerprint == FINGERPRINT


def test_resurfaced_is_not_a_new_finding(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(
        tmp_path,
        prior_fingerprint_state="closed",
        include_current_fingerprint=True,
    )
    compute_closure(db_path, CURRENT_SCAN_ID)

    with get_session(db_path) as session:
        current_row = _fp_row(session, scan_run_id=CURRENT_SCAN_ID)
        prior_row = _fp_row(session, scan_run_id=PRIOR_SCAN_ID)
        # Same fingerprint on both sides — the whole point is it is not re-keyed.
        assert current_row.finding_fingerprint == prior_row.finding_fingerprint == FINGERPRINT


def _seed_signature(session, *, scan_run_id, created_at, digest="digest-resurf", target_set_digest="tsd-resurf", probe_health=None):
    session.add(
        ScanScopeSignature(
            scan_run_id=scan_run_id,
            signature_version="2.0.0",
            digest=digest,
            target_set_digest=target_set_digest,
            probe_health_json=json.dumps(probe_health if probe_health is not None else HEALTHY_TLS),
            created_at=created_at,
        )
    )


def test_resurfaced_can_close_again_and_history_is_retained(tmp_path):
    """CLOSE-02 acceptance test: closed -> resurfaced -> reclosed, with the
    resurfaced event row STILL PRESENT after the reclosure.
    """
    from quirk.intelligence.closure import compute_closure

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    now = datetime.now(timezone.utc)
    scan1, scan2, scan3, scan4 = "scan-r1", "scan-r2", "scan-r3", "scan-r4"

    # Scan 1: fingerprint detected, open.
    with get_session(db_path) as session:
        _seed_signature(session, scan_run_id=scan1, created_at=now - timedelta(days=4))
        session.add(
            RemediationItemFingerprint(
                remediation_item_id=None,
                slug=SLUG,
                scan_run_id=scan1,
                finding_fingerprint=FINGERPRINT,
                host=HOST,
                port=PORT,
                finding_title="Plaintext HTTP service detected",
                state="open",
                observed_at=now - timedelta(days=4),
            )
        )
        session.commit()

    # Scan 2: rechecked, absent, healthy probe -> closes.
    with get_session(db_path) as session:
        _seed_signature(session, scan_run_id=scan2, created_at=now - timedelta(days=3))
        session.add(CryptoEndpoint(host=HOST, port=PORT, protocol=PROTOCOL, scan_run_id=scan2))
        session.commit()
    counters2 = compute_closure(db_path, scan2)
    assert counters2["closed"] == 1

    # Scan 3: detected again -> resurfaced.
    with get_session(db_path) as session:
        _seed_signature(session, scan_run_id=scan3, created_at=now - timedelta(days=2))
        session.add(
            RemediationItemFingerprint(
                remediation_item_id=None,
                slug=SLUG,
                scan_run_id=scan3,
                finding_fingerprint=FINGERPRINT,
                host=HOST,
                port=PORT,
                finding_title="Plaintext HTTP service detected",
                state="not_observed",
                observed_at=now - timedelta(days=2),
            )
        )
        session.commit()
    counters3 = compute_closure(db_path, scan3)
    assert counters3["resurfaced"] == 1

    with get_session(db_path) as session:
        row3 = _fp_row(session, scan_run_id=scan3)
        assert row3.state == "resurfaced"

    # Scan 4: rechecked with a healthy probe, absent -> recloses.
    with get_session(db_path) as session:
        _seed_signature(session, scan_run_id=scan4, created_at=now - timedelta(days=1))
        session.add(CryptoEndpoint(host=HOST, port=PORT, protocol=PROTOCOL, scan_run_id=scan4))
        session.commit()
    counters4 = compute_closure(db_path, scan4)
    assert counters4["reclosed"] == 1

    with get_session(db_path) as session:
        row3_after = _fp_row(session, scan_run_id=scan3)
        assert row3_after.state == "closed"

        events = (
            session.query(RemediationClosureEvent)
            .filter(
                RemediationClosureEvent.slug == SLUG,
                RemediationClosureEvent.finding_fingerprint == FINGERPRINT,
            )
            .order_by(RemediationClosureEvent.id.asc())
            .all()
        )
        assert [e.event_type for e in events] == ["closed", "resurfaced", "reclosed"]
        # The resurfaced row SURVIVES the later reclosure — never rewritten.
        assert events[1].from_state == "closed"
        assert events[1].to_state == "resurfaced"
        assert events[2].from_state == "resurfaced"
        assert events[2].to_state == "closed"


def test_scope_mismatch_cannot_produce_resurfaced(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(
        tmp_path,
        prior_fingerprint_state="closed",
        include_current_fingerprint=True,
        current_digest="digest-mismatch",
    )
    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["refused_scope_mismatch"] == 1
    assert counters.get("resurfaced", 0) == 0
    with get_session(db_path) as session:
        current_row = _fp_row(session, scan_run_id=CURRENT_SCAN_ID)
        assert current_row.state == "not_observed"
        assert _events(session, event_type="resurfaced") == []


def test_missing_signature_cannot_produce_resurfaced(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(
        tmp_path,
        prior_fingerprint_state="closed",
        include_current_fingerprint=True,
        include_current_signature=False,
    )
    counters = compute_closure(db_path, CURRENT_SCAN_ID)

    assert counters["refused_missing_signature"] == 1
    assert counters.get("resurfaced", 0) == 0
    with get_session(db_path) as session:
        assert _events(session, event_type="resurfaced") == []


def test_resurfaced_counted_as_open_reported_separately(tmp_path):
    from quirk.intelligence.closure import closure_counts

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    now = datetime.now(timezone.utc)
    scan_run_id = "scan-counts-1"

    counts_spec = {"open": 2, "resurfaced": 3, "closed": 4, "not_observed": 1}
    with get_session(db_path) as session:
        i = 0
        for state, n in counts_spec.items():
            for _ in range(n):
                i += 1
                session.add(
                    RemediationItemFingerprint(
                        remediation_item_id=None,
                        slug=SLUG,
                        scan_run_id=scan_run_id,
                        finding_fingerprint=f"fp-count-{i:04d}",
                        host=HOST,
                        port=PORT,
                        finding_title="Plaintext HTTP service detected",
                        state=state,
                        observed_at=now,
                    )
                )
        session.commit()

        result = closure_counts(session, scan_run_id=scan_run_id)

    assert result == {
        "open": 2,
        "resurfaced": 3,
        "closed": 4,
        "not_observed": 1,
        "open_like": 5,
    }


def test_item_progress_unchanged_by_resurfaced(tmp_path):
    from quirk.intelligence.remediation import item_progress

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    now = datetime.now(timezone.utc)
    scan_run_id = "scan-counts-2"

    counts_spec = {"open": 2, "resurfaced": 3, "closed": 4, "not_observed": 1}
    with get_session(db_path) as session:
        i = 0
        for state, n in counts_spec.items():
            for _ in range(n):
                i += 1
                session.add(
                    RemediationItemFingerprint(
                        remediation_item_id=None,
                        slug=SLUG,
                        scan_run_id=scan_run_id,
                        finding_fingerprint=f"fp-progress-{i:04d}",
                        host=HOST,
                        port=PORT,
                        finding_title="Plaintext HTTP service detected",
                        state=state,
                        observed_at=now,
                    )
                )
        session.commit()

        result = item_progress(session, scan_run_id=scan_run_id, slug=SLUG)

    assert result == (4, 10)


def test_resurface_is_idempotent(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = _seed_two_scans(
        tmp_path,
        prior_fingerprint_state="closed",
        include_current_fingerprint=True,
    )
    first = compute_closure(db_path, CURRENT_SCAN_ID)
    with get_session(db_path) as session:
        first_state = _fp_row(session, scan_run_id=CURRENT_SCAN_ID).state
        first_event_count = session.query(RemediationClosureEvent).filter(
            RemediationClosureEvent.event_type == "resurfaced"
        ).count()

    second = compute_closure(db_path, CURRENT_SCAN_ID)
    with get_session(db_path) as session:
        second_state = _fp_row(session, scan_run_id=CURRENT_SCAN_ID).state
        second_event_count = session.query(RemediationClosureEvent).filter(
            RemediationClosureEvent.event_type == "resurfaced"
        ).count()

    assert first["resurfaced"] == 1
    assert second["resurfaced"] == 0
    assert first_state == second_state == "resurfaced"
    assert first_event_count == second_event_count == 1


# ---------------------------------------------------------------------------
# CLOSE-02 Task 3: durability, "the event table is not a decision input", and
# a scalar-shape guard.
# ---------------------------------------------------------------------------


def test_closure_counts_never_returns_a_scalar(tmp_path):
    from quirk.intelligence.closure import closure_counts
    from quirk.intelligence.remediation import ITEM_STATES

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    now = datetime.now(timezone.utc)
    scan_run_id = "scan-scalar-shape"

    with get_session(db_path) as session:
        session.add(
            RemediationItemFingerprint(
                remediation_item_id=None,
                slug=SLUG,
                scan_run_id=scan_run_id,
                finding_fingerprint="fp-only-one",
                host=HOST,
                port=PORT,
                finding_title="Plaintext HTTP service detected",
                state="open",
                observed_at=now,
            )
        )
        session.commit()

        result = closure_counts(session, scan_run_id=scan_run_id)

    assert set(result.keys()) == set(ITEM_STATES) | {"open_like"}
    assert result["open"] == 1
    assert result["closed"] == 0
    assert result["resurfaced"] == 0
    assert result["not_observed"] == 0


def test_resurfaced_event_survives_a_database_reopen(tmp_path):
    from quirk.intelligence.closure import compute_closure

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    now = datetime.now(timezone.utc)
    scan1, scan2, scan3, scan4 = "scan-reopen-1", "scan-reopen-2", "scan-reopen-3", "scan-reopen-4"

    with get_session(db_path) as session:
        _seed_signature(session, scan_run_id=scan1, created_at=now - timedelta(days=4))
        session.add(
            RemediationItemFingerprint(
                remediation_item_id=None,
                slug=SLUG,
                scan_run_id=scan1,
                finding_fingerprint=FINGERPRINT,
                host=HOST,
                port=PORT,
                finding_title="Plaintext HTTP service detected",
                state="open",
                observed_at=now - timedelta(days=4),
            )
        )
        session.commit()

    with get_session(db_path) as session:
        _seed_signature(session, scan_run_id=scan2, created_at=now - timedelta(days=3))
        session.add(CryptoEndpoint(host=HOST, port=PORT, protocol=PROTOCOL, scan_run_id=scan2))
        session.commit()
    compute_closure(db_path, scan2)

    with get_session(db_path) as session:
        _seed_signature(session, scan_run_id=scan3, created_at=now - timedelta(days=2))
        session.add(
            RemediationItemFingerprint(
                remediation_item_id=None,
                slug=SLUG,
                scan_run_id=scan3,
                finding_fingerprint=FINGERPRINT,
                host=HOST,
                port=PORT,
                finding_title="Plaintext HTTP service detected",
                state="not_observed",
                observed_at=now - timedelta(days=2),
            )
        )
        session.commit()
    compute_closure(db_path, scan3)

    with get_session(db_path) as session:
        _seed_signature(session, scan_run_id=scan4, created_at=now - timedelta(days=1))
        session.add(CryptoEndpoint(host=HOST, port=PORT, protocol=PROTOCOL, scan_run_id=scan4))
        session.commit()
    compute_closure(db_path, scan4)

    # Close every prior session and open a FRESH one — the durability claim is that
    # the history is on disk, not an artifact of an in-memory object graph.
    with get_session(db_path) as session:
        events = (
            session.query(RemediationClosureEvent)
            .filter(
                RemediationClosureEvent.slug == SLUG,
                RemediationClosureEvent.finding_fingerprint == FINGERPRINT,
            )
            .order_by(RemediationClosureEvent.id.asc())
            .all()
        )
        assert [e.event_type for e in events] == ["closed", "resurfaced", "reclosed"]


# ---------------------------------------------------------------------------
# D-29: the event table is a RECORD, never an INPUT to a transition decision.
# ---------------------------------------------------------------------------
def _compute_closure_reads_closure_event_table(source: str) -> bool:
    """AST-walk `source`, return True iff the `compute_closure` function body
    contains a `query(...)` call referencing `RemediationClosureEvent` anywhere
    in its argument chain — an AST walk, not a substring scan, so a docstring's
    prose mention of the model name (as this module's own docstring has) can
    never produce a false positive.
    """
    tree = ast.parse(source)
    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "compute_closure":
            target = node
            break
    if target is None:
        return False

    for node in ast.walk(target):
        if isinstance(node, ast.Call):
            func = node.func
            is_query_call = (
                isinstance(func, ast.Attribute) and func.attr == "query"
            )
            if not is_query_call:
                continue
            for arg in node.args:
                for sub in ast.walk(arg):
                    if isinstance(sub, ast.Name) and sub.id == "RemediationClosureEvent":
                        return True
    return False


def test_no_transition_reads_the_event_table():
    source = Path("quirk/intelligence/closure.py").read_text(encoding="utf-8")
    assert not _compute_closure_reads_closure_event_table(source), (
        "compute_closure must decide transitions from persisted fingerprint "
        "state only (D-29) — it must never query RemediationClosureEvent"
    )

    # Negative control: prove the AST walk CAN detect a real violation.
    fixture_source = (
        "def compute_closure(db_path, scan_run_id):\n"
        "    with get_session(db_path) as session:\n"
        "        prior = session.query(RemediationClosureEvent).filter(\n"
        "            RemediationClosureEvent.slug == 'x'\n"
        "        ).all()\n"
        "        return prior\n"
    )
    assert _compute_closure_reads_closure_event_table(fixture_source), (
        "negative control fixture should have tripped the D-29 AST-walk guard"
    )
