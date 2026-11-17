"""Phase 31: Trend analysis intelligence module.

compute_trend_report() is a pure function (D-12: no datetime.now() inside).
The caller supplies current_ts and previous_ts as parameters.

Session grouping is by scan_run_id (list_session_timestamps, RVW-003 / FIND-12);
legacy rows with scan_run_id NULL fall back to millisecond buckets so two scans
started in different milliseconds stay distinct (CR-05).
_fetch_session_endpoints resolves a session timestamp back to its scan run.

Scan-error counting (Phase 237 D-10/D-11): environment categories are advisory
and weigh 0; an ADVISORY outage row weighs the number of targets it covers.

NULL scanned_at rows (D-13): v4.2-era endpoints may have scanned_at IS NULL.
These are excluded from session grouping AND from per-session endpoint fetches by
filtering scanned_at.isnot(None) in every query.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Iterable, List, Mapping, Optional, Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.models import CryptoEndpoint
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.dashboard.api.finding_title_bridge import canonical_cli_title
from quirk.scanner.target_outcome import failed_target_count

FindingsDeriver = Callable[[Sequence[Any]], List[Mapping[str, Any]]]


# ---------------------------------------------------------------------------
# Severity bucketing
# ---------------------------------------------------------------------------

# Phase 237 D-10: trends keeps its OWN advisory-only set. Environment facts
# (extra/binary not installed, internal-target guard) stay advisory; run-to-run
# outcomes (targets_unreachable, auth_failed, missing_credentials) are scan-error
# regressions, otherwise a FULL connector outage collapses to one advisory row
# and reads as zero while a partial outage shows. The shared
# COVERAGE_SKIP_ADVISORY_CATEGORIES (scoring, findings_evaluator, sensor_cmd) is
# deliberately unchanged (235.3 P-02) and is not used here.
# target_unanswered is NOT in either set.
_ADVISORY_ONLY_CATEGORIES: frozenset = frozenset(
    {"missing_extra", "missing_binary", "internal_target_refused"}
)
_OUTAGE_CATEGORIES: frozenset = frozenset(
    {"targets_unreachable", "auth_failed", "missing_credentials"}
)


def _error_weight(ep) -> int:
    """Scan-error weight of one endpoint row (Phase 237 D-11).

    0 for advisory-only categories. An ADVISORY outage row stands for every
    target of its phase, so it weighs N from "<k> of <N> targets ..." (else 1,
    e.g. the Vault missing-token row). Everything else weighs 1. Note: for
    db/k8s/cloud the classifier also forwards in-band error rows (P-08), so a
    full outage there may read up to 2N; this is documented, not subtracted.
    """
    category = getattr(ep, "scan_error_category", None)
    if category in _ADVISORY_ONLY_CATEGORIES:
        return 0
    if ep.protocol == "ADVISORY" and category in _OUTAGE_CATEGORIES:
        return failed_target_count(ep.scan_error) or 1
    return 1


_SEVERITY_BUCKET = {
    "CRITICAL": "high",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    # INFO intentionally absent — excluded from counts and samples (D-05)
}

_SEVERITY_RANK = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "INFO": 4,
}


def severity_rank(severity: Any) -> int:
    """Sort rank of a severity label (CRITICAL first; unknown last)."""
    return _SEVERITY_RANK.get(severity, 99)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SampleFindingItem:
    host: str
    port: Optional[int]
    protocol: Optional[str]
    severity: str
    title: Optional[str] = None


@dataclass
class SeverityTransitionItem:
    """One finding, keyed (host, port, canonical title), whose severity changed
    between two sessions without its identity changing (D-03)."""
    host: str
    port: Optional[int]
    protocol: Optional[str]
    previous_severity: Optional[str]
    current_severity: Optional[str]
    title: Optional[str] = None


@dataclass
class TrendReport:
    current_session_ts: Optional[datetime]
    previous_session_ts: Optional[datetime]
    # Phase 199 / TRIAGE-10: widened Optional[int] -> Optional[float] x3 —
    # transport-accurate typing so a fractional score survives, and the
    # delta reflects real float subtraction.
    current_score: Optional[float]
    previous_score: Optional[float]
    score_delta: Optional[float]
    new_high: int
    new_medium: int
    new_low: int
    resolved_high: int
    resolved_medium: int
    resolved_low: int
    scan_errors_new_count: int
    scan_errors_resolved_count: int
    new_findings_sample: List[SampleFindingItem] = field(default_factory=list)
    resolved_findings_sample: List[SampleFindingItem] = field(default_factory=list)
    severity_transitions: List[SeverityTransitionItem] = field(default_factory=list)
    new_total: int = 0
    resolved_total: int = 0


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def list_session_timestamps(
    db: Session, limit: int = 10, *, complete_only: bool = False
) -> List[datetime]:
    """Return up to `limit` most recent distinct session timestamps (newest first).

    RVW-003: a session is one `scan_run_id`, represented by its *earliest*
    endpoint timestamp. Grouping on a millisecond-precision strftime key
    instead made one scan look like many sessions - a scan's stages each stamp
    their own rows as they run, so a 10-endpoint scan could yield 10 "sessions",
    and the trend delta was then computed between two stages of the same scan.

    Rows predating the column (scan_run_id IS NULL) are bucketed by millisecond
    so two scans started in different milliseconds stay distinct (CR-05). NULL
    scanned_at rows are excluded (D-13). The returned datetimes are real stored
    values, so _fetch_session_endpoints can match them exactly (FIND-12).

    Phase 237 D-08/D-09: with ``complete_only=True`` sessions whose scan_run_id
    is incomplete (checkpoint rows but no completed 'reports' checkpoint, see
    quirk.intelligence.scan_completion) are dropped BEFORE the ``limit`` slice,
    so a running or interrupted scan is never a trend session. Legacy NULL-run
    keys are always kept (D-07/D-14). The default False leaves every other
    importer's behaviour unchanged.

    Shared by the dashboard routes and the notifier (Phase 229 D-08); it must
    stay free of dashboard-extra imports.
    """
    rows = (
        db.query(CryptoEndpoint.scanned_at, CryptoEndpoint.scan_run_id)
        .filter(CryptoEndpoint.scanned_at.isnot(None))
        .all()
    )
    earliest: dict = {}
    for row_ts, row_run_id in rows:
        if row_ts is None:
            continue
        if isinstance(row_ts, str):
            try:
                row_ts = datetime.fromisoformat(row_ts)
            except ValueError:
                continue
        if row_run_id:
            key = row_run_id
        else:
            key = (
                "legacy",
                row_ts.replace(microsecond=(row_ts.microsecond // 1000) * 1000),
            )
        prev = earliest.get(key)
        if prev is None or row_ts < prev:
            earliest[key] = row_ts
    if complete_only:
        from quirk.intelligence.scan_completion import incomplete_scan_run_ids

        incomplete = incomplete_scan_run_ids(db)
        earliest = {
            k: v for k, v in earliest.items()
            if not (isinstance(k, str) and k in incomplete)
        }
    return sorted(earliest.values(), reverse=True)[:limit]


def _fetch_session_endpoints(db: Session, target_ts: datetime) -> List[CryptoEndpoint]:
    """Fetch every endpoint belonging to the scan session `target_ts` represents.

    RVW-003: `target_ts` is a session's *earliest* endpoint timestamp, as returned
    by the session listers. We resolve it to the stored `scan_run_id` and return
    the whole session. The previous 1-millisecond window returned only the rows
    stamped in that same millisecond — meaning a trend "session" was really one
    stage (often one endpoint) of a scan, and score deltas were computed between
    two slices of the *same* scan.

    Rows written before `scan_run_id` existed (and sensor-origin rows) are
    grouped by millisecond bucket, exactly as `list_session_timestamps` keys
    them. `target_ts` is that bucket's real earliest stamp, which is NOT
    millisecond-aligned, so the window is the bucket containing it -
    [floor_ms(target_ts), floor_ms(target_ts) + 1ms) - never
    [target_ts, target_ts + 1ms), which reached into the next bucket and put
    its rows in two sessions (229-REVIEW WR-04). Two scans in different
    milliseconds stay distinct (CR-05). Excludes NULL scanned_at rows (D-13)
    via explicit filter.
    """
    # closes cbom-intel-reports/IN-03 (Phase 77 D-09) — yield_per(1000) streaming
    # replaces .all() materialization; SQLAlchemy idiomatic chunk size per Discretion.
    keyed = (
        db.query(CryptoEndpoint.scan_run_id)
        .filter(
            CryptoEndpoint.scanned_at == target_ts,
            CryptoEndpoint.scan_run_id.isnot(None),
        )
        .first()
    )
    if keyed is not None and keyed[0]:
        return list(
            db.query(CryptoEndpoint)
            .filter(CryptoEndpoint.scan_run_id == keyed[0])
            .yield_per(1000)
        )

    bucket_lo = target_ts.replace(microsecond=(target_ts.microsecond // 1000) * 1000)
    streamed = (
        db.query(CryptoEndpoint)
        .filter(
            CryptoEndpoint.scanned_at >= bucket_lo,
            CryptoEndpoint.scanned_at < bucket_lo + timedelta(milliseconds=1),
            CryptoEndpoint.scanned_at.isnot(None),
            CryptoEndpoint.scan_run_id.is_(None),
        )
        .yield_per(1000)
    )
    return list(streamed)


def _bucket_for_severity(sev: str) -> Optional[str]:
    """Map a raw severity string to a display bucket, or None for INFO/unknown."""
    return _SEVERITY_BUCKET.get(sev)


def _count_by_bucket(keys: Iterable[tuple], sev_map: dict) -> dict:
    """Count (host, port, protocol) keys by severity bucket, looking severity
    up per key in `sev_map`.

    Returns a dict with keys "high", "medium", "low". Keys whose severity is
    None or INFO/unknown are silently ignored (D-05) — this is unchanged from
    the old severity-in-key behaviour, only the lookup mechanism moved from
    "read the 4th tuple element" to "look up in the map" since severity is no
    longer part of the key.
    """
    counts: dict = {"high": 0, "medium": 0, "low": 0}
    for key in keys:
        bucket = _bucket_for_severity(sev_map.get(key))
        if bucket is not None:
            counts[bucket] += 1
    return counts


def finding_key(f: Mapping[str, Any]) -> tuple:
    """The ONE finding identity: (host, port, canonical title).

    Severity and the finding id are never part of the key (D-03).
    canonical_cli_title folds bridged titles; unbridged titles pass through.
    """
    t = f.get("title") or ""
    return (str(f.get("host") or ""), f.get("port"), canonical_cli_title(t) or t)


_finding_key = finding_key


def _count_findings_by_bucket(findings: Iterable[Mapping[str, Any]]) -> dict:
    """Count findings (one per finding, not per endpoint) by severity bucket."""
    items = list(findings)
    return _count_by_bucket(range(len(items)), {i: f.get("severity") for i, f in enumerate(items)})


def index_findings(findings: Iterable[Mapping[str, Any]], excluded_hosts: set) -> dict:
    """finding_key -> finding; on collision keep the highest-severity one.

    The ONE finding index shared by Trends and Compare (237 D-03, review
    WR-05). Findings on an ``excluded_hosts`` (host, port) are dropped. D-03
    callers pass the SAME errored-now set for both sides of a delta.
    """
    out: dict = {}
    for f in findings:
        if (f.get("host"), f.get("port")) in excluded_hosts:
            continue
        k = finding_key(f)
        cur = out.get(k)
        if cur is None or severity_rank(f.get("severity")) < severity_rank(cur.get("severity")):
            out[k] = f
    return out


_index_findings = index_findings


def _sample_findings(
    findings_by_key: dict,
    target_keys: set,
) -> List[SampleFindingItem]:
    """Return sample findings (max 5) whose finding key is in target_keys.

    Sort: severity rank asc (CRITICAL first), host, port (None-safe). Cap 5 (D-08).
    """
    matched = [findings_by_key[k] for k in target_keys if k in findings_by_key]
    matched.sort(
        key=lambda f: (
            _SEVERITY_RANK.get(f.get("severity"), 99),
            str(f.get("host") or ""),
            f.get("port") or 0,
            f.get("title") or "",
        )
    )
    return [
        SampleFindingItem(
            host=f.get("host"),
            port=f.get("port"),
            protocol=f.get("protocol"),
            severity=f.get("severity"),
            title=f.get("title"),
        )
        for f in matched[:5]
    ]


def _default_report_deriver(endpoints: Sequence[Any]) -> List[Mapping[str, Any]]:
    """Report-composer default deriver (lazy import avoids an import cycle)."""
    from quirk.engine.findings_evaluator import derive_report_findings

    return derive_report_findings(endpoints)


def _score_for_session(
    endpoints: List[CryptoEndpoint],
    findings_deriver: Optional[FindingsDeriver] = None,
) -> Optional[float]:
    """Compute the readiness score for a list of endpoints.

    quirk/intelligence/scoring.py's compute_readiness_score still returns
    total_score = int(round(...)) today (unchanged, LOCKED). This function's
    return annotation is transport-accurate rather than source-accurate,
    Phase 199 / TRIAGE-10: it preserves whatever score_dict["score"] yields,
    including None (zero domains assessed) or a future fractional value.
    """
    # Phase 228 (XSURF-07, D-09): findings come from the caller's deriver (dashboard) or the report composer; a findings-less score is not reachable by default.
    derive = findings_deriver or _default_report_deriver
    return _score_from_findings(endpoints, derive(endpoints))


def _score_from_findings(
    endpoints: List[CryptoEndpoint],
    findings: Sequence[Mapping[str, Any]],
) -> Optional[float]:
    """Score from an already-derived findings list (derive-once, D-01)."""
    evidence = build_evidence_summary(endpoints, findings)
    score_dict = compute_readiness_score(evidence)
    return score_dict["score"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_trend_report(
    current_ts: datetime,
    previous_ts: Optional[datetime],
    db: Session,
    *,
    findings_deriver: Optional[FindingsDeriver] = None,
) -> TrendReport:
    """Compare two scan sessions and return a trend report.

    Args:
        findings_deriver: optional callable mapping a session's endpoints to
            findings for scoring; defaults to the report composer (D-09).

    D-12: Pure function — no datetime.now() inside. Caller supplies timestamps.
    D-06: When previous_ts is None, returns null-delta single-session response.
    D-13: NULL scanned_at rows are excluded from all session fetches.

    Match key for finding delta: (host, port, canonical title) over DERIVED findings
    (see _finding_key; the legacy endpoint-severity rationale follows). Severity is NOT part
    of the key — it is carried alongside as a per-key map instead. Severity is
    populated only by the three cloud connectors; measured against
    output/quirk.db's crypto_endpoints table: 30 rows, 0 non-NULL severity. A
    severity-in-key filter (`severity is not None`) on data shaped like that
    empties both key sets before the key is ever consulted, so the delta was
    empty on every real scan by construction — this is what IDENT-02 fixes.

    D-03's original intent — a HIGH→MEDIUM transition at an unchanged endpoint
    should be visible as a partial-remediation signal, not silently disappear —
    is now served by `severity_transitions` instead of by severity-in-key: for
    every (host, port, protocol) present in both sessions whose severity
    differs, one `SeverityTransitionItem(host, port, protocol,
    previous_severity, current_severity)` is emitted, and that endpoint is
    excluded from new_findings_sample/resolved_findings_sample (it did not
    appear or disappear — it changed).

    Severity bucketing (unchanged, D-05): CRITICAL/HIGH → "high", MEDIUM →
    "medium", LOW → "low", INFO/None → excluded from counts and samples. Bucket
    counts (new_high/new_medium/new_low/resolved_*) are therefore honestly
    zero when severity is absent on every row. `new_total`/`resolved_total`
    are the severity-agnostic counterparts — `len(new_keys)` /
    `len(resolved_keys)` — and are the signal that stays non-zero even when
    severity is entirely NULL.

    Scan error delta (D-04/D-05, unchanged): rows with scan_error IS NOT NULL
    are excluded from finding delta keys; counted separately as
    scan_errors_new_count / scan_errors_resolved_count.

    Sample arrays (D-08, unchanged): capped at 5, sorted by severity desc
    (CRITICAL first), then host asc, then port asc.

    Accuracy note: Trend accuracy depends on consistent target configuration
    between scans. IP-addressed targets may produce phantom new/resolved
    findings if IPs change. NULL collision with v4.2-era sessions
    (scanned_at IS NULL) is expected behavior per D-13.
    """
    derive = findings_deriver or _default_report_deriver
    current_eps = _fetch_session_endpoints(db, current_ts)
    cur_f = list(derive(current_eps)) if current_eps else []
    current_score = _score_from_findings(current_eps, cur_f) if current_eps else None

    # D-06: single-session early return — no previous data to compare
    if previous_ts is None:
        return TrendReport(
            current_session_ts=current_ts,
            previous_session_ts=None,
            current_score=current_score,
            previous_score=None,
            score_delta=None,
            new_high=0,
            new_medium=0,
            new_low=0,
            resolved_high=0,
            resolved_medium=0,
            resolved_low=0,
            scan_errors_new_count=0,
            scan_errors_resolved_count=0,
            new_total=0,
            resolved_total=0,
        )

    previous_eps = _fetch_session_endpoints(db, previous_ts)
    prev_f = list(derive(previous_eps)) if previous_eps else []
    previous_score = _score_from_findings(previous_eps, prev_f) if previous_eps else None
    score_delta = (
        current_score - previous_score
        if current_score is not None and previous_score is not None
        else None
    )

    # D-03: a (host, port) that errored in the current session is excluded from
    # BOTH sides. Previous-only exclusion turned an unchanged finding sharing
    # (host, port) with an errored row into a phantom NEW one (review CR-01).
    current_error_hosts = {
        (ep.host, ep.port) for ep in current_eps if ep.scan_error is not None
    }
    current_sev = index_findings(cur_f, current_error_hosts)
    previous_sev = index_findings(prev_f, current_error_hosts)
    current_keys = set(current_sev)
    previous_keys = set(previous_sev)

    new_keys = current_keys - previous_keys
    resolved_keys = previous_keys - current_keys

    # A severity change on the same finding is one transition, not new+resolved.
    severity_transitions = sorted(
        (
            SeverityTransitionItem(
                host=current_sev[key].get("host"),
                port=current_sev[key].get("port"),
                protocol=current_sev[key].get("protocol"),
                previous_severity=previous_sev[key].get("severity"),
                current_severity=current_sev[key].get("severity"),
                title=current_sev[key].get("title"),
            )
            for key in (current_keys & previous_keys)
            if current_sev[key].get("severity") != previous_sev[key].get("severity")
        ),
        key=lambda t: (str(t.host or ""), t.port or 0, t.title or ""),
    )

    new_counts = _count_findings_by_bucket(current_sev[k] for k in new_keys)
    resolved_counts = _count_findings_by_bucket(previous_sev[k] for k in resolved_keys)

    # D-05: scan error count delta computed independently of finding delta.
    # Phase 41 / D-15 + 235.1 D-06: exclude advisory-only categories
    # (missing_extra, missing_binary, and the 235.3 coverage-skip categories) so that "user did not
    # install [motion] this run" does not register as a scan-error regression.
    # getattr(..., None) tolerates older DB rows that predate the column.
    cur_err = sum(_error_weight(ep) for ep in current_eps if ep.scan_error is not None)
    prev_err = sum(_error_weight(ep) for ep in previous_eps if ep.scan_error is not None)
    scan_errors_new_count = max(0, cur_err - prev_err)
    scan_errors_resolved_count = max(0, prev_err - cur_err)

    # D-08: top-5 sample arrays, sorted by severity then host then port
    new_samples = _sample_findings(current_sev, new_keys)
    resolved_samples = _sample_findings(previous_sev, resolved_keys)

    return TrendReport(
        current_session_ts=current_ts,
        previous_session_ts=previous_ts,
        current_score=current_score,
        previous_score=previous_score,
        score_delta=score_delta,
        new_high=new_counts["high"],
        new_medium=new_counts["medium"],
        new_low=new_counts["low"],
        resolved_high=resolved_counts["high"],
        resolved_medium=resolved_counts["medium"],
        resolved_low=resolved_counts["low"],
        scan_errors_new_count=scan_errors_new_count,
        scan_errors_resolved_count=scan_errors_resolved_count,
        new_findings_sample=new_samples,
        resolved_findings_sample=resolved_samples,
        severity_transitions=severity_transitions,
        new_total=len(new_keys),
        resolved_total=len(resolved_keys),
    )
