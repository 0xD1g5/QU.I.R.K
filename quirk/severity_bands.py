"""Phase 184.4 — Shared readiness-band table (SCORE-05 / D-04).

Single source of truth for the readiness band thresholds and the per-band
CRITICAL-finding allowance. Prior to this phase these numbers were
duplicated in THREE places that could (and did — BACK-89) silently drift
apart:

  - `quirk/intelligence/scoring.py::_rating()` (the numeric-score producer)
  - `quirk/reports/content_model.py::_BAND_CRITICAL_THRESHOLD` (the
    congruence guard's consumer-side table)
  - `quirk/reports/html_renderer.py::_score_band()` (a second, severity-blind
    producer feeding the same guard on the backward-compat path)

This module is the ONE place those numbers now live. `_rating()` and the
`html_renderer.py` fallback path both read `band_for_score()` /
`cap_band_for_severity()` from here; `content_model.py` imports
`BAND_CRITICAL_ALLOWANCE` directly (D-04).

Import discipline: THIS MODULE IS STDLIB-ONLY. It must never import
anything from `quirk` — `quirk/reports/content_model.py` currently imports
nothing but stdlib, and that property is what lets its pre-I/O congruence
guard run cheaply and unconditionally before any file is written. Adding a
`quirk`-rooted import here would either invert `quirk/intelligence` <->
`quirk/reports` layering (neither package imports the other) or reintroduce
I/O-bearing code into the guard's import graph. See Phase 184.4 D-04.
"""
from __future__ import annotations

import json
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Band ordering — most to least favourable. Every consumer must use this
# order rather than re-deriving it (e.g. for "least-destructive band that
# satisfies X" searches in cap_band_for_severity()).
# ---------------------------------------------------------------------------
BAND_ORDER: tuple = ("EXCELLENT", "GOOD", "MODERATE", "FAIR", "POOR")

# ---------------------------------------------------------------------------
# Minimum numeric score required for each band. POOR is the implicit floor
# and MUST NOT be a key here: a POOR entry would make the "else" branch in
# band_for_score() ambiguous (what would 0 be >= to?). POOR is anything that
# doesn't clear FAIR's threshold.
# ---------------------------------------------------------------------------
BAND_THRESHOLDS: Dict[str, int] = {
    "EXCELLENT": 85,
    "GOOD": 70,
    "MODERATE": 55,
    "FAIR": 35,
}

# ---------------------------------------------------------------------------
# Per-band CRITICAL-finding allowance (D-06 / TRANS-03, lifted verbatim from
# quirk/reports/content_model.py::_BAND_CRITICAL_THRESHOLD). None means
# "unrestricted" — that band may coexist with any CRITICAL count.
# ---------------------------------------------------------------------------
BAND_CRITICAL_ALLOWANCE: Dict[str, Optional[int]] = {
    "EXCELLENT": 0,   # D-06: zero CRITICAL allowed with EXCELLENT
    "GOOD": 0,        # D-06: zero CRITICAL allowed with GOOD
    "MODERATE": 0,    # D-06: zero CRITICAL allowed with MODERATE — per RESEARCH Pattern 2
    "FAIR": None,     # D-06: no restriction — FAIR can coexist with CRITICAL
    "POOR": None,     # D-06: no restriction — POOR can coexist with CRITICAL
}


def dump_json() -> str:
    """Phase 188 SCORE-07 — single-producer JSON artifact for non-Python consumers.

    Serializes `BAND_ORDER`, `BAND_THRESHOLDS`, and `BAND_CRITICAL_ALLOWANCE`
    into the committed artifact `src/dashboard/src/lib/severity-bands.json`,
    which `ScoreGauge.tsx` statically imports instead of hardcoding its own
    threshold literals. `tests/test_severity_bands_freshness.py` asserts the
    committed file byte-matches this function's live output (mirrors
    `tests/test_error_codes_freshness.py`'s generator-drift gate shape).

    Deterministic: `json.dumps(..., indent=2, sort_keys=True)` plus a single
    trailing newline, so two calls in one process (and across processes) are
    byte-identical regardless of dict insertion order.

    Regenerate the committed artifact with:

        python -c "from quirk.severity_bands import dump_json; \
import sys; sys.stdout.write(dump_json())" \
> src/dashboard/src/lib/severity-bands.json

    Closes SCORE-07, backlog 999.92, audit WARN-01.
    """
    payload = {
        "band_order": list(BAND_ORDER),
        "band_thresholds": dict(BAND_THRESHOLDS),
        "band_critical_allowance": dict(BAND_CRITICAL_ALLOWANCE),
        "generated_by": "quirk.severity_bands.dump_json",
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def band_for_score(score: int) -> str:
    """Numeric-only band lookup — the exact chain `_rating()` / `_score_band()`
    each hardcoded before Phase 184.4, now reading `BAND_THRESHOLDS`.
    """
    if score >= BAND_THRESHOLDS["EXCELLENT"]:
        return "EXCELLENT"
    if score >= BAND_THRESHOLDS["GOOD"]:
        return "GOOD"
    if score >= BAND_THRESHOLDS["MODERATE"]:
        return "MODERATE"
    if score >= BAND_THRESHOLDS["FAIR"]:
        return "FAIR"
    return "POOR"


def cap_band_for_severity(numeric_band: str, critical_count: int) -> str:
    """D-01/D-02: cap the BAND (never the numeric score) for open CRITICAL findings.

    Returns `numeric_band` unchanged when `critical_count <= 0`. Otherwise
    returns the least-destructive band in `BAND_ORDER` whose
    `BAND_CRITICAL_ALLOWANCE` admits `critical_count`, but never a band MORE
    favourable than `numeric_band` — this is a floor on severity, not a
    promotion, so a genuinely POOR score stays POOR.

    With the shipped table this means: any `critical_count >= 1` caps
    EXCELLENT/GOOD/MODERATE down to FAIR, and leaves FAIR and POOR untouched.
    There is no graduated N-CRITICAL ladder and no HIGH-count tier (D-02) —
    the guard only restricts CRITICAL, and every extra tier is another
    threshold that must be independently justified and proven to agree with
    the congruence guard. Do not add one here.

    Why this does not double-count against the existing agility contribution
    (D-03): CRITICAL findings also feed `high_impact` at
    `quirk/intelligence/scoring.py:155`, consumed by the
    `agility_high_impact_ratio` weight (14.0, `scoring.py:54`). That path
    moves the NUMBER (the numeric score); this function caps the BAND
    (the presentation label). They are orthogonal outputs of the same input,
    not two penalties for the same thing. Removing CRITICAL from
    `high_impact` to "avoid overlap" would silently RAISE every
    CRITICAL-bearing scan's score and re-baseline every scoring fixture and
    trend delta in the suite — a regression wearing a cleanup's clothes.
    Anyone reading this function and concluding the agility path is now
    redundant is wrong, and this comment is where they will read that.

    Raises `ValueError` for a `numeric_band` outside `BAND_ORDER` (184.4
    WR-03). This is deliberately FAIL-FAST rather than a silent clamp to
    "POOR": this module is the new single source of truth, and an
    unrecognized band always means a caller bug (every in-tree call site
    derives `numeric_band` from `band_for_score()` immediately beforehand).
    A silent fallback would emit a plausible-looking band and mask that bug
    all the way into a delivered report. The check runs BEFORE the
    `critical_count <= 0` early return so an invalid band is rejected
    identically whether or not any CRITICAL finding happens to be open —
    otherwise validation coverage would depend on scan contents.
    """
    if numeric_band not in BAND_ORDER:
        raise ValueError(
            f"numeric_band {numeric_band!r} not in BAND_ORDER {BAND_ORDER}"
        )

    if critical_count <= 0:
        return numeric_band

    numeric_idx = BAND_ORDER.index(numeric_band)
    for idx in range(numeric_idx, len(BAND_ORDER)):
        candidate = BAND_ORDER[idx]
        allowance = BAND_CRITICAL_ALLOWANCE.get(candidate)
        if allowance is None or critical_count <= allowance:
            return candidate
    return BAND_ORDER[-1]


def cap_reason(
    numeric_band: str, capped_band: str, critical_count: int, score: int
) -> Optional[str]:
    """D-09: structured, static cap-reason sentence.

    Returns `None` when `capped_band == numeric_band` (uncapped). Otherwise
    returns a single sentence built ONLY from static band names and
    integers, never from a finding's title or description:

        "Band capped at {capped_band}: {n} CRITICAL finding(s) open (score {score}/100)."

    Because this string is composed entirely of static band-name literals
    and integers — never scanner-derived or finding-derived text — downstream
    renderers do not need to sanitize it before display, unlike finding
    titles/descriptions which `report.html.j2` decides sanitization for
    per-value.
    """
    if capped_band == numeric_band:
        return None
    return (
        f"Band capped at {capped_band}: {critical_count} CRITICAL finding(s) "
        f"open (score {score}/100)."
    )
