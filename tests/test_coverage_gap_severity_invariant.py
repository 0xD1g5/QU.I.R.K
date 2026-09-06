"""Phase 184.4 WR-02 — enforce the "coverage_gap is never CRITICAL" invariant.

WHY THIS FILE EXISTS
--------------------
Two independent tallies of "the CRITICAL finding count" feed two different
consumers, and they use DIFFERENT counting bases:

  1. The severity floor in ``quirk.intelligence.scoring.compute_readiness_score()``
     reads ``evidence["finding_severity_counts"]["CRITICAL"]``, which
     ``quirk.intelligence.evidence.build_evidence_summary()`` builds AFTER
     filtering out ``category == "coverage_gap"`` findings (Phase 45 / D-07).

  2. The congruence guard's tally comes from
     ``quirk.reports.content_model._count_severities(findings)``, which counts
     EVERY finding's severity with NO coverage_gap filter.

Today those two bases agree, but only because coverage_gap findings happen to
be emitted at INFO severity. ``html_renderer.py``'s own comment names that
dependency explicitly -- and Phase 184.4's code review (WR-02) observed that
the invariant it relies on was *documented but not enforced*. A future scanner
change emitting a CRITICAL coverage_gap finding would silently split the two
bases: the severity floor would not fire (evidence excludes the finding) while
the congruence guard WOULD see it and reject the favourable band, producing a
``ReportCongruenceError`` at render time for a scan the producer believed was
consistent.

This file turns that documented assumption into an enforced run-time gate,
matching the established pattern in ``tests/test_band_severity_matrix_gate.py``
and ``tests/test_band_producer_scan_gate.py``.

WHY OPTION (a) AND NOT OPTION (b)
---------------------------------
The review offered an alternative: make ``_count_severities()`` apply the same
coverage_gap filter. That was NOT chosen. The guard deliberately counts
unfiltered so that a coverage_gap finding which somehow IS severe still
blocks a favourable band -- filtering it there would remove a real safety net
to fix a hypothetical one. Enforcing the upstream invariant keeps both
properties.

THE FOUR LEGS
-------------
1. Behavioural: the real evaluator emits coverage_gap findings at INFO.
2. Differential: the two counting bases agree on real evaluator output.
3. Prove-it-can-fail: leg 2's differential DOES diverge when fed a synthetic
   CRITICAL coverage_gap finding, so leg 2 is load-bearing, not vacuous.
4. Run-time source scan: every file in ``quirk/`` mentioning ``coverage_gap``
   is in a dispositioned ledger, so a NEW emitter cannot be added silently.
   Derived from the source tree at test-run time -- a hand-written list of
   known sites is not a safeguard (CLAUDE.md).
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from quirk.intelligence.evidence import build_evidence_summary
from quirk.engine.findings_evaluator import evaluate_endpoints
from quirk.reports.content_model import _count_severities

_QUIRK_ROOT = Path(__file__).resolve().parent.parent / "quirk"


def _cfg():
    return SimpleNamespace(scan=SimpleNamespace(ports_tls=[], ports_http=[]))


def _advisory_ep(**kwargs):
    """Minimal duck-typed CryptoEndpoint stand-in for the ADVISORY path."""
    defaults = dict(
        host="kerberos_scanner",
        port=0,
        protocol="ADVISORY",
        scan_error=(
            "Kerberos scanning skipped — run `pip install quirk[identity]` to enable"
        ),
        scan_error_category="missing_extra",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _critical_counts(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Compute BOTH counting bases for the same finding list.

    Returns the two numbers WR-02 is about: the guard-side tally
    (``_count_severities``, unfiltered) and the score-side tally
    (``build_evidence_summary``, coverage_gap-filtered).
    """
    guard_side = _count_severities(findings).get("CRITICAL", 0)
    evidence = build_evidence_summary(endpoints=[], findings=findings)
    score_side = evidence["finding_severity_counts"].get("CRITICAL", 0)
    return {"guard_side": guard_side, "score_side": score_side}


# ---------------------------------------------------------------------------
# Leg 1 — behavioural: the real emitter uses INFO.
# ---------------------------------------------------------------------------

def test_evaluator_emits_coverage_gap_findings_at_info() -> None:
    """The one in-tree producer of ``category == "coverage_gap"`` findings
    (``quirk/engine/findings_evaluator.py``) must emit them at INFO.

    This is the assumption ``html_renderer.py``'s comment and the severity
    floor both rest on. Asserted against the real evaluator's output, not
    against a hand-built fixture, so a severity change at the emitter is
    caught here.
    """
    findings = evaluate_endpoints(_cfg(), [_advisory_ep()])
    coverage_gaps = [f for f in findings if f.get("category") == "coverage_gap"]

    assert coverage_gaps, (
        "expected at least one coverage_gap finding from the ADVISORY/"
        f"missing_extra path — got {findings!r}. If the emitter moved, this "
        "gate is now scanning nothing and must be repointed, not deleted."
    )
    for f in coverage_gaps:
        assert str(f.get("severity", "")).upper() == "INFO", (
            f"coverage_gap finding emitted at severity "
            f"{f.get('severity')!r}, expected INFO: {f!r}"
        )


@pytest.mark.parametrize("severity", ["CRITICAL", "HIGH", "MEDIUM"])
def test_evaluator_never_emits_coverage_gap_above_info(severity: str) -> None:
    """Stronger form of leg 1: no coverage_gap finding may carry ANY
    above-INFO severity. CRITICAL is the one that splits the counting bases,
    but HIGH/MEDIUM would signal the emitter's contract had changed and the
    INFO assumption was no longer safe to rely on."""
    findings = evaluate_endpoints(_cfg(), [_advisory_ep()])
    offenders = [
        f for f in findings
        if f.get("category") == "coverage_gap"
        and str(f.get("severity", "")).upper() == severity
    ]
    assert not offenders, (
        f"coverage_gap finding(s) emitted at {severity}: {offenders!r}"
    )


# ---------------------------------------------------------------------------
# Leg 2 — differential: the two counting bases agree.
# ---------------------------------------------------------------------------

def test_counting_bases_agree_on_real_evaluator_output() -> None:
    """The WR-02 invariant stated directly: for the findings the real
    evaluator produces, the guard-side CRITICAL tally (unfiltered) and the
    score-side CRITICAL tally (coverage_gap-filtered) must be equal.

    A mixed finding set is used -- a coverage_gap row alongside genuinely
    severe rows -- so the test would still be meaningful if the CRITICAL
    count were nonzero rather than only proving 0 == 0.
    """
    findings = evaluate_endpoints(_cfg(), [_advisory_ep()])
    findings = list(findings) + [
        {"severity": "CRITICAL", "host": "h1", "port": 1, "title": "A real critical"},
        {"severity": "CRITICAL", "host": "h2", "port": 2, "title": "Another critical"},
        {"severity": "HIGH", "host": "h3", "port": 3, "title": "A high"},
    ]

    counts = _critical_counts(findings)
    assert counts["guard_side"] == counts["score_side"], (
        "the congruence guard's CRITICAL tally and the severity floor's "
        f"CRITICAL tally disagree: {counts!r}. A coverage_gap finding is "
        "being counted by one basis and not the other — see this module's "
        "docstring."
    )
    # Guard against a vacuous 0 == 0 pass.
    assert counts["guard_side"] == 2, (
        f"fixture drift — expected 2 CRITICAL findings, got {counts!r}"
    )


# ---------------------------------------------------------------------------
# Leg 3 — prove the differential CAN fail.
# ---------------------------------------------------------------------------

def test_differential_diverges_on_a_critical_coverage_gap() -> None:
    """Feed the SAME differential a synthetic CRITICAL coverage_gap finding —
    exactly the future scanner change WR-02 warns about — and assert the two
    bases then disagree.

    This proves leg 2 is load-bearing: without it, leg 2 could pass forever
    on a codebase where the filter had been removed entirely and both bases
    were trivially identical.
    """
    hostile = [
        {
            "severity": "CRITICAL",
            "category": "coverage_gap",
            "host": "kerberos_scanner",
            "port": 0,
            "title": "Synthetic CRITICAL coverage gap (test-only)",
        },
    ]

    counts = _critical_counts(hostile)
    assert counts["guard_side"] == 1, (
        f"the guard-side tally should count the unfiltered coverage_gap "
        f"finding: {counts!r}"
    )
    assert counts["score_side"] == 0, (
        f"the score-side tally should exclude the coverage_gap finding "
        f"(Phase 45 / D-07): {counts!r}"
    )
    assert counts["guard_side"] != counts["score_side"], (
        "the differential in leg 2 cannot detect a CRITICAL coverage_gap "
        "finding — that test is vacuous and this gate is not protecting "
        "anything."
    )


# ---------------------------------------------------------------------------
# Leg 4 — run-time source scan: no new coverage_gap site appears silently.
# ---------------------------------------------------------------------------

# Every quirk/ file that mentions "coverage_gap", with why it is safe.
# Keyed by repo-relative path (line numbers deliberately omitted -- they churn
# and a line-keyed ledger rots into noise). The ASSERTION is on the KEY SET:
# a new file introducing coverage_gap fails until it is dispositioned here,
# which is the moment to check its severity.
_COVERAGE_GAP_SITE_DISPOSITIONS: Dict[str, str] = {
    "quirk/engine/findings_evaluator.py": (
        "EMITTER — the only site that sets category='coverage_gap' on a "
        "FINDING. Hardcodes severity='INFO'. Behaviourally locked by leg 1 "
        "above. A severity change here is the exact WR-02 hazard."
    ),
    "quirk/intelligence/evidence.py": (
        "CONSUMER — build_evidence_summary() filters coverage_gap out of "
        "finding_severity_counts (Phase 45 / D-07). This is the score-side "
        "counting basis in leg 2."
    ),
    "quirk/reports/html_renderer.py": (
        "CONSUMER — excludes coverage_gap from the display sev_counts tally "
        "and counts CRITICAL independently for the band cap. Read-only with "
        "respect to severity; emits nothing."
    ),
    "quirk/reports/docx_renderer.py": (
        "CONSUMER — filters coverage_gap out of report_findings for display. "
        "Read-only with respect to severity; emits nothing."
    ),
    "quirk/cbom/writer.py": (
        "NOT A FINDING EMITTER — sets scan_error_category='coverage_gap' on "
        "an ADVISORY CryptoEndpoint, not a finding category. "
        "findings_evaluator only routes scan_error_category=='missing_extra' "
        "to a coverage_gap finding, so these rows fall through to the "
        "generic scan-error handler and produce an INFO finding with "
        "category=None. Verified behaviourally: they never yield a "
        "coverage_gap-categorised finding at all."
    ),
    "quirk/errors.py": (
        "LOOKUP TABLE ONLY — maps the 'coverage_gap' category name to error "
        "code CBOM-001. Carries no severity and emits no finding."
    ),
    "quirk/dashboard/api/schemas.py": (
        "SCHEMA FIELD ONLY — an Optional[str] `category` field plus a comment "
        "naming coverage_gap as the motivating case (Phase 45 Q2). Passes the "
        "producer's value through to the API; sets no severity."
    ),
    "quirk/reports/writer.py": (
        "COMMENT ONLY — prose describing why error_endpoints is threaded into "
        "the CBOM writer. No coverage_gap literal is assigned anywhere."
    ),
    "quirk/util/optional_extra.py": (
        "COMMENT ONLY — prose stating that missing deps yield one coverage_gap "
        "INFO advisory. It produces the ADVISORY/missing_extra CryptoEndpoint "
        "row; findings_evaluator (above) is what turns that into an INFO "
        "finding. Sets no severity itself."
    ),
    "quirk/intelligence/scoring.py": (
        "FALSE POSITIVE / DIFFERENT CONCEPT — matches only as a substring of "
        "`adcs_coverage_gap_count`, the AD CS ESC4/5/7/8 misconfiguration "
        "metric (Phase 80). Unrelated to finding category 'coverage_gap'; it "
        "is a numeric evidence key feeding a score weight, not a severity. "
        "Dispositioned rather than pattern-excluded so the scan stays a dumb "
        "substring match that cannot be tuned into blindness."
    ),
}


def _files_mentioning_coverage_gap() -> Dict[str, int]:
    """Scan quirk/ at test-run time for every .py file containing the literal
    ``coverage_gap``. Regenerated from the source on every run -- never a
    hardcoded list."""
    hits: Dict[str, int] = {}
    for path in sorted(_QUIRK_ROOT.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        count = text.count("coverage_gap")
        if count:
            rel = path.resolve().relative_to(_QUIRK_ROOT.parent.resolve())
            hits[rel.as_posix()] = count
    return hits


def test_every_coverage_gap_site_is_dispositioned() -> None:
    """No file may introduce ``coverage_gap`` into quirk/ without a written
    disposition here. This is the tripwire that makes a FUTURE emitter --
    the thing WR-02 is actually worried about -- impossible to add silently:
    a new emitter fails this test, and dispositioning it forces someone to
    state its severity."""
    found = _files_mentioning_coverage_gap()

    # Self-check: the scan must not be silently scanning nothing.
    assert found, (
        f"the coverage_gap source scan found zero files under {_QUIRK_ROOT} — "
        "the scan is broken or mis-rooted, which would make this gate pass "
        "vacuously forever."
    )

    undispositioned = sorted(set(found) - set(_COVERAGE_GAP_SITE_DISPOSITIONS))
    assert not undispositioned, (
        "new coverage_gap site(s) with no disposition: "
        f"{undispositioned}. If any of these EMITS a finding with "
        "category='coverage_gap', it MUST use INFO severity — a CRITICAL "
        "coverage_gap splits the severity floor's counting basis from the "
        "congruence guard's (see this module's docstring). Add an entry to "
        "_COVERAGE_GAP_SITE_DISPOSITIONS stating which it is."
    )

    stale = sorted(set(_COVERAGE_GAP_SITE_DISPOSITIONS) - set(found))
    assert not stale, (
        f"dispositioned coverage_gap site(s) no longer mention coverage_gap: "
        f"{stale}. Remove the stale ledger entries so this ledger keeps "
        "reflecting the real source tree."
    )


def test_coverage_gap_site_scan_detects_an_undispositioned_file(tmp_path) -> None:
    """Prove leg 4 can fail: point the same scan logic at a tree containing an
    undispositioned coverage_gap file and assert it is reported."""
    fake_root = tmp_path / "quirk"
    fake_root.mkdir()
    (fake_root / "sneaky_new_scanner.py").write_text(
        'f["category"] = "coverage_gap"\n', encoding="utf-8"
    )

    found = {
        p.resolve().relative_to(fake_root.parent.resolve()).as_posix()
        for p in fake_root.rglob("*.py")
        if "coverage_gap" in p.read_text(encoding="utf-8")
    }
    undispositioned = found - set(_COVERAGE_GAP_SITE_DISPOSITIONS)

    assert undispositioned == {"quirk/sneaky_new_scanner.py"}, (
        "the source scan did not flag an undispositioned coverage_gap file — "
        f"the scan logic in leg 4 may be vacuous. found={found!r}"
    )
