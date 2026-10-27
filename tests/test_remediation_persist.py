"""Phase 179 Plan 03: scan-time persistence of remediation items + fingerprints.

Covers `persist_remediation_snapshot` — the fix for the concrete defect:
today `_add_candidate` merges by title and persists nothing, so 8 plaintext
endpoints read as "fixing 1 closes nothing, fixing the 8th vanishes the
item, rewording the title re-keys the history." This module proves progress
is expressible as a fraction (`(0, 8)`, never `(8, 8)`, never a boolean) and
that no row is ever written "closed" — that is Phase 180's word to write.
"""
from __future__ import annotations

import inspect

import pytest

from quirk.db import get_session, init_db
from quirk.intelligence.remediation import ITEM_STATES, item_progress
from quirk.intelligence.remediation_persist import persist_remediation_snapshot
from quirk.models import CryptoEndpoint, RemediationItem, RemediationItemFingerprint

SCAN_RUN_ID = "2026-09-02T00:00:00Z"


def _endpoint(host: str, port: int, protocol: str = "HTTP") -> CryptoEndpoint:
    return CryptoEndpoint(host=host, port=port, protocol=protocol)


def _plaintext_finding(host: str, port: int) -> dict:
    return {
        "host": host,
        "port": port,
        "title": "Plaintext HTTP service detected",
        "severity": "MEDIUM",
        "recommendation": "Terminate TLS at this endpoint.",
    }


def _eight_plaintext_endpoints_and_findings():
    endpoints = [_endpoint(f"host{i}.example.com", 80 + i) for i in range(8)]
    findings = [_plaintext_finding(f"host{i}.example.com", 80 + i) for i in range(8)]
    return endpoints, findings


def test_eight_plaintext_endpoints_persist_as_zero_of_eight(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()

    counters = persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)

    assert counters["items"] >= 1
    assert counters["fingerprints"] == 8

    with get_session(db_path) as session:
        fraction = item_progress(
            session, scan_run_id=SCAN_RUN_ID, slug="plaintext-http-exposure"
        )
        assert fraction == (0, 8)

        item = (
            session.query(RemediationItem)
            .filter(
                RemediationItem.slug == "plaintext-http-exposure",
                RemediationItem.scan_run_id == SCAN_RUN_ID,
            )
            .one()
        )
        assert item.constituency == "fingerprint"
        assert item.state != "closed"

        fp_rows = (
            session.query(RemediationItemFingerprint)
            .filter(
                RemediationItemFingerprint.scan_run_id == SCAN_RUN_ID,
                RemediationItemFingerprint.slug == "plaintext-http-exposure",
            )
            .all()
        )
        assert len(fp_rows) == 8


def test_fixing_one_of_eight_never_produced_by_this_module(tmp_path) -> None:
    """This module never writes 'closed' — a 1-of-8 fix is Phase 180's job.

    Re-running the SAME scan_run_id against unchanged findings must not
    silently drop the item just because one host "looks fixed" in a
    subsequent evidence pass — that is exactly the vanishing-item defect
    this plan closes. Prove idempotent re-persistence keeps all 8 rows.
    """
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)
    counters_second = persist_remediation_snapshot(
        db_path, SCAN_RUN_ID, endpoints, findings
    )

    # Idempotent: the unique constraint means the second call adds nothing.
    assert counters_second["fingerprints"] == 0

    with get_session(db_path) as session:
        fraction = item_progress(
            session, scan_run_id=SCAN_RUN_ID, slug="plaintext-http-exposure"
        )
        assert fraction == (0, 8)


def test_no_written_row_has_closed_state(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)

    with get_session(db_path) as session:
        for item in session.query(RemediationItem).all():
            assert item.state in ITEM_STATES
            assert item.state != "closed"
        for fp in session.query(RemediationItemFingerprint).all():
            assert fp.state in ITEM_STATES
            assert fp.state != "closed"


def test_evidence_only_item_has_zero_join_rows(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    # scan_error.count > 0 triggers "Increase scan coverage" (Phase 234 review
    # D-31; it was rate >= 0.2) (slug=scan-reliability,
    # constituency=evidence_only) in build_phased_roadmap.
    endpoints = [_endpoint(f"host{i}.example.com", 443, protocol="TLS") for i in range(5)]
    for i, ep in enumerate(endpoints):
        if i < 2:
            ep.scan_error = "connection timeout"
    findings: list = []

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)

    with get_session(db_path) as session:
        item = (
            session.query(RemediationItem)
            .filter(
                RemediationItem.slug == "scan-reliability",
                RemediationItem.scan_run_id == SCAN_RUN_ID,
            )
            .one_or_none()
        )
        assert item is not None
        assert item.constituency == "evidence_only"
        assert item.state == "not_observed"

        fp_rows = (
            session.query(RemediationItemFingerprint)
            .filter(
                RemediationItemFingerprint.scan_run_id == SCAN_RUN_ID,
                RemediationItemFingerprint.slug == "scan-reliability",
            )
            .all()
        )
        assert fp_rows == []


def test_excluded_fallback_titles_produce_no_item_row(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    # Zero endpoints forces build_phased_roadmap's endpoints==0 fallback
    # branch, which emits the 3 REMEDIATION_EXCLUDED_TITLES alongside the
    # 3 deterministic evidence_only baseline items (which DO have slugs).
    counters = persist_remediation_snapshot(db_path, SCAN_RUN_ID, [], [])

    assert counters["skipped_findings"] == 3

    with get_session(db_path) as session:
        titles = {
            item.title for item in session.query(RemediationItem).all()
        }
        from quirk.intelligence.remediation import REMEDIATION_EXCLUDED_TITLES

        assert titles.isdisjoint(REMEDIATION_EXCLUDED_TITLES)


def test_second_call_same_scan_run_id_is_idempotent(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)
    with get_session(db_path) as session:
        items_before = session.query(RemediationItem).count()
        fps_before = session.query(RemediationItemFingerprint).count()

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)
    with get_session(db_path) as session:
        items_after = session.query(RemediationItem).count()
        fps_after = session.query(RemediationItemFingerprint).count()

    assert items_after == items_before
    assert fps_after == fps_before


def test_unmatched_finding_title_is_silently_unattached(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()
    # A finding whose title matches no constituency tuple at all.
    findings.append(
        {
            "host": "weird.example.com",
            "port": 9999,
            "title": "Some completely unrecognised finding title",
            "severity": "LOW",
            "recommendation": "n/a",
        }
    )

    counters = persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)

    # Still exactly 8 join rows for plaintext-http-exposure — the unmatched
    # finding attached to nothing, and did not raise.
    assert counters["fingerprints"] == 8

    with get_session(db_path) as session:
        all_titles = {
            fp.finding_title
            for fp in session.query(RemediationItemFingerprint).all()
        }
        assert "Some completely unrecognised finding title" not in all_titles


def test_severity_constituency_two_of_three_join_rows(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints = [_endpoint(f"sev{i}.example.com", 443, protocol="TLS") for i in range(3)]
    findings = [
        {
            "host": "sev0.example.com",
            "port": 443,
            "title": "Weak signature algorithm in use",
            "severity": "HIGH",
            "recommendation": "n/a",
        },
        {
            "host": "sev1.example.com",
            "port": 443,
            "title": "Deprecated key exchange",
            "severity": "CRITICAL",
            "recommendation": "n/a",
        },
        {
            "host": "sev2.example.com",
            "port": 443,
            "title": "Informational note",
            "severity": "LOW",
            "recommendation": "n/a",
        },
    ]

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)

    with get_session(db_path) as session:
        item = (
            session.query(RemediationItem)
            .filter(
                RemediationItem.slug == "high-impact-findings",
                RemediationItem.scan_run_id == SCAN_RUN_ID,
            )
            .one()
        )
        assert item.constituency == "severity"

        fp_rows = (
            session.query(RemediationItemFingerprint)
            .filter(
                RemediationItemFingerprint.scan_run_id == SCAN_RUN_ID,
                RemediationItemFingerprint.slug == "high-impact-findings",
            )
            .all()
        )
        assert len(fp_rows) == 2
        severities = {fp.finding_title for fp in fp_rows}
        assert severities == {"Weak signature algorithm in use", "Deprecated key exchange"}


def test_score_neutral_high_finding_is_not_a_high_impact_constituent(tmp_path) -> None:
    """D-25: a HIGH finding in a score-neutral category is real, but it is not
    one of the high-impact item's constituents, so it never holds the item
    open or shows up in its progress."""
    from quirk.intelligence.evidence import SCORE_NEUTRAL_FINDING_CATEGORIES

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints = [_endpoint(f"neu{i}.example.com", 443, protocol="TLS") for i in range(2)]
    neutral_category = sorted(SCORE_NEUTRAL_FINDING_CATEGORIES)[0]
    findings = [
        {
            "host": "neu0.example.com",
            "port": 443,
            "title": "Weak signature algorithm in use",
            "severity": "HIGH",
            "recommendation": "n/a",
        },
        {
            "host": "neu1.example.com",
            "port": 443,
            "title": "JWKS fetched with TLS certificate verification disabled",
            "severity": "HIGH",
            "category": neutral_category,
            "recommendation": "n/a",
        },
    ]

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)

    with get_session(db_path) as session:
        fp_rows = (
            session.query(RemediationItemFingerprint)
            .filter(
                RemediationItemFingerprint.scan_run_id == SCAN_RUN_ID,
                RemediationItemFingerprint.slug == "high-impact-findings",
            )
            .all()
        )
        assert {fp.finding_title for fp in fp_rows} == {"Weak signature algorithm in use"}
        closed, total = item_progress(session, scan_run_id=SCAN_RUN_ID, slug="high-impact-findings")
        assert total == 1


def test_persist_never_writes_closed_literal_in_source() -> None:
    """Grep-style guard mirrored as a test: no literal "closed" anywhere.

    That is Phase 180's word to write, and only after its two-sided
    condition holds.
    """
    import quirk.intelligence.remediation_persist as mod

    source = inspect.getsource(mod)
    assert '"closed"' not in source


def test_no_db_path_or_scan_run_id_returns_zeroed_counters_without_raising(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()

    counters = persist_remediation_snapshot(db_path, None, endpoints, findings)
    assert counters == {"items": 0, "fingerprints": 0, "skipped_findings": 0}

    counters = persist_remediation_snapshot(None, SCAN_RUN_ID, endpoints, findings)
    assert counters == {"items": 0, "fingerprints": 0, "skipped_findings": 0}


# ---------------------------------------------------------------------------
# Task 2: call-site ordering guard — cheap, does not require running a scan.
# ---------------------------------------------------------------------------


def test_run_scan_wires_remediation_persist_between_db_persist_and_reporting() -> None:
    import run_scan

    source = inspect.getsource(run_scan.main)

    assert "persist_remediation_snapshot" in source
    assert '"remediation_persist"' in source

    db_persist_idx = source.index('"db_persist"')
    remediation_idx = source.index('"remediation_persist"')
    reporting_idx = source.index('"reporting"')

    assert db_persist_idx < remediation_idx < reporting_idx


# ---------------------------------------------------------------------------
# Plan 06 close-out addendum: `_SLUG_PRIORITY` is a second hand-maintained
# table that mirrors REMEDIATION_KIND_SLUGS's inline priority comments with
# nothing but a comment linking them (179-03 deviation, flagged in
# 179-CONTEXT.md's addendum). This guard makes drift between the two key
# sets fail loudly instead of silently defaulting `priority=None` for a slug
# that was added to one table but not the other.
# ---------------------------------------------------------------------------


def test_slug_priority_key_set_matches_kind_slugs() -> None:
    from quirk.intelligence.remediation import REMEDIATION_KIND_SLUGS
    from quirk.intelligence.remediation_persist import _SLUG_PRIORITY

    kind_slugs = set(REMEDIATION_KIND_SLUGS.values())
    priority_slugs = set(_SLUG_PRIORITY.keys())

    missing_priority = kind_slugs - priority_slugs
    extra_priority = priority_slugs - kind_slugs

    assert not missing_priority, (
        f"slug(s) in REMEDIATION_KIND_SLUGS with no _SLUG_PRIORITY entry: "
        f"{sorted(missing_priority)}"
    )
    assert not extra_priority, (
        f"_SLUG_PRIORITY entry(ies) with no matching REMEDIATION_KIND_SLUGS "
        f"slug: {sorted(extra_priority)}"
    )


# ---------------------------------------------------------------------------
# Phase 229 Plan 01 (FIND-11, D-01/D-23): detected rows are written `open`.
# DETECTED_ITEM_STATE is imported inside each test so a missing constant fails
# only these tests, not collection of the whole file.
# ---------------------------------------------------------------------------


def test_detected_and_default_state_constants() -> None:
    from quirk.intelligence.remediation import DEFAULT_ITEM_STATE, DETECTED_ITEM_STATE

    assert DETECTED_ITEM_STATE == "open"
    assert DEFAULT_ITEM_STATE == "not_observed"


def test_detected_fingerprint_rows_and_item_are_written_open(tmp_path) -> None:
    from quirk.intelligence.remediation import DETECTED_ITEM_STATE

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)

    with get_session(db_path) as session:
        fp_rows = session.query(RemediationItemFingerprint).all()
        assert len(fp_rows) >= 8
        assert {fp.state for fp in fp_rows} == {DETECTED_ITEM_STATE}
        item = (
            session.query(RemediationItem)
            .filter(
                RemediationItem.slug == "plaintext-http-exposure",
                RemediationItem.scan_run_id == SCAN_RUN_ID,
            )
            .one()
        )
        assert item.state == DETECTED_ITEM_STATE


def test_counter_only_fingerprint_item_stays_not_observed(tmp_path, monkeypatch) -> None:
    """D-23: gate on constituents, not kind. A fingerprint-kind roadmap item
    with no matching finding is written not_observed."""
    import quirk.intelligence.remediation_persist as mod

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    monkeypatch.setattr(
        mod,
        "build_phased_roadmap",
        lambda evidence, weights: {
            "items": [
                {"title": "Remove plaintext HTTP exposure", "phase": "NOW"}
            ]
        },
    )

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, [], [])

    with get_session(db_path) as session:
        item = (
            session.query(RemediationItem)
            .filter(
                RemediationItem.slug == "plaintext-http-exposure",
                RemediationItem.scan_run_id == SCAN_RUN_ID,
            )
            .one()
        )
        assert item.constituency == "fingerprint"
        assert item.state == "not_observed"
        assert session.query(RemediationItemFingerprint).count() == 0


def test_rerun_does_not_reset_resurfaced_state(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)
    with get_session(db_path) as session:
        item = (
            session.query(RemediationItem)
            .filter(
                RemediationItem.slug == "plaintext-http-exposure",
                RemediationItem.scan_run_id == SCAN_RUN_ID,
            )
            .one()
        )
        item.state = "resurfaced"

    persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)

    with get_session(db_path) as session:
        item = (
            session.query(RemediationItem)
            .filter(
                RemediationItem.slug == "plaintext-http-exposure",
                RemediationItem.scan_run_id == SCAN_RUN_ID,
            )
            .one()
        )
        assert item.state == "resurfaced"


# ---------------------------------------------------------------------------
# 229-REVIEW CR-02: a failed snapshot is distinguishable from a clean scan,
# and run_scan.py gates closure on it.
# ---------------------------------------------------------------------------


def test_persist_failure_reports_failed_flag(tmp_path, monkeypatch) -> None:
    import quirk.intelligence.remediation_persist as mod

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()

    def _boom(*_a, **_k):
        raise RuntimeError("simulated snapshot failure")

    monkeypatch.setattr(mod, "build_phased_roadmap", _boom)
    counters = persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)
    assert counters.get("failed") == 1
    with get_session(db_path) as session:
        assert session.query(RemediationItem).count() == 0


def test_clean_persist_has_no_failed_flag(tmp_path) -> None:
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    endpoints, findings = _eight_plaintext_endpoints_and_findings()
    counters = persist_remediation_snapshot(db_path, SCAN_RUN_ID, endpoints, findings)
    assert "failed" not in counters


def test_run_scan_skips_closure_when_snapshot_failed() -> None:
    """The closure_verify block must consult the persist failure flag BEFORE it
    calls compute_closure."""
    import run_scan

    source = inspect.getsource(run_scan.main)
    closure_idx = source.index('"closure_verify"')
    gate_idx = source.index('_remediation_counters.get("failed")', closure_idx)
    call_idx = source.index("compute_closure(cfg.output.db_path", closure_idx)
    assert closure_idx < gate_idx < call_idx
