"""quirk.merge.scan — Cross-sensor merge pipeline (Phase 110 MERGE-01/02/04/05).

merge_scan() assembles the union of latest-push-per-sensor CryptoEndpoint rows
plus NULL-sensor local rows, runs the canonical engine chain (build_evidence_summary →
compute_readiness_score → build_cbom) exactly ONCE over the full union (Option A),
computes a coverage_warning from Sensor push recency, and persists the merged
result as a MergeRun row — without rewriting the source endpoints' scanned_at.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.cbom.builder import build_cbom
from quirk.cbom.writer import write_cbom_files
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import CryptoEndpoint, MergeRun, Sensor

# Redefined locally to avoid importing from the dashboard layer (D-06 seam).
# Matches quirk/dashboard/api/routes/scan.py SESSION_BRACKET = timedelta(minutes=5).
_SESSION_BRACKET = timedelta(minutes=5)

# Sensors not pushed in more than stale_days are omitted from the warning
# (assumed decommissioned / intentionally offline).
_DEFAULT_STALE_DAYS = 30


def _build_coverage_warning(
    sensors: List[Sensor],
    now: datetime,
    stale_days: int = _DEFAULT_STALE_DAYS,
) -> Optional[Dict[str, Any]]:
    """Compute coverage_warning from sensor push recency.

    Returns None when all enrolled sensors are current.
    Returns {"missing_sensors": [ids], "reason": str} when any enrolled,
    non-stale sensor is overdue (last_push_at is None or now > last_push_at + 2×cadence).

    A sensor enrolled but silent for > stale_days is excluded (assumed decommissioned).
    """
    stale_cutoff = timedelta(days=stale_days)
    overdue: List[str] = []

    for s in sensors:
        if s.last_push_at is None:
            # Never pushed — check enrollment age.  If enrolled long ago (past
            # stale_days) with no push ever, treat as decommissioned and exclude
            # rather than warning forever (WR-02).
            ref_ts = s.enrolled_at
            if ref_ts is not None:
                silent_duration = now - ref_ts
                if silent_duration > stale_cutoff:
                    continue  # decommissioned / forgotten enrollment — exclude
            overdue.append(s.sensor_id)
        else:
            # Exclude sensors silent for > stale_days (decommissioned / intentionally offline)
            silent_duration = now - s.last_push_at
            if silent_duration > stale_cutoff:
                continue
            # Overdue: now > last_push_at + 2 × expected cadence
            # Guard against NULL expected_cadence_minutes (WR-03)
            cadence_minutes = s.expected_cadence_minutes
            if cadence_minutes is None:
                cadence_minutes = 1440  # fallback to 24h (architecture §6)
            cadence = timedelta(minutes=cadence_minutes)
            if now > s.last_push_at + 2 * cadence:
                overdue.append(s.sensor_id)

    if not overdue:
        return None

    return {
        "missing_sensors": overdue,
        "reason": (
            f"{len(overdue)} enrolled sensor(s) have not pushed within "
            f"2× their expected cadence: {', '.join(overdue)}"
        ),
    }


def _assemble_union(
    db: Session,
) -> List[CryptoEndpoint]:
    """Assemble the union of:
    1. Latest-push-per-sensor rows (func.max(scanned_at) per non-null sensor_id).
    2. NULL-sensor local rows within SESSION_BRACKET of the latest local scanned_at.

    Source rows are returned read-only — scanned_at is never mutated (MERGE-05).
    """
    union: List[CryptoEndpoint] = []

    # --- Part 1: Latest push per enrolled sensor ----------------------------
    # Subquery: (sensor_id, max(scanned_at)) for rows with a non-null sensor_id.
    sub = (
        db.query(
            CryptoEndpoint.sensor_id,
            func.max(CryptoEndpoint.scanned_at).label("max_ts"),
        )
        .filter(CryptoEndpoint.sensor_id.isnot(None))
        .group_by(CryptoEndpoint.sensor_id)
        .subquery()
    )
    sensor_eps: List[CryptoEndpoint] = (
        db.query(CryptoEndpoint)
        .join(
            sub,
            (CryptoEndpoint.sensor_id == sub.c.sensor_id)
            & (CryptoEndpoint.scanned_at == sub.c.max_ts),
        )
        .all()
    )
    union.extend(sensor_eps)

    # --- Part 2: NULL-sensor local rows (SESSION_BRACKET window) ------------
    latest_local_ts = (
        db.query(func.max(CryptoEndpoint.scanned_at))
        .filter(CryptoEndpoint.sensor_id.is_(None))
        .scalar()
    )
    if latest_local_ts is not None:
        local_eps: List[CryptoEndpoint] = (
            db.query(CryptoEndpoint)
            .filter(
                CryptoEndpoint.sensor_id.is_(None),
                CryptoEndpoint.scanned_at >= latest_local_ts - _SESSION_BRACKET,
                CryptoEndpoint.scanned_at <= latest_local_ts,
            )
            .all()
        )
        union.extend(local_eps)

    return union


def merge_scan(
    db: Session,
    *,
    now: Optional[datetime] = None,
    stale_days: int = _DEFAULT_STALE_DAYS,
    profile: str = "balanced",
    weights: Optional[Dict[str, float]] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the cross-sensor merge pipeline and return a result dict.

    Steps:
    1. Assemble the union (latest-per-sensor + NULL-sensor local window).
    2. Compute coverage_warning from Sensor.last_push_at recency.
    3. Option A: ONE call to build_evidence_summary(union) → compute_readiness_score(evidence).
    4. build_cbom(union) → write_cbom_files() for the CBOM artifacts on disk.
    5. Guard empty union: return a coverage_warning noting no data rather than a clean 100.
    6. Persist a MergeRun row (scan_id, merged_at, endpoint_count, sensor_count, score,
       coverage_warning_json). Source CryptoEndpoint.scanned_at is NEVER rewritten.

    Args:
        db: SQLAlchemy session (caller manages lifecycle via get_session or similar).
            The caller (or get_session context manager) is responsible for commit.
        now: Injectable reference time (defaults to datetime.now(timezone.utc) naive)
            for testing.
        stale_days: Sensors silent for longer than this are excluded from coverage checks.
        profile: Scoring profile — "balanced" | "aggressive" | "conservative".
        weights: Optional per-weight override dict for compute_readiness_score.
        output_dir: Directory for CBOM artifact output.  When None, CBOM artifacts
            are not written and cbom_json_path / cbom_xml_path will be None in the
            result dict.

    Returns:
        Dict with keys: scan_id, score, rating, subscores, drivers, coverage_warning,
        endpoint_count, sensor_count, cbom_json_path, cbom_xml_path.
    """
    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. Assemble union (READ ONLY — never mutate scanned_at)
    union = _assemble_union(db)

    # 2. Coverage warning from enrolled sensor push recency
    sensors = db.query(Sensor).all()
    coverage_warning = _build_coverage_warning(sensors, now, stale_days=stale_days)

    # 3. Guard empty union (T-110-03 / Pitfall 4): do not silently score 100
    if not union:
        if coverage_warning is None:
            coverage_warning = {
                "missing_sensors": [],
                "reason": "No endpoints found — no sensors enrolled and no local scan data.",
            }
        scan_id = now.isoformat(sep=" ")
        # Persist empty merge result — commit is caller's responsibility (WR-04)
        merge_row = MergeRun(
            scan_id=scan_id,
            merged_at=now,
            endpoint_count=0,
            sensor_count=len(sensors),
            score=None,
            coverage_warning_json=json.dumps(coverage_warning),
        )
        db.add(merge_row)
        db.flush()
        return {
            "scan_id": scan_id,
            "score": None,
            "rating": None,
            "subscores": {},
            "drivers": [],
            "coverage_warning": coverage_warning,
            "endpoint_count": 0,
            "sensor_count": len(sensors),
            "cbom_json_path": None,
            "cbom_xml_path": None,
        }

    # 4. Option A: ONE call over the FULL UNION (MERGE-02 — never average per-segment)
    evidence = build_evidence_summary(union, findings=None)
    score_result = compute_readiness_score(evidence, profile=profile, weights=weights)

    # 5. Build CBOM over the full union and write artifacts (CR-01)
    bom = build_cbom(union)
    cbom_json_path: Optional[str] = None
    cbom_xml_path: Optional[str] = None
    if output_dir is not None:
        stamp = now.strftime("%Y%m%dT%H%M%S")
        cbom_json_path, cbom_xml_path = write_cbom_files(bom, output_dir, stamp)

    # 6. Persist merge result as a MergeRun row (source scanned_at NOT mutated)
    # Commit is the caller's responsibility (WR-04); flush ensures the row is
    # visible within the same session without committing mid-unit-of-work.
    scan_id = now.isoformat(sep=" ")
    cw_json = json.dumps(coverage_warning) if coverage_warning is not None else None

    merge_row = MergeRun(
        scan_id=scan_id,
        merged_at=now,
        endpoint_count=len(union),
        sensor_count=len(sensors),
        score=int(score_result["score"]) if score_result.get("score") is not None else None,
        coverage_warning_json=cw_json,
    )
    db.add(merge_row)
    db.flush()

    return {
        "scan_id": scan_id,
        "score": score_result.get("score"),
        "rating": score_result.get("rating"),
        "subscores": score_result.get("subscores", {}),
        "drivers": score_result.get("drivers", []),
        "coverage_warning": coverage_warning,
        "endpoint_count": len(union),
        "sensor_count": len(sensors),
        "cbom_json_path": cbom_json_path,
        "cbom_xml_path": cbom_xml_path,
    }
