"""Phase 41 ROBUST-01..03 acceptance tests.

Wave 0 (Plan 41-01) created xfail stubs; Wave 2 (Plan 41-03) flipped the
ROBUST-02 TLS-timeout assertion; Wave 3 (Plan 41-04) flips the remaining
four to real source-inspection assertions and adds a D-15 trends.py
category-aware error-counting test.

The wiring is asserted structurally — the actual import-failure / live
exception paths are exercised end-to-end in UAT-SERIES; here we keep the
unit suite under the D-16 60s budget by verifying the canonical patterns
appear in run_scan source.
"""
from __future__ import annotations

import pytest

import inspect


def test_missing_extra_advisory_stderr() -> None:
    """ROBUST-01 / D-12 / Phase 68 UX-02: stderr advisory emits QRK format via format_error."""
    import run_scan
    src = inspect.getsource(run_scan)
    assert "format_error" in src, "run_scan.py must import/call format_error"
    assert "INSTALL-001" in src, "run_scan.py must reference QRK-INSTALL-001 for missing-extra advisory"
    assert (
        "scan_error_category=\"missing_extra\"" in src
        or "scan_error_category='missing_extra'" in src
    ), "missing_extra category constant not referenced"


def test_missing_extra_exit_code_zero() -> None:
    """ROBUST-01 / D-13: missing optional extra -> exit 0 (scan completes).

    main() returns None on the success path; missing-extra is treated as a
    handled error and routed through error_endpoints (not via sys.exit/return
    non-zero). Asserted structurally: the missing_extra category is referenced
    and main() does not call sys.exit on advisory paths.
    """
    import run_scan
    src = inspect.getsource(run_scan)
    assert "missing_extra" in src
    # No sys.exit on the advisory path — advisories print to stderr only.
    advisory_block_start = src.find("format_error(\"INSTALL-001\")")
    assert advisory_block_start != -1
    # Within ~500 chars of the advisory print there must NOT be a sys.exit(non-zero)
    window = src[advisory_block_start: advisory_block_start + 500]
    assert "sys.exit(1)" not in window
    assert "sys.exit(2)" not in window


def test_per_scanner_timeout_respected_tls() -> None:
    """ROBUST-02: TLS scanner reads cfg.scan.timeouts.tls_seconds."""
    import run_scan
    src = inspect.getsource(run_scan)
    # The TLS phase must reference the new sub-table read (D-08).
    assert "cfg.scan.timeouts.tls_seconds" in src, (
        "TLS timeout not sourced from canonical sub-table"
    )
    # And the BACK-45 mutation pattern must be gone.
    assert "cfg.scan.timeout_seconds = " not in src, (
        "BACK-45 mutation still present"
    )
    assert "cfg.scan.concurrency = " not in src, (
        "BACK-45 concurrency mutation still present"
    )


def test_unexpected_exception_captured_in_scan_errors() -> None:
    """ROBUST-03 / D-14: BaseException wrapper produces a CryptoEndpoint with
    scan_error_category='exception'."""
    import run_scan
    src = inspect.getsource(run_scan)
    assert "except BaseException" in src, "BaseException catch missing"
    assert (
        "scan_error_category=\"exception\"" in src
        or "scan_error_category='exception'" in src
    ), "exception category constant not produced by wrapper"


def test_keyboard_interrupt_propagates() -> None:
    """D-14: KeyboardInterrupt and SystemExit are re-raised, not swallowed.

    Required ordering: the (KeyboardInterrupt, SystemExit) re-raise clause
    must come BEFORE the BaseException catch, otherwise the broad catch
    swallows the abort signal.
    """
    import run_scan
    src = inspect.getsource(run_scan)
    assert "except (KeyboardInterrupt, SystemExit)" in src
    assert "except BaseException" in src
    kbi = src.find("except (KeyboardInterrupt, SystemExit)")
    bex = src.find("except BaseException")
    assert kbi != -1 and bex != -1, "wrapper clauses not found"
    assert kbi < bex, (
        "KeyboardInterrupt re-raise must come before BaseException catch"
    )


def test_trends_excludes_missing_extra_from_error_counts() -> None:
    """D-15: trends.py must not count missing_extra entries as scan errors.

    A previous scan with a single missing_extra row and a current scan with
    one missing_extra + one exception row should produce cur_err=1, prev_err=0
    so missing-extras never register as a scan-error regression.
    """
    from quirk.models import CryptoEndpoint
    prev = [
        CryptoEndpoint(
            host="x", port=1, protocol="P",
            scan_error="missing", scan_error_category="missing_extra",
        ),
    ]
    cur = [
        CryptoEndpoint(
            host="x", port=1, protocol="P",
            scan_error="missing", scan_error_category="missing_extra",
        ),
        CryptoEndpoint(
            host="y", port=2, protocol="P",
            scan_error="boom", scan_error_category="exception",
        ),
    ]
    cur_err = sum(
        1 for ep in cur
        if ep.scan_error is not None
        and getattr(ep, "scan_error_category", None) != "missing_extra"
    )
    prev_err = sum(
        1 for ep in prev
        if ep.scan_error is not None
        and getattr(ep, "scan_error_category", None) != "missing_extra"
    )
    assert cur_err == 1
    assert prev_err == 0
    assert max(0, cur_err - prev_err) == 1  # one new exception
    # And confirm the trends.py source itself uses the same exclusion clause.
    import inspect as _inspect
    from quirk.intelligence import trends as _trends
    tsrc = _inspect.getsource(_trends)
    # 235.3 D-07: the literal moved into the shared set; assert the import and
    # the runtime membership instead of the literal's presence in trends source.
    assert "COVERAGE_SKIP_ADVISORY_CATEGORIES" in tsrc
    assert "missing_extra" in _trends._ADVISORY_ONLY_CATEGORIES
    assert "getattr(ep, \"scan_error_category\", None)" in tsrc


@pytest.mark.parametrize("category", [
    "missing_extra", "missing_binary",
    "internal_target_refused", "auth_failed", "missing_credentials", "targets_unreachable",
])
def test_trends_advisory_category_not_a_scan_error_regression(tmp_path, category) -> None:
    """235.1 D-06: advisory-only categories never register as scan-error regressions.

    Drives the real compute_trend_report (not a reimplementation of its filter):
    previous session clean, current session adds one <category> ADVISORY row and
    one genuine exception row -> exactly one new scan error.
    """
    from datetime import datetime

    from sqlalchemy.orm import sessionmaker

    from quirk.db import init_db
    from quirk.intelligence.trends import compute_trend_report
    from quirk.models import CryptoEndpoint

    prev_ts = datetime(2026, 1, 1, 10, 0, 0)
    cur_ts = datetime(2026, 1, 2, 10, 0, 0)
    engine = init_db(str(tmp_path / "t.db"))
    with sessionmaker(bind=engine)() as db:
        db.add(CryptoEndpoint(host="10.0.0.1", port=443, protocol="tls", scanned_at=prev_ts))
        db.add(CryptoEndpoint(host="10.0.0.1", port=443, protocol="tls", scanned_at=cur_ts))
        db.add(CryptoEndpoint(
            host="source_scanner", port=0, protocol="ADVISORY",
            scan_error="semgrep is not installed (QRK-INSTALL-008)",
            scan_error_category=category, scanned_at=cur_ts,
        ))
        db.commit()
        report = compute_trend_report(cur_ts, prev_ts, db, findings_deriver=lambda eps: [])
        assert report.scan_errors_new_count == 0
        db.add(CryptoEndpoint(
            host="10.0.0.2", port=443, protocol="tls", scan_error="boom",
            scan_error_category="exception", scanned_at=cur_ts,
        ))
        db.commit()
        report = compute_trend_report(cur_ts, prev_ts, db, findings_deriver=lambda eps: [])
        assert report.scan_errors_new_count == 1


def test_trends_target_unanswered_counts_as_regression(tmp_path) -> None:
    """235.3 P-02/P-14: a per-target target_unanswered row is a real scan error
    (NOT advisory-only) and registers as one new regression."""
    from datetime import datetime

    from sqlalchemy.orm import sessionmaker

    from quirk.db import init_db
    from quirk.intelligence.trends import compute_trend_report
    from quirk.models import CryptoEndpoint

    prev_ts = datetime(2026, 1, 1, 10, 0, 0)
    cur_ts = datetime(2026, 1, 2, 10, 0, 0)
    engine = init_db(str(tmp_path / "t.db"))
    with sessionmaker(bind=engine)() as db:
        db.add(CryptoEndpoint(host="10.0.0.1", port=443, protocol="tls", scanned_at=prev_ts))
        db.add(CryptoEndpoint(
            host="10.0.0.9", port=389, protocol="ldap", scan_error="no answer",
            scan_error_category="target_unanswered", scanned_at=cur_ts,
        ))
        db.commit()
        report = compute_trend_report(cur_ts, prev_ts, db, findings_deriver=lambda eps: [])
        assert report.scan_errors_new_count == 1
