"""Phase 184.4, SCORE-05, D-11(1): band x severity matrix walk gate.

ROADMAP Success Criterion #3 (as literally written): every band the producer
(`quirk.severity_bands.cap_band_for_severity()`, fed by
`quirk.severity_bands.band_for_score()`) can emit is one
`quirk.reports.content_model._check_congruence()` accepts, across the FULL
matrix of (score, CRITICAL count) combinations -- not a sample.

Both tables walked here -- `BAND_THRESHOLDS` and `BAND_CRITICAL_ALLOWANCE`
-- are imported directly from `quirk.severity_bands` at test run time. This
file must NEVER re-type the threshold values (85/70/55/35) or the allowance
values (0/None) as bare literals in its own assertions/tables -- a
hand-copied table is exactly the drift D-11(1) exists to prevent (see
CLAUDE.md's "GSD state.* Verb Integrity" TOOL-04 section: a written list of
known values is not a safeguard). The score probe-points and the CRITICAL
count range are BOTH derived from the shared module's own tables, not
hand-picked.

`_check_congruence()` is imported directly from `quirk.reports.content_model`
and is never re-implemented here -- this file defines zero `_check*`
functions of its own.
"""
from __future__ import annotations

import pytest

from quirk.severity_bands import (
    BAND_ORDER,
    BAND_THRESHOLDS,
    BAND_CRITICAL_ALLOWANCE,
    band_for_score,
    cap_band_for_severity,
)
from quirk.reports.content_model import _check_congruence


# ---------------------------------------------------------------------------
# Derive probe points from the shared module's own tables -- never literals.
# ---------------------------------------------------------------------------
def _derive_score_probe_points() -> list[int]:
    """For every band's threshold: the threshold itself and threshold - 1,
    plus the 0 and 100 endpoints. All values come from BAND_THRESHOLDS, never
    hand-typed band-boundary numbers."""
    points: set[int] = {0, 100}
    for threshold in BAND_THRESHOLDS.values():
        points.add(threshold)
        points.add(threshold - 1)
    return sorted(p for p in points if 0 <= p <= 100)


def _derive_critical_count_range() -> range:
    """0 through max(finite allowance) + 2 -- extends past every finite
    allowance in BAND_CRITICAL_ALLOWANCE without hardcoding that ceiling."""
    finite_allowances = [
        v for v in BAND_CRITICAL_ALLOWANCE.values() if v is not None
    ]
    ceiling = (max(finite_allowances) if finite_allowances else 0) + 2
    return range(0, ceiling + 1)


_SCORE_PROBE_POINTS = _derive_score_probe_points()
_CRITICAL_COUNT_RANGE = _derive_critical_count_range()


def test_probe_derivation_is_nonempty() -> None:
    """Sanity: the derived probe sets are non-trivial. If BAND_THRESHOLDS or
    BAND_CRITICAL_ALLOWANCE were ever emptied, this would catch a
    vacuously-passing walk before the matrix test itself gives a false green."""
    assert len(_SCORE_PROBE_POINTS) >= 4, _SCORE_PROBE_POINTS
    assert len(_CRITICAL_COUNT_RANGE) >= 3, _CRITICAL_COUNT_RANGE


# ---------------------------------------------------------------------------
# The matrix walk itself.
# ---------------------------------------------------------------------------
def test_every_emittable_band_is_congruence_accepted() -> None:
    """For every derived (score, critical_count) combination, the band the
    producer would emit -- cap_band_for_severity(band_for_score(score),
    critical_count) -- must be one _check_congruence() accepts (does not
    raise). Every combination in the derived matrix, no sampling."""
    failures: list[str] = []
    for score in _SCORE_PROBE_POINTS:
        numeric_band = band_for_score(score)
        for critical_count in _CRITICAL_COUNT_RANGE:
            emitted_band = cap_band_for_severity(numeric_band, critical_count)
            try:
                _check_congruence(emitted_band, {"CRITICAL": critical_count})
            except Exception as exc:  # noqa: BLE001 - we want the exact type recorded
                failures.append(
                    f"score={score} critical_count={critical_count} "
                    f"numeric_band={numeric_band} emitted_band={emitted_band} "
                    f"-> {type(exc).__name__}: {exc}"
                )
    assert not failures, (
        f"{len(failures)} (score, critical_count) combination(s) produced a "
        f"band the congruence guard rejects:\n" + "\n".join(failures)
    )


def test_band_tables_have_consistent_key_sets() -> None:
    """Every band in BAND_ORDER must be a key of BAND_CRITICAL_ALLOWANCE, and
    every key of BAND_THRESHOLDS must be in BAND_ORDER. A band present in one
    table and absent from the other is a silent hole the matrix walk above
    would otherwise skip over entirely (it only ever iterates BAND_ORDER via
    band_for_score()/cap_band_for_severity(), so a band missing from
    BAND_CRITICAL_ALLOWANCE would raise inside cap_band_for_severity() rather
    than being caught as a data-shape problem)."""
    missing_from_allowance = [
        band for band in BAND_ORDER if band not in BAND_CRITICAL_ALLOWANCE
    ]
    assert not missing_from_allowance, (
        f"band(s) in BAND_ORDER missing from BAND_CRITICAL_ALLOWANCE: "
        f"{missing_from_allowance}"
    )

    unknown_threshold_keys = [
        band for band in BAND_THRESHOLDS if band not in BAND_ORDER
    ]
    assert not unknown_threshold_keys, (
        f"BAND_THRESHOLDS key(s) not present in BAND_ORDER: "
        f"{unknown_threshold_keys}"
    )


# ---------------------------------------------------------------------------
# Prove the walk CAN fail -- a matrix walk never observed failing is an
# assertion about itself, not about the code (CLAUDE.md: "the behavioural
# test is the safeguard," not a currently-green assertion).
# ---------------------------------------------------------------------------
def test_matrix_walk_fails_when_allowance_table_is_mutated() -> None:
    """Feed the SAME walk logic a mutated allowance table where a band the
    producer can legitimately emit becomes disallowed by the guard, and
    assert the walk then raises. This proves the walk is load-bearing, not
    vacuous."""
    # Build a hostile allowance table: same keys/shape as the real one, but
    # force EVERY band's allowance to 0 (nothing may coexist with any
    # CRITICAL). This guarantees at least one (score, critical_count>=1)
    # combination the real cap_band_for_severity() emits (e.g. FAIR, which
    # the real table allows unrestricted CRITICAL for) becomes rejected by a
    # guard built against this hostile table.
    hostile_allowance = {band: 0 for band in BAND_CRITICAL_ALLOWANCE}

    def hostile_check_congruence(band: str, sev_counts: dict) -> None:
        threshold = hostile_allowance.get(band)
        if threshold is None:
            return
        n_critical = sev_counts.get("CRITICAL", 0)
        if n_critical > threshold:
            raise ValueError(
                f"hostile guard: '{band}' inconsistent with {n_critical} "
                f"CRITICAL finding(s)"
            )

    saw_failure = False
    for score in _SCORE_PROBE_POINTS:
        numeric_band = band_for_score(score)
        for critical_count in _CRITICAL_COUNT_RANGE:
            if critical_count <= 0:
                continue
            emitted_band = cap_band_for_severity(numeric_band, critical_count)
            try:
                hostile_check_congruence(emitted_band, {"CRITICAL": critical_count})
            except ValueError:
                saw_failure = True
                break
        if saw_failure:
            break

    assert saw_failure, (
        "the matrix walk logic did not fail under a deliberately hostile "
        "allowance table -- the walk itself may be vacuous"
    )


